"""Pydantic schemas + grounding checks for AEGIS action briefs."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

RecommendedAction = Literal["load_shed", "reroute", "deenergize"]

RISK_TOL = 0.02
NUM_TOL = 0.05  # absolute tolerance for cited floats

_DRIVER_PLAIN = {
    "oil_temp": "oil temperature",
    "wind_speed": "wind",
    "surge_level": "flood water",
    "flood_surge_level": "flood water",
    "load": "electrical load",
    "voltage": "voltage",
}


def _plain_drivers(drivers: Any) -> list[str]:
    out: list[str] = []
    if not drivers:
        return out
    for d in drivers:
        if isinstance(d, dict):
            feat = str(d.get("feature") or d.get("name") or d)
        else:
            feat = str(d)
        out.append(_DRIVER_PLAIN.get(feat, feat.replace("_", " ")))
    return out


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
    """Keep raw feature keys for grounding / structured API; UI maps to plain words."""
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


def _short_name(facts: dict[str, Any]) -> str:
    name = str(facts.get("name") or facts.get("asset_id") or "This site")
    # Strip demo suffixes if present in DB
    for needle in (" (Ian conflict demo)", " (conflict demo)", " Tap"):
        if name.endswith(needle) or needle in name:
            name = name.replace(" (Ian conflict demo)", "").replace(" (conflict demo)", "")
            if name.endswith(" Tap"):
                name = name[: -len(" Tap")]
            break
    return name.strip()


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
    name = _short_name(facts)

    if conflict or risk > 0.7:
        action: RecommendedAction = "deenergize"
    elif risk > 0.5:
        action = "reroute"
    else:
        action = "load_shed"
    warning = None
    if conflict:
        warning = (
            "Flood or high wind at this site. Check readings before you shut anything down."
        )
    if downstream:
        trade = (
            f"About ${cost:,.0f} to replace this equipment, or risk losing power "
            f"at nearby sites that depend on it."
        )
    else:
        trade = f"About ${cost:,.0f} to replace this equipment if it fails."

    elev = facts.get("elevation")
    wind = (weather or {}).get("wind_speed")
    surge = (weather or {}).get("flood_surge_level")
    bits = [f"{name} needs attention."]
    try:
        if wind is not None and float(wind) > 100:
            bits.append(f"Wind is high at {float(wind):.0f} mph.")
    except (TypeError, ValueError):
        pass
    try:
        if surge is not None and elev is not None and float(surge) > float(elev):
            bits.append(
                f"Flood water ({float(surge):.1f} ft) is above the site pad "
                f"({float(elev):.1f} ft)."
            )
    except (TypeError, ValueError):
        pass
    if conflict:
        bits.append("Caution: weather looks dangerous here. Review before shutting down.")
    summary = " ".join(bits)
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
    """Operator-facing Markdown (kept for engineer expander / eval scripts)."""
    _ = provider
    driver_line = ", ".join(_plain_drivers(brief.drivers)) if brief.drivers else "n/a"
    if brief.risk > 0.7 or brief.conflict_flag:
        how = "High"
    elif brief.risk > 0.3:
        how = "Watch"
    else:
        how = "Low"
    action_plain = {
        "load_shed": "Reduce load",
        "reroute": "Reroute power",
        "deenergize": "Shut down equipment",
    }.get(brief.recommended_action, brief.recommended_action)

    wind = brief.cited_weather.get("wind_speed")
    surge = brief.cited_weather.get("flood_surge_level")
    load = brief.cited_sensors.get("load")
    oil = brief.cited_sensors.get("oil_temp")

    def _n(v: float | None, fmt: str) -> str:
        return fmt.format(v) if v is not None else "n/a"

    conflict_block = ""
    if brief.conflict_flag or brief.conflict_warning:
        warn = brief.conflict_warning or (
            "Flood or high wind at this site. Check readings before you shut anything down."
        )
        conflict_block = f"\n## Caution\n**WARNING:** {warn}\n"

    return (
        f"# Site summary (`{brief.asset_id}`)\n\n"
        f"## What's happening\n"
        f"{brief.summary or 'Review this site before acting.'}\n"
        f"{conflict_block}\n"
        f"## Why it matters\n"
        f"- How serious: **{how}**\n"
        f"- Why: {driver_line}\n"
        f"- Wind: {_n(wind, '{:.0f} mph')}; Flood water: {_n(surge, '{:.1f} ft')}\n"
        f"- Load: {_n(load, '{:.2f}')}; Oil temperature: {_n(oil, '{:.1f} C')}\n\n"
        f"## Suggested next step\n"
        f"**{action_plain}**. Confirm under Approve an action.\n\n"
        f"**Trade-off:** {brief.trade_off}\n"
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
