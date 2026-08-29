"""LangGraph state for AEGIS Controlled Autonomy."""

from __future__ import annotations

from enum import Enum
from typing import Any, TypedDict


class ApprovalStatus(str, Enum):
    pending = "pending"
    approved = "approved"
    rejected = "rejected"
    interrupted = "interrupted"


class AegisGraphState(TypedDict, total=False):
    asset_id: str
    raw_telemetry: dict[str, Any]
    risk_score: float
    is_anomaly: bool
    anomaly_score: float
    impact_nodes: list[str]
    action_plan: str
    recommendation: str
    approval_status: str
    thread_id: str
    messages: list[str]
    force_anomaly: bool
    force_normal: bool
    human_decision: str
    human_reason: str
    drivers: list[Any]
    conflict_flag: bool
