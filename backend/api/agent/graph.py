"""Compile and run the AEGIS LangGraph Controlled Autonomy machine."""

from __future__ import annotations

import uuid
from typing import Any

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.types import Command

from api.agent.nodes import (
    briefing_node,
    human_review_node,
    impact_node,
    normalize_node,
    predict_node,
    route_after_human,
    route_after_validate,
    validate_node,
)
from api.agent.state import AegisGraphState, ApprovalStatus

_CHECKPOINTER = MemorySaver()
_COMPILED = None


def build_graph():
    g = StateGraph(AegisGraphState)
    g.add_node("normalize", normalize_node)
    g.add_node("validate", validate_node)
    g.add_node("human_review", human_review_node)
    g.add_node("predict", predict_node)
    g.add_node("impact", impact_node)
    g.add_node("briefing", briefing_node)

    g.add_edge(START, "normalize")
    g.add_edge("normalize", "validate")
    g.add_conditional_edges(
        "validate",
        route_after_validate,
        {
            "human_review": "human_review",
            "predict": "predict",
        },
    )
    g.add_conditional_edges(
        "human_review",
        route_after_human,
        {
            "predict": "predict",
            "end": END,
        },
    )
    g.add_edge("predict", "impact")
    g.add_edge("impact", "briefing")
    g.add_edge("briefing", END)
    return g


def get_compiled_graph():
    global _COMPILED
    if _COMPILED is None:
        _COMPILED = build_graph().compile(checkpointer=_CHECKPOINTER)
    return _COMPILED


def _serialize_state(values: dict[str, Any], thread_id: str, status: str) -> dict[str, Any]:
    return {
        "status": status,
        "thread_id": thread_id,
        "asset_id": values.get("asset_id"),
        "risk_score": values.get("risk_score"),
        "is_anomaly": values.get("is_anomaly"),
        "anomaly_score": values.get("anomaly_score"),
        "impact_nodes": values.get("impact_nodes") or [],
        "action_plan": values.get("action_plan") or "",
        "recommendation": values.get("recommendation") or "",
        "approval_status": values.get("approval_status"),
        "raw_telemetry": values.get("raw_telemetry") or {},
        "messages": values.get("messages") or [],
        "drivers": values.get("drivers") or [],
        "conflict_flag": values.get("conflict_flag"),
    }


def _has_interrupt(result: dict[str, Any]) -> bool:
    return bool(result.get("__interrupt__"))


def run_agent(
    asset_id: str,
    *,
    thread_id: str | None = None,
    raw_telemetry: dict[str, Any] | None = None,
    force_anomaly: bool = False,
    force_normal: bool = False,
) -> dict[str, Any]:
    """Start the graph for an asset. May return status=interrupted."""
    app = get_compiled_graph()
    tid = thread_id or f"aegis-{asset_id}-{uuid.uuid4().hex[:10]}"
    config = {"configurable": {"thread_id": tid}}
    initial: AegisGraphState = {
        "asset_id": asset_id,
        "thread_id": tid,
        "raw_telemetry": raw_telemetry or {},
        "force_anomaly": force_anomaly,
        "force_normal": force_normal,
        "messages": [],
        "risk_score": 0.0,
        "is_anomaly": False,
        "impact_nodes": [],
        "action_plan": "",
        "approval_status": ApprovalStatus.pending.value,
    }
    result = app.invoke(initial, config)
    if _has_interrupt(result):
        interrupt_payload = result["__interrupt__"][0].value
        out = _serialize_state(result, tid, "interrupted")
        out["approval_status"] = ApprovalStatus.interrupted.value
        out["interrupt"] = interrupt_payload
        return out
    return _serialize_state(result, tid, "completed")


def resume_agent(
    thread_id: str,
    *,
    decision: str,
    reason_text: str = "",
) -> dict[str, Any]:
    """Resume after anomaly Manual Audit (approved | rejected)."""
    app = get_compiled_graph()
    config = {"configurable": {"thread_id": thread_id}}
    result = app.invoke(
        Command(resume={"decision": decision, "reason_text": reason_text}),
        config,
    )
    if _has_interrupt(result):
        out = _serialize_state(result, thread_id, "interrupted")
        out["interrupt"] = result["__interrupt__"][0].value
        return out
    return _serialize_state(result, thread_id, "completed")


def predict_only(
    asset_id: str,
    overrides: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Nervous-system predict: normalize + validate + predict without HITL wait."""
    state: AegisGraphState = {
        "asset_id": asset_id,
        "raw_telemetry": overrides or {},
        "force_anomaly": False,
        "messages": [],
    }
    state.update(normalize_node(state))
    state.update(validate_node(state))
    state.update(predict_node(state))
    return {
        "asset_id": asset_id,
        "temp": (state.get("raw_telemetry") or {}).get("oil_temp"),
        "load": (state.get("raw_telemetry") or {}).get("load"),
        "wind_speed": (state.get("raw_telemetry") or {}).get("wind_speed"),
        "risk_score": state.get("risk_score"),
        "is_anomaly": state.get("is_anomaly"),
        "anomaly_score": state.get("anomaly_score"),
        "drivers": state.get("drivers") or [],
    }
