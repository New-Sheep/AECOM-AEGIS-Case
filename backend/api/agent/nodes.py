"""LangGraph node functions wrapping existing AEGIS services."""

from __future__ import annotations

from typing import Any

import pandas as pd
from langgraph.types import interrupt

from api.agent.state import AegisGraphState, ApprovalStatus
from api.models import Asset, AuditLog, ShadowLog, Telemetry, WeatherContext
from api.services.anomaly import anomaly_score, load_isolation_forest, predict_anomaly
from api.services.briefing import build_asset_facts
from api.services.data_loader import FEATURE_COLS
from api.services.graph import cached_graph, downstream_impact
from api.services.inference import top_drivers
from api.services.llm import generate_action_brief
from api.services.predict import load_model, score_row
from api.services.preprocess import transform_feature_dict


LIFELINE_TYPES = {"Hospital", "WaterPlant", "Pump"}


def _append_msg(state: AegisGraphState, msg: str) -> list[str]:
    return list(state.get("messages") or []) + [msg]


def _feature_row(raw: dict[str, Any]) -> dict[str, float]:
    return {
        "load": float(raw.get("load", 0.5)),
        "oil_temp": float(raw.get("oil_temp", raw.get("temp", 70.0))),
        "wind_speed": float(raw.get("wind_speed", 0.0)),
        "surge_level": float(raw.get("surge_level", raw.get("flood_surge_level", 0.0))),
    }


def normalize_node(state: AegisGraphState) -> dict[str, Any]:
    asset_id = state["asset_id"]
    asset = Asset.objects.get(external_id=asset_id)
    tel = Telemetry.objects.filter(asset=asset).order_by("-timestamp").first()
    wx = (
        WeatherContext.objects.filter(asset=asset).order_by("-timestamp").first()
        or WeatherContext.objects.filter(asset__isnull=True).order_by("-timestamp").first()
    )

    raw: dict[str, Any] = {
        "asset_id": asset.external_id,
        "name": asset.name,
        "type": asset.asset_type,
        "lat": asset.lat,
        "lon": asset.lon,
        "elevation": float(asset.elevation),
        "scada_link_id": asset.scada_link_id,
        "replacement_cost": float(asset.replacement_cost),
        "conflict_flag": bool(asset.conflict_flag),
        "gis": {"lat": asset.lat, "lon": asset.lon, "elevation": float(asset.elevation)},
    }
    if tel:
        raw.update(
            {
                "load": float(tel.load),
                "oil_temp": float(tel.oil_temp),
                "temp": float(tel.oil_temp),
                "voltage": float(tel.voltage),
                "battery_voltage": float(tel.battery_voltage),
                "scada_is_anomaly": bool(tel.is_anomaly),
            }
        )
    if wx:
        raw.update(
            {
                "wind_speed": float(wx.wind_speed),
                "surge_level": float(wx.flood_surge_level),
                "flood_surge_level": float(wx.flood_surge_level),
                "storm_category": wx.storm_category,
                "ambient_temp": float(wx.ambient_temp),
            }
        )

    # Optional overrides from API (weather refresh simulation)
    overrides = state.get("raw_telemetry") or {}
    for key in (
        "load",
        "oil_temp",
        "temp",
        "wind_speed",
        "surge_level",
        "flood_surge_level",
    ):
        if key in overrides and overrides[key] is not None:
            raw[key] = overrides[key]
            if key == "temp":
                raw["oil_temp"] = overrides[key]
            if key == "flood_surge_level":
                raw["surge_level"] = overrides[key]

    return {
        "raw_telemetry": raw,
        "conflict_flag": bool(asset.conflict_flag),
        "risk_score": float(asset.risk_score),
        "approval_status": ApprovalStatus.pending.value,
        "action_plan": "",
        "impact_nodes": [],
        "messages": _append_msg(state, f"normalize: loaded {asset_id}"),
    }


def validate_node(state: AegisGraphState) -> dict[str, Any]:
    raw = state.get("raw_telemetry") or {}
    feats = _feature_row(raw)
    force = bool(state.get("force_anomaly"))
    force_normal = bool(state.get("force_normal"))
    try:
        model = load_isolation_forest()
        is_anom = False if force_normal else (force or predict_anomaly(model, feats))
        try:
            score = anomaly_score(model, feats)
        except Exception:  # noqa: BLE001
            score = 1.0 if is_anom else 0.0
    except FileNotFoundError:
        is_anom = False if force_normal else (force or bool(raw.get("scada_is_anomaly")))
        score = 1.0 if is_anom else 0.0

    return {
        "is_anomaly": is_anom,
        "anomaly_score": round(score, 4),
        "messages": _append_msg(
            state, f"validate: is_anomaly={is_anom} score={score:.3f}"
        ),
    }


def route_after_validate(state: AegisGraphState) -> str:
    if state.get("is_anomaly"):
        return "human_review"
    return "predict"


def human_review_node(state: AegisGraphState) -> dict[str, Any]:
    """Interrupt until operator approves/rejects continuing the AI pipeline."""
    payload = interrupt(
        {
            "type": "anomaly_manual_audit",
            "message": "Anomaly Shield — Manual Audit required before AI pipeline continues.",
            "asset_id": state.get("asset_id"),
            "anomaly_score": state.get("anomaly_score"),
            "raw_telemetry": state.get("raw_telemetry"),
        }
    )
    if isinstance(payload, dict):
        decision = str(payload.get("decision", "")).lower()
        reason = str(payload.get("reason_text", "") or "")
    else:
        decision = str(payload).lower()
        reason = ""

    if decision not in {"approved", "rejected"}:
        decision = "rejected"

    asset_id = state.get("asset_id", "")
    try:
        asset = Asset.objects.get(external_id=asset_id)
        AuditLog.objects.create(
            user_id="demo-ic",
            asset=asset,
            action="agent_human_review",
            reason_text=reason or f"Anomaly HITL: {decision}",
            authorization_level="L3",
            ai_recommendation="hold_for_audit" if decision == "rejected" else "continue_pipeline",
            human_override=True,
            outcome=f"agent_review_{decision}",
        )
        ShadowLog.objects.create(
            asset=asset,
            ai_predicted_action="human_review_required",
            human_actual_action=decision,
        )
    except Asset.DoesNotExist:
        pass

    if decision == "rejected":
        return {
            "human_decision": decision,
            "human_reason": reason,
            "approval_status": ApprovalStatus.rejected.value,
            "action_plan": (
                f"# Held for Manual Audit\n\nAsset `{asset_id}` anomaly review **rejected**. "
                f"AI pipeline stopped.\n\nReason: {reason or 'n/a'}"
            ),
            "recommendation": "HOLD",
            "messages": _append_msg(state, "human_review: rejected — pipeline halted"),
        }

    return {
        "human_decision": decision,
        "human_reason": reason,
        "approval_status": ApprovalStatus.approved.value,
        "messages": _append_msg(state, "human_review: approved — continue to predict"),
    }


def route_after_human(state: AegisGraphState) -> str:
    if state.get("approval_status") == ApprovalStatus.rejected.value:
        return "end"
    return "predict"


def predict_node(state: AegisGraphState) -> dict[str, Any]:
    raw = state.get("raw_telemetry") or {}
    feats = transform_feature_dict(_feature_row(raw))
    model = load_model()
    risk = score_row(
        model,
        load=feats["load"],
        oil_temp=feats["oil_temp"],
        wind_speed=feats["wind_speed"],
        surge_level=feats["surge_level"],
    )
    row = pd.Series(feats)
    drivers = top_drivers(model, row, k=3)

    # Persist score onto asset for map consistency
    asset_id = state["asset_id"]
    Asset.objects.filter(external_id=asset_id).update(
        risk_score=risk,
        drivers_json=drivers,
    )

    return {
        "risk_score": round(float(risk), 4),
        "drivers": drivers,
        "messages": _append_msg(state, f"predict: risk_score={risk:.3f}"),
    }


def impact_node(state: AegisGraphState) -> dict[str, Any]:
    asset_id = state["asset_id"]
    g = cached_graph()
    _, downstream = downstream_impact(asset_id, g)
    lifelines = []
    for nid in downstream:
        ntype = g.nodes[nid].get("asset_type") if nid in g else None
        if ntype in LIFELINE_TYPES:
            lifelines.append(nid)
    # Prefer lifelines; fall back to all downstream
    impact_nodes = lifelines or list(downstream)
    return {
        "impact_nodes": impact_nodes,
        "messages": _append_msg(
            state, f"impact: {len(impact_nodes)} nodes {impact_nodes[:5]}"
        ),
    }


def briefing_node(state: AegisGraphState) -> dict[str, Any]:
    asset = Asset.objects.get(external_id=state["asset_id"])
    facts = build_asset_facts(asset)
    # Prefer live graph state over stale ORM where applicable
    facts["risk"] = float(state.get("risk_score", facts.get("risk", 0.0)))
    facts["downstream_ids"] = state.get("impact_nodes") or facts.get("downstream_ids")
    if state.get("drivers"):
        facts["drivers"] = state["drivers"]
    raw = state.get("raw_telemetry") or {}
    if raw:
        facts["sensors"] = {
            **(facts.get("sensors") or {}),
            "load": raw.get("load"),
            "oil_temp": raw.get("oil_temp"),
            "voltage": raw.get("voltage"),
        }
        facts["weather"] = {
            **(facts.get("weather") or {}),
            "wind_speed": raw.get("wind_speed"),
            "flood_surge_level": raw.get("surge_level", raw.get("flood_surge_level")),
        }
    facts["is_anomaly"] = bool(state.get("is_anomaly"))

    md, provider = generate_action_brief(facts)
    md = f"_LangGraph briefing_node · provider=`{provider}`_\n\n" + md
    if facts.get("conflict_flag") or float(facts.get("risk") or 0) > 0.7:
        recommendation = "DE-ENERGIZE"
    elif float(facts.get("risk") or 0) > 0.5:
        recommendation = "REROUTE"
    else:
        recommendation = "LOAD_SHED"

    return {
        "action_plan": md,
        "recommendation": recommendation,
        "approval_status": ApprovalStatus.pending.value,
        "messages": _append_msg(state, f"briefing: recommendation={recommendation}"),
    }
