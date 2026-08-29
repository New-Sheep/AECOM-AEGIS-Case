"""AEGIS DRF API — Sprint 3 Command Center endpoints."""

from __future__ import annotations

import random
from datetime import datetime, timedelta, timezone

from rest_framework import status
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from api.models import Asset, AuditLog, ShadowLog, Telemetry, WeatherContext
from api.services.briefing import build_asset_facts
from api.services.graph import cached_graph, downstream_impact, hospital_linked_ids
from api.services.llm import EXEC_TOKEN, generate_action_brief, suggest_action_level

VALID_ACTIONS = {"load_shed", "reroute", "deenergize"}
ACTION_AUTH = {
    "load_shed": "L1",
    "reroute": "L2",
    "deenergize": "L4",
}


class RiskMapView(APIView):
    """GET /api/v1/assets/risk_map/"""

    def get(self, request: Request) -> Response:
        hospital_only = str(request.query_params.get("hospital_linked", "")).lower() in {
            "1",
            "true",
            "yes",
        }
        graph = cached_graph()
        linked = hospital_linked_ids(graph) if hospital_only else None

        payload = []
        for asset in Asset.objects.all():
            if linked is not None and asset.external_id not in linked:
                continue
            impact_count, downstream_ids = downstream_impact(asset.external_id, graph)
            tel = (
                Telemetry.objects.filter(asset=asset)
                .order_by("-timestamp")
                .only("is_anomaly")
                .first()
            )
            payload.append(
                {
                    "id": asset.external_id,
                    "name": asset.name,
                    "type": asset.asset_type,
                    "coords": [asset.lat, asset.lon],
                    "current_risk": round(float(asset.risk_score), 4),
                    "impact_count": impact_count,
                    "downstream_ids": downstream_ids,
                    "conflict_flag": bool(asset.conflict_flag),
                    "confidence": round(float(asset.confidence), 3),
                    "drivers": asset.drivers_json or [],
                    "replacement_cost": float(asset.replacement_cost),
                    "elevation": float(asset.elevation),
                    "scada_link_id": asset.scada_link_id,
                    "is_anomaly": bool(tel.is_anomaly) if tel else False,
                }
            )

        conflicts = sum(1 for a in payload if a["conflict_flag"])
        return Response(
            {
                "count": len(payload),
                "conflict_count": conflicts,
                "sprint": 4,
                "assets": payload,
            }
        )


class HealthView(APIView):
    def get(self, request: Request) -> Response:
        return Response(
            {
                "status": "ok",
                "service": "aegis-api",
                "sprint": 4,
                "assets": Asset.objects.count(),
                "audit_logs": AuditLog.objects.count(),
                "agent": "langgraph",
            }
        )


class DashboardHeaderView(APIView):
    """GET /api/v1/dashboard/header/"""

    def get(self, request: Request) -> Response:
        assets = list(Asset.objects.all())
        graph = cached_graph()
        wx = WeatherContext.objects.order_by("-timestamp").first()

        conflict_count = sum(1 for a in assets if a.conflict_flag)
        high_risk = [a for a in assets if a.risk_score > 0.7 or a.conflict_flag]
        high_risk_count = sum(1 for a in assets if a.risk_score > 0.7)
        dollars = sum(float(a.replacement_cost) for a in high_risk)
        impact_tally = 0
        for a in high_risk:
            ic, _ = downstream_impact(a.external_id, graph)
            impact_tally += ic

        wind = float(wx.wind_speed) if wx else 0.0
        surge = float(wx.flood_surge_level) if wx else 0.0
        storm = wx.storm_category if wx else "unknown"

        if conflict_count or high_risk_count >= 5 or wind > 100:
            threat = "CRITICAL"
        elif high_risk_count >= 2 or wind > 70:
            threat = "ELEVATED"
        elif high_risk_count >= 1:
            threat = "WATCH"
        else:
            threat = "NORMAL"

        return Response(
            {
                "threat_level": threat,
                "storm_category": storm,
                "wind_speed": wind,
                "surge_level": surge,
                "conflict_count": conflict_count,
                "high_risk_count": high_risk_count,
                "dollars_at_risk": round(dollars, 2),
                "impact_tally": impact_tally,
                "asset_count": len(assets),
                "sprint": 4,
                "scenario": "Hurricane Ian · SW Florida",
                "data_stack": [
                    "Open-Meteo wind (Ian window)",
                    "NOAA CO-OPS surge (IDW)",
                    "ETT oil/load proxy (not SGW SCADA)",
                    "XGBoost + Isolation Forest",
                    "LangGraph + NVIDIA NIM briefs",
                ],
            }
        )


class ActionBriefView(APIView):
    """GET /api/v1/assets/<id>/action_brief/"""

    def get(self, request: Request, asset_id: str) -> Response:
        try:
            asset = Asset.objects.get(external_id=asset_id)
        except Asset.DoesNotExist:
            return Response(
                {"detail": f"Asset {asset_id} not found"},
                status=status.HTTP_404_NOT_FOUND,
            )
        facts = build_asset_facts(asset)
        from api.services.brief_schema import render_brief_markdown
        from api.services.llm import generate_action_brief_structured

        structured, provider, ground_issues = generate_action_brief_structured(facts)
        markdown = render_brief_markdown(structured, provider=provider)
        if ground_issues and provider == "fake":
            markdown += (
                "\n\n_Note: structured brief validation/NIM issue "
                f"(`{'; '.join(ground_issues[:3])}`); served FAKE brief._\n"
            )
        from api.services.provenance import asset_provenance

        provenance = asset_provenance(
            asset_id=asset.external_id, scada_link_id=asset.scada_link_id
        )
        return Response(
            {
                "asset_id": asset.external_id,
                "markdown": markdown,
                "provider": provider,
                "facts": facts,
                "structured": structured.model_dump(),
                "grounding_issues": ground_issues,
                "provenance": provenance,
            }
        )


class ForecastView(APIView):
    """GET /api/v1/assets/<id>/forecast/ — synthetic short-horizon series."""

    def get(self, request: Request, asset_id: str) -> Response:
        try:
            asset = Asset.objects.get(external_id=asset_id)
        except Asset.DoesNotExist:
            return Response(
                {"detail": f"Asset {asset_id} not found"},
                status=status.HTTP_404_NOT_FOUND,
            )
        tel = Telemetry.objects.filter(asset=asset).order_by("-timestamp").first()
        base_temp = float(tel.oil_temp) if tel else 70.0
        base_load = float(tel.load) if tel else 0.5
        rng = random.Random(hash(asset.external_id) % 10_000)
        now = datetime.now(timezone.utc)
        points = []
        for i in range(12):
            t = now + timedelta(hours=i)
            noise_t = rng.uniform(-2.0, 2.5)
            noise_l = rng.uniform(-0.03, 0.04)
            # Slight upward drift if high risk / conflict
            drift = 0.4 * i if (asset.risk_score > 0.5 or asset.conflict_flag) else 0.05 * i
            points.append(
                {
                    "t": t.isoformat(),
                    "hour_offset": i,
                    "oil_temp": round(base_temp + drift + noise_t, 2),
                    "load": round(min(1.0, max(0.0, base_load + noise_l + 0.01 * i)), 3),
                }
            )
        return Response(
            {
                "asset_id": asset.external_id,
                "series": points,
                "note": "Synthetic short-horizon stub for Command Center chart (not a trained forecast).",
            }
        )


class ControlShutdownView(APIView):
    """POST /api/v1/control/shutdown/"""

    def post(self, request: Request) -> Response:
        data = request.data if isinstance(request.data, dict) else {}
        asset_id = str(data.get("asset_id") or "").strip()
        action_level = str(data.get("action_level") or "").strip()
        reason = str(data.get("reason_text") or "").strip()
        token = str(data.get("authorization_token") or "").strip()
        user_id = str(data.get("user_id") or "demo-ic").strip() or "demo-ic"
        human_override = bool(data.get("human_override", False))

        if not reason:
            return Response(
                {"detail": "reason_text is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if action_level not in VALID_ACTIONS:
            return Response(
                {
                    "detail": f"action_level must be one of {sorted(VALID_ACTIONS)}",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        if not asset_id:
            return Response(
                {"detail": "asset_id is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            asset = Asset.objects.get(external_id=asset_id)
        except Asset.DoesNotExist:
            return Response(
                {"detail": f"Asset {asset_id} not found"},
                status=status.HTTP_404_NOT_FOUND,
            )

        if action_level == "deenergize":
            if token != EXEC_TOKEN:
                return Response(
                    {
                        "detail": f"L4 deenergize requires authorization_token={EXEC_TOKEN}",
                    },
                    status=status.HTTP_403_FORBIDDEN,
                )
        elif not token:
            return Response(
                {"detail": "authorization_token is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        facts = build_asset_facts(asset)
        ai_rec = suggest_action_level(facts)
        auth_level = ACTION_AUTH[action_level]

        if action_level == "load_shed":
            outcome = "L1 suggest-only logged (no OT actuation)"
        elif action_level == "reroute":
            outcome = "L2 reroute suggestion logged for expert review"
        else:
            outcome = "L4 de-energize authorized (mock — no breaker trip)"

        # L3 gate message: conflict without override on L4
        if (
            action_level == "deenergize"
            and asset.conflict_flag
            and not human_override
        ):
            # Still allow but note gate review in outcome
            outcome += "; ConflictFlag present — commander proceeded without override flag"

        audit = AuditLog.objects.create(
            user_id=user_id,
            asset=asset,
            action=action_level,
            reason_text=reason,
            authorization_level=auth_level,
            ai_recommendation=ai_rec,
            human_override=human_override or (ai_rec != action_level),
            outcome=outcome,
        )
        ShadowLog.objects.create(
            asset=asset,
            ai_predicted_action=ai_rec,
            human_actual_action=action_level,
        )

        return Response(
            {
                "ok": True,
                "audit_id": audit.id,
                "asset_id": asset.external_id,
                "action_level": action_level,
                "authorization_level": auth_level,
                "ai_recommendation": ai_rec,
                "outcome": outcome,
                "human_override": audit.human_override,
            },
            status=status.HTTP_201_CREATED,
        )


# --- Sprint 4a: Nervous system + LangGraph agent ---


class PredictView(APIView):
    """POST /api/v1/predict/ — Risk Engine (whiteboard nervous system)."""

    def post(self, request: Request) -> Response:
        from api.agent.graph import predict_only

        data = request.data if isinstance(request.data, dict) else {}
        asset_id = str(data.get("asset_id") or "").strip()
        if not asset_id:
            return Response(
                {"detail": "asset_id is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if not Asset.objects.filter(external_id=asset_id).exists():
            return Response(
                {"detail": f"Asset {asset_id} not found"},
                status=status.HTTP_404_NOT_FOUND,
            )
        overrides = {
            k: data[k]
            for k in ("temp", "oil_temp", "load", "wind_speed", "surge_level")
            if k in data and data[k] is not None
        }
        try:
            result = predict_only(asset_id, overrides)
        except Exception as exc:  # noqa: BLE001
            return Response(
                {"detail": str(exc)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
        return Response(result)


class ImpactView(APIView):
    """GET /api/v1/impact/<node_id>/ — Graph Impact."""

    def get(self, request: Request, node_id: str) -> Response:
        if not Asset.objects.filter(external_id=node_id).exists():
            return Response(
                {"detail": f"Asset {node_id} not found"},
                status=status.HTTP_404_NOT_FOUND,
            )
        g = cached_graph()
        count, impacted = downstream_impact(node_id, g)
        # Criticality: lifeline share + fan-out
        lifeline = 0
        for nid in impacted:
            if nid in g and g.nodes[nid].get("asset_type") in {
                "Hospital",
                "WaterPlant",
                "Pump",
            }:
                lifeline += 1
        criticality = min(0.99, 0.4 + 0.15 * lifeline + 0.05 * count)
        return Response(
            {
                "node_id": node_id,
                "impacted_assets": impacted,
                "impact_count": count,
                "criticality_score": round(criticality, 2),
            }
        )


class BriefView(APIView):
    """POST /api/v1/brief/ — GenAI Brief (FAKE/NVIDIA)."""

    def post(self, request: Request) -> Response:
        data = request.data if isinstance(request.data, dict) else {}
        asset_id = str(data.get("asset_id") or "").strip()
        if not asset_id:
            return Response(
                {"detail": "asset_id is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            asset = Asset.objects.get(external_id=asset_id)
        except Asset.DoesNotExist:
            return Response(
                {"detail": f"Asset {asset_id} not found"},
                status=status.HTTP_404_NOT_FOUND,
            )
        facts = build_asset_facts(asset)
        if data.get("context_str"):
            facts["extra_context"] = str(data["context_str"])
        md, provider = generate_action_brief(facts)
        rec = suggest_action_level(facts)
        recommendation = (
            "DE-ENERGIZE"
            if facts.get("conflict_flag") or float(facts.get("risk") or 0) > 0.7
            else rec.upper()
        )
        return Response(
            {
                "asset_id": asset_id,
                "context_str": md,
                "action_plan": md,
                "recommendation": recommendation,
                "provider": provider,
            }
        )


class AgentRunView(APIView):
    """POST /api/v1/agent/run/ — start LangGraph Controlled Autonomy."""

    def post(self, request: Request) -> Response:
        from api.agent.graph import run_agent

        data = request.data if isinstance(request.data, dict) else {}
        asset_id = str(data.get("asset_id") or "").strip()
        if not asset_id:
            return Response(
                {"detail": "asset_id is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if not Asset.objects.filter(external_id=asset_id).exists():
            return Response(
                {"detail": f"Asset {asset_id} not found"},
                status=status.HTTP_404_NOT_FOUND,
            )
        overrides = data.get("raw_telemetry") if isinstance(data.get("raw_telemetry"), dict) else {}
        for k in ("temp", "oil_temp", "load", "wind_speed", "surge_level"):
            if k in data and data[k] is not None:
                overrides[k] = data[k]
        force = bool(data.get("force_anomaly", False))
        try:
            result = run_agent(
                asset_id,
                raw_telemetry=overrides,
                force_anomaly=force,
            )
        except Exception as exc:  # noqa: BLE001
            return Response(
                {"detail": str(exc)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
        code = status.HTTP_202_ACCEPTED if result.get("status") == "interrupted" else status.HTTP_200_OK
        return Response(result, status=code)


class AgentResumeView(APIView):
    """POST /api/v1/agent/resume/ — resume after anomaly Manual Audit."""

    def post(self, request: Request) -> Response:
        from api.agent.graph import resume_agent

        data = request.data if isinstance(request.data, dict) else {}
        thread_id = str(data.get("thread_id") or "").strip()
        decision = str(data.get("decision") or "").strip().lower()
        reason = str(data.get("reason_text") or "").strip()
        if not thread_id:
            return Response(
                {"detail": "thread_id is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if decision not in {"approved", "rejected"}:
            return Response(
                {"detail": "decision must be approved or rejected"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            result = resume_agent(thread_id, decision=decision, reason_text=reason)
        except Exception as exc:  # noqa: BLE001
            return Response(
                {"detail": str(exc)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
        return Response(result)
