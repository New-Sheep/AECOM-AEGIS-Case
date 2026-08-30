"""AEGIS DRF API — Sprint 3 Command Center endpoints."""

from __future__ import annotations

import random
from datetime import datetime, timedelta, timezone

from rest_framework import status
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from api.models import Asset, AuditLog, ScenarioClock, ShadowLog, Telemetry, WeatherContext
from api.services.briefing import build_asset_facts
from api.services.graph import cached_graph, downstream_impact, hospital_linked_ids
from api.services.llm import EXEC_TOKEN, generate_action_brief, suggest_action_level
from api.services.scenario import clock_payload
from api.services.impact_economy import (
    customer_impact,
    customers_for_asset,
    dependency_impact,
    finance_breakdown,
    is_critical,
    region_situation,
    site_explain,
)

VALID_ACTIONS = {
    "load_shed",
    "reroute",
    "deenergize",
    "restore_load",
    "reenergize",
}
ACTION_AUTH = {
    "load_shed": "L1",
    "reroute": "L2",
    "deenergize": "L4",
    "restore_load": "L1",
    "reenergize": "L4",
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
                    "operational_state": asset.operational_state,
                    "baseline_load": (
                        float(asset.baseline_load)
                        if asset.baseline_load is not None
                        else None
                    ),
                    "customers_served": customers_for_asset(asset),
                    "critical_lifeline": is_critical(asset.asset_type),
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
        storm_raw = (wx.storm_category if wx else "") or ""
        # Event-agnostic: keep real category; map only legacy seed placeholders
        legacy = {"ConflictDemo", "Sprint2-Demo", "demo", "unknown", "Cat3", ""}
        if storm_raw.strip() in legacy:
            storm = "Active severe weather"
        else:
            storm = storm_raw.strip()

        # Threat = weather/risk rollup; CRITICAL reserved for decision queue or many high-risk
        if conflict_count > 0 or high_risk_count >= 5:
            threat = "CRITICAL"
        elif wind > 100 or high_risk_count >= 2 or wind > 70:
            threat = "ELEVATED"
        elif high_risk_count >= 1:
            threat = "WATCH"
        else:
            threat = "NORMAL"

        severe_weather = wind > 70 or surge > 5.0
        clock = clock_payload(ScenarioClock.get_solo())
        fin = finance_breakdown()
        return Response(
            {
                "threat_level": threat,
                "storm_category": storm,
                "wind_speed": wind,
                "surge_level": surge,
                "conflict_count": conflict_count,
                "high_risk_count": high_risk_count,
                "dollars_at_risk": round(dollars, 2),
                "illustrative_outage_cost_usd": fin["illustrative_outage_cost_usd"],
                "customers_at_risk": fin["customers_at_risk"],
                "hours_at_risk": fin["hours_at_risk"],
                "finance_methodology": fin["methodology"],
                "impact_tally": impact_tally,
                "asset_count": len(assets),
                "sprint": 4,
                "scenario": "Active emergency · service territory",
                "severe_weather": severe_weather,
                **clock,
                "data_stack": [
                    "Public weather and flood readings",
                    "Equipment sensor readings (demo)",
                    "Risk scoring and safety checks",
                    "Site dependency map",
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

        mode = str(request.query_params.get("mode") or "fake").strip().lower()
        if mode not in {"fake", "live"}:
            mode = "fake"

        structured, provider, ground_issues = generate_action_brief_structured(
            facts, mode=mode
        )
        markdown = render_brief_markdown(structured, provider=provider)
        live_fallback = bool(
            mode == "live" and provider == "fake" and ground_issues
        )
        if live_fallback:
            markdown += (
                "\n\n_Using the standard site summary._\n"
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
                "mode": mode,
                "live_fallback": live_fallback,
                "facts": facts,
                "structured": structured.model_dump(),
                "grounding_issues": ground_issues if mode == "live" else [],
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
    """POST /api/v1/control/shutdown/ — protect + restore actions (stateful)."""

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

        op = asset.operational_state or Asset.OperationalState.NORMAL

        if action_level in {"deenergize", "reenergize"}:
            if token != EXEC_TOKEN:
                return Response(
                    {
                        "detail": (
                            f"{action_level} requires authorization_token={EXEC_TOKEN}"
                        ),
                    },
                    status=status.HTTP_403_FORBIDDEN,
                )
        elif not token:
            return Response(
                {"detail": "authorization_token is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Idempotency / legality
        if action_level == "load_shed" and op in {
            Asset.OperationalState.LOAD_REDUCED,
            Asset.OperationalState.DEENERGIZED,
        }:
            return Response(
                {
                    "detail": (
                        f"Reduce load already applied or site is shut down "
                        f"(state={op}). Use restore/re-energize if needed."
                    ),
                },
                status=status.HTTP_409_CONFLICT,
            )
        if action_level == "deenergize" and op == Asset.OperationalState.DEENERGIZED:
            return Response(
                {"detail": "Site is already shut down (deenergized)."},
                status=status.HTTP_409_CONFLICT,
            )
        if action_level == "reroute" and op == Asset.OperationalState.DEENERGIZED:
            return Response(
                {"detail": "Cannot reroute while site is shut down. Re-energize first."},
                status=status.HTTP_409_CONFLICT,
            )
        if action_level == "restore_load" and op != Asset.OperationalState.LOAD_REDUCED:
            return Response(
                {
                    "detail": (
                        f"restore_load only valid when load_reduced (state={op})."
                    ),
                },
                status=status.HTTP_409_CONFLICT,
            )
        if action_level == "reenergize" and op != Asset.OperationalState.DEENERGIZED:
            return Response(
                {
                    "detail": (
                        f"reenergize only valid when deenergized (state={op})."
                    ),
                },
                status=status.HTTP_409_CONFLICT,
            )

        facts = build_asset_facts(asset)
        ai_rec = suggest_action_level(facts)
        auth_level = ACTION_AUTH[action_level]

        tel = Telemetry.objects.filter(asset=asset).order_by("-timestamp").first()
        load_before: float | None = float(tel.load) if tel else None
        load_after: float | None = load_before
        conflict_cleared = False

        def _ensure_baseline() -> None:
            if asset.baseline_load is None and load_before is not None:
                asset.baseline_load = float(load_before)

        def _target_restore() -> float:
            if asset.baseline_load is not None:
                return float(asset.baseline_load)
            return 0.8 if action_level == "restore_load" else 0.7

        if action_level == "load_shed":
            _ensure_baseline()
            if tel is not None and load_before is not None:
                load_after = max(0.05, round(load_before * 0.8, 4))
                tel.load = load_after
                tel.save(update_fields=["load"])
            asset.operational_state = Asset.OperationalState.LOAD_REDUCED
            if asset.conflict_flag:
                asset.conflict_flag = False
                conflict_cleared = True
            asset.save(
                update_fields=[
                    "operational_state",
                    "baseline_load",
                    "conflict_flag",
                ]
            )
            outcome = "Load reduced ~20% on this site (demo)."
            if load_before is not None and load_after is not None:
                human_summary = (
                    f"Reduced electrical load on {asset.name} "
                    f"from {load_before:.2f} to {load_after:.2f} (demo simulation)."
                )
            else:
                human_summary = (
                    f"Load reduction logged for {asset.name} (no telemetry to update)."
                )
            if conflict_cleared:
                human_summary += " Attention flag cleared for this site."

        elif action_level == "reroute":
            outcome = "Reroute request logged for operators."
            human_summary = (
                f"Reroute request logged for {asset.name}. "
                "Field crews must still execute the switch. Sensors are unchanged for now."
            )

        elif action_level == "deenergize":
            _ensure_baseline()
            if tel is not None:
                load_after = 0.0
                tel.load = load_after
                tel.save(update_fields=["load"])
            had_conflict = bool(asset.conflict_flag)
            asset.operational_state = Asset.OperationalState.DEENERGIZED
            if had_conflict:
                asset.conflict_flag = False
                conflict_cleared = True
            asset.save(
                update_fields=[
                    "operational_state",
                    "baseline_load",
                    "conflict_flag",
                ]
            )
            outcome = "Site shut down (demo simulation)."
            parts = [
                f"Shut down {asset.name}: load set to 0 (demo, no real breaker trip)."
            ]
            if conflict_cleared:
                parts.append("Attention flag cleared for this site.")
            if had_conflict and not human_override:
                parts.append("Proceeded without the conflict override checkbox.")
            human_summary = " ".join(parts)

        elif action_level == "restore_load":
            target = _target_restore()
            if tel is not None:
                load_after = round(target, 4)
                tel.load = load_after
                tel.save(update_fields=["load"])
            asset.operational_state = Asset.OperationalState.NORMAL
            asset.save(update_fields=["operational_state"])
            outcome = "Load restored toward baseline (demo)."
            human_summary = (
                f"Restored load on {asset.name} "
                f"from {load_before if load_before is not None else '-'} "
                f"to {load_after if load_after is not None else target:.2f} "
                "(demo restore — real grids restore in stages)."
            )

        else:  # reenergize
            target = _target_restore()
            if tel is not None:
                load_after = round(target, 4)
                tel.load = load_after
                tel.save(update_fields=["load"])
            asset.operational_state = Asset.OperationalState.NORMAL
            asset.save(update_fields=["operational_state"])
            outcome = "Site re-energized (demo simulation)."
            human_summary = (
                f"Re-energized {asset.name}: load set to {load_after:.2f} "
                "(demo, no real breaker close)."
            )

        remaining_conflicts = list(
            Asset.objects.filter(conflict_flag=True)
            .order_by("external_id")
            .values_list("name", flat=True)[:8]
        )
        remaining_count = Asset.objects.filter(conflict_flag=True).count()
        asset.refresh_from_db()

        audit = AuditLog.objects.create(
            user_id=user_id,
            asset=asset,
            action=action_level,
            reason_text=reason,
            authorization_level=auth_level,
            ai_recommendation=ai_rec,
            human_override=human_override or (ai_rec != action_level),
            outcome=outcome[:128],
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
                "asset_name": asset.name,
                "action_level": action_level,
                "authorization_level": auth_level,
                "ai_recommendation": ai_rec,
                "outcome": outcome,
                "human_summary": human_summary,
                "human_override": audit.human_override,
                "load_before": load_before,
                "load_after": load_after,
                "conflict_cleared": conflict_cleared,
                "operational_state": asset.operational_state,
                "remaining_conflict_count": remaining_count,
                "remaining_conflict_sites": remaining_conflicts,
            },
            status=status.HTTP_201_CREATED,
        )


class ScenarioTickView(APIView):
    """POST /api/v1/scenario/tick/"""

    def post(self, request: Request) -> Response:
        from api.services.scenario import tick_scenario

        data = request.data if isinstance(request.data, dict) else {}
        force = bool(data.get("force", False))
        body = tick_scenario(force=force)
        return Response(body)


class ScenarioResetView(APIView):
    """POST /api/v1/scenario/reset/"""

    def post(self, request: Request) -> Response:
        from api.services.scenario import reset_scenario

        data = request.data if isinstance(request.data, dict) else {}
        seed = int(data.get("seed") or 42)
        body = reset_scenario(seed=seed)
        return Response(body)


class ScenarioPauseView(APIView):
    """POST /api/v1/scenario/pause/  body: {paused: bool}"""

    def post(self, request: Request) -> Response:
        from api.services.scenario import set_paused

        data = request.data if isinstance(request.data, dict) else {}
        paused = bool(data.get("paused", True))
        return Response(set_paused(paused))


class ExplainSiteView(APIView):
    """GET /api/v1/explain/site/<asset_id>/"""

    def get(self, request: Request, asset_id: str) -> Response:
        try:
            asset = Asset.objects.get(external_id=asset_id)
        except Asset.DoesNotExist:
            return Response(
                {"detail": f"Asset {asset_id} not found"},
                status=status.HTTP_404_NOT_FOUND,
            )
        return Response(site_explain(asset))


class ExplainRegionView(APIView):
    """GET /api/v1/explain/region/"""

    def get(self, request: Request) -> Response:
        return Response(region_situation())


class ExplainCustomersView(APIView):
    """GET /api/v1/explain/customers/?asset_id="""

    def get(self, request: Request) -> Response:
        asset_id = str(request.query_params.get("asset_id") or "").strip() or None
        return Response(customer_impact(asset_id=asset_id))


class ExplainFinanceView(APIView):
    """GET /api/v1/explain/finance/"""

    def get(self, request: Request) -> Response:
        return Response(finance_breakdown())


class ExplainDependenciesView(APIView):
    """GET /api/v1/explain/dependencies/<asset_id>/"""

    def get(self, request: Request, asset_id: str) -> Response:
        try:
            asset = Asset.objects.get(external_id=asset_id)
        except Asset.DoesNotExist:
            return Response(
                {"detail": f"Asset {asset_id} not found"},
                status=status.HTTP_404_NOT_FOUND,
            )
        return Response(dependency_impact(asset))


class AssistantChatView(APIView):
    """POST /api/v1/assistant/chat/ — Ask AEGIS operator Q&A."""

    def post(self, request: Request) -> Response:
        from api.services.assistant import answer_assistant

        data = request.data if isinstance(request.data, dict) else {}
        asset_id = str(data.get("asset_id") or "").strip()
        message = str(data.get("message") or "").strip()
        mode = str(data.get("mode") or "fake").strip().lower() or "fake"
        history = data.get("history") if isinstance(data.get("history"), list) else []
        conversation_id = str(data.get("conversation_id") or "").strip() or None
        if not asset_id:
            return Response(
                {"detail": "asset_id is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if not message:
            return Response(
                {"detail": "message is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            body = answer_assistant(
                asset_id=asset_id,
                message=message,
                history=history,
                mode=mode,
                conversation_id=conversation_id,
            )
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_404_NOT_FOUND)
        return Response(body)


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
