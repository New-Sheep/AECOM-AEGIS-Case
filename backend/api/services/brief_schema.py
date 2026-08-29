"""Pydantic schemas + grounding checks for AEGIS action briefs."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

RecommendedAction = Literal["load_shed", "reroute", "deenergize"]

RISK_TOL = 0.02
NUM_TOL = 0.05  # absolute tolerance for cited floats


class ActionBrief(BaseModel):
    asset_id: str
    risk: float = Field(ge=0.0, le=1.0)
    confidence: float | None = Field(default=None, ge=0.0, le=1.0)
    conflict_flag: bool = False
    conflict_warning: str | None = None
    drivers: list[str] = Field(default_factory=list)
    cited_sensors: dict[str, float] = Field(default_factory=dict)
    cited_weather: dict[str, float] = Field(default_factory=dict)
    downstream_ids: list[str] = Field(default_factory=list)
    trade_off: str
    recommended_action: RecommendedAction
    summary: str = ""


class JudgeVerdict(BaseModel):
    faithful: bool
    score: float = Field(ge=0.0, le=1.0)
    issues: list[str] = Field(default_factory=list)
    rationale: str = ""


def _driver_labels(drivers: Any) -> list[str]:
    out: list[str] = []
    if not drivers:
        return out
    for d in drivers:
        if isinstance(d, dict):
            feat = d.get("feature") or d.get("name") or str(d)
            out.append(str(feat))
        else:
            out.append(str(d))
    return out


def _float_map(src: dict[str, Any] | None, keys: list[str]) -> dict[str, float]:
    if not src:
        return {}
    out: dict[str, float] = {}
    for k in keys:
        if k in src and src[k] is not None:
            try:
                out[k] = float(src[k])
            except (TypeError, ValueError):
                continue
    return out


def fake_action_brief(facts: dict[str, Any]) -> ActionBrief:
    """Deterministic structured brief from facts (FAKE path / fallback)."""
    asset_id = str(facts.get("asset_id") or "UNKNOWN")
    risk = float(facts.get("risk") or 0.0)
    conflict = bool(facts.get("conflict_flag"))
    conf_raw = facts.get("confidence")
    confidence = float(conf_raw) if conf_raw is not None else None
    drivers = _driver_labels(facts.get("drivers"))
    sensors = facts.get("sensors") or {}
    weather = facts.get("weather") or {}
    downstream = [str(x) for x in (facts.get("downstream_ids") or [])]
    cost = float(facts.get("replacement_cost") or 0.0)
    lifelines = ", ".join(downstream) if downstream else "none listed"

    if conflict or risk > 0.7:
        action: RecommendedAction = "deenergize"
    elif risk > 0.5:
        action = "reroute"
    else:
        action = "load_shed"
    warning = None
    if conflict:
        warning = (
            "Old Guard physics says CRITICAL while XGBoost risk is in the "
            "'Safe' band (< 0.3). Do not trust the low score alone — escalate to human review."
        )
    trade = (
        f"Protecting CapEx of ~${cost:,.0f} (replacement_cost) "
        f"vs cascading outage of lifeline nodes {lifelines}."
    )
    name = facts.get("name") or asset_id
    summary = f"Incident brief for {name} ({asset_id}) at risk {risk:.3f}."
    return ActionBrief(
        asset_id=asset_id,
        risk=risk,
        confidence=confidence,
        conflict_flag=conflict,
        conflict_warning=warning,
        drivers=drivers,
        cited_sensors=_float_map(sensors, ["load", "oil_temp", "voltage", "battery_voltage"]),
        cited_weather=_float_map(weather, ["wind_speed", "flood_surge_level", "ambient_temp"]),
        downstream_ids=downstream,
        trade_off=trade,
        recommended_action=action,  # type: ignore[arg-type]
        summary=summary,
    )


def render_brief_markdown(brief: ActionBrief, *, provider: str = "fake") -> str:
    """Render ActionBrief into Command Center Markdown."""
    driver_line = ", ".join(brief.drivers) if brief.drivers else "n/a"
    conf = f"{brief.confidence:.3f}" if brief.confidence is not None else "n/a"
    conflict_block = ""
    if brief.conflict_flag or brief.conflict_warning:
        warn = brief.conflict_warning or "ConflictFlag raised — escalate to human review."
        conflict_block = f"\n## ConflictFlag\n**WARNING:** {warn}\n"

    def _s(key: str) -> str:
        v = brief.cited_sensors.get(key)
        return f"{v}" if v is not None else "n/a"

    def _w(key: str) -> str:
        v = brief.cited_weather.get(key)
        return f"{v}" if v is not None else "n/a"

    lifelines = ", ".join(brief.downstream_ids) if brief.downstream_ids else "none listed"
    return (
        f"# AEGIS Action Brief — `{brief.asset_id}`\n\n"
        f"**Provider:** {provider}\n\n"
        f"{brief.summary}\n\n"
        f"## Risk\n"
        f"- **current_risk:** `{brief.risk:.3f}`\n"
        f"- **confidence:** `{conf}`\n"
        f"- **top drivers:** {driver_line}\n"
        f"{conflict_block}\n"
        f"## Grounded sensors / weather\n"
        f"- SCADA load: `{_s('load')}`\n"
        f"- SCADA oil_temp: `{_s('oil_temp')}` °C\n"
        f"- SCADA voltage: `{_s('voltage')}`\n"
        f"- Weather wind_speed: `{_w('wind_speed')}` mph\n"
        f"- Weather flood_surge_level: `{_w('flood_surge_level')}`\n\n"
        f"## Lifeline dependencies\n"
        f"Downstream lifelines at stake: **{lifelines}** "
        f"(hospital / water paths when present).\n\n"
        f"**Trade-off:** {brief.trade_off}\n\n"
        f"## Recommended posture\n"
        f"AI suggests **`{brief.recommended_action}`** "
        f"(L1 suggest-only / L4 requires executive token `AEGIS-EXEC-DEMO`).\n"
    )


def deterministic_validate(brief: ActionBrief, facts: dict[str, Any]) -> list[str]:
    """Return list of grounding failure reasons (empty = pass)."""
    issues: list[str] = []
    expected_id = str(facts.get("asset_id") or "")
    if brief.asset_id != expected_id:
        issues.append(f"asset_id mismatch: {brief.asset_id!r} != {expected_id!r}")

    try:
        fact_risk = float(facts.get("risk") or 0.0)
    except (TypeError, ValueError):
        fact_risk = 0.0
    if abs(brief.risk - fact_risk) > RISK_TOL:
        issues.append(f"risk drift: brief={brief.risk} facts={fact_risk}")

    fact_conflict = bool(facts.get("conflict_flag"))
    if fact_conflict:
        if not (brief.conflict_warning and brief.conflict_warning.strip()):
            issues.append("conflict_flag true but conflict_warning empty")
        if brief.recommended_action != "deenergize":
            issues.append(
                f"conflict requires deenergize, got {brief.recommended_action!r}"
            )

    sensors = facts.get("sensors") or {}
    for k, v in brief.cited_sensors.items():
        if k not in sensors or sensors[k] is None:
            issues.append(f"invented sensor cite: {k}={v}")
            continue
        try:
            fv = float(sensors[k])
        except (TypeError, ValueError):
            issues.append(f"bad facts sensor {k}")
            continue
        if abs(v - fv) > NUM_TOL:
            issues.append(f"sensor {k} mismatch: cited={v} facts={fv}")

    weather = facts.get("weather") or {}
    for k, v in brief.cited_weather.items():
        if k not in weather or weather[k] is None:
            issues.append(f"invented weather cite: {k}={v}")
            continue
        try:
            fv = float(weather[k])
        except (TypeError, ValueError):
            issues.append(f"bad facts weather {k}")
            continue
        if abs(v - fv) > NUM_TOL:
            issues.append(f"weather {k} mismatch: cited={v} facts={fv}")

    return issues
