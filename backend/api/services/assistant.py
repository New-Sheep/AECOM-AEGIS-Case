"""Operator Q&A assistant. FAKE templates + optional live NIM."""

from __future__ import annotations

from typing import Any

from api.models import Asset, AuditLog
from api.services.briefing import build_asset_facts
from api.services.llm import suggest_action_level, use_fake_llm

_THRESHOLDS = {
    "wind_mph": 100.0,
    "oil_c": 95.0,
}


def _f(val: Any, default: float = 0.0) -> float:
    try:
        return float(val)
    except (TypeError, ValueError):
        return default


def _plain_action(code: str) -> str:
    return {
        "load_shed": "Reduce load",
        "reroute": "Reroute power",
        "deenergize": "Shut down equipment",
    }.get(code, code)


def _short(name: str) -> str:
    n = name.replace(" (Ian conflict demo)", "").replace(" (conflict demo)", "")
    if n.endswith(" Tap"):
        n = n[: -len(" Tap")]
    return n.strip() or name


def build_site_context(asset: Asset) -> dict[str, Any]:
    facts = build_asset_facts(asset)
    sensors = facts.get("sensors") or {}
    weather = facts.get("weather") or {}
    elev = _f(facts.get("elevation"))
    wind = _f(weather.get("wind_speed"))
    surge = _f(weather.get("flood_surge_level"))
    oil = _f(sensors.get("oil_temp"))
    load = _f(sensors.get("load"))
    last = (
        AuditLog.objects.filter(asset=asset)
        .order_by("-timestamp")
        .values("action", "outcome", "timestamp")
        .first()
    )
    return {
        "facts": facts,
        "asset_id": asset.external_id,
        "name": _short(asset.name),
        "risk": _f(facts.get("risk")),
        "conflict": bool(facts.get("conflict_flag")),
        "elevation": elev,
        "wind": wind,
        "surge": surge,
        "oil": oil,
        "load": load,
        "downstream": facts.get("downstream_ids") or [],
        "suggested": suggest_action_level(facts),
        "last_audit": last,
    }


def _fake_reply(message: str, ctx: dict[str, Any]) -> dict[str, Any]:
    msg = (message or "").strip().lower()
    name = ctx["name"]
    proposed: str | None = None

    if any(k in msg for k in ("what should", "what do", "next step", "recommend", "choice")):
        suggested = ctx["suggested"]
        proposed = suggested
        reply = (
            f"For **{name}**, start with **{_plain_action(suggested)}**.\n\n"
            "- **Reduce load**: cuts power demand here by about 20% (demo). Use when things look risky but you are not ready to shut down.\n"
            "- **Reroute power**: asks crews to move power onto another path (logged only in this demo).\n"
            "- **Shut down**: turns this site off in the demo and clears its attention flag. Needs the executive token in Approve.\n\n"
            "Confirm under **Approve an action** or use the buttons under the map. Ask AEGIS never trips breakers by itself."
        )
    elif any(k in msg for k in ("warning", "conflict", "disagree", "banner", "attention", "caution")):
        if ctx["conflict"]:
            reply = (
                f"**{name}** needs attention: flood or high wind looks dangerous "
                f"(flood water **{ctx['surge']:.1f} ft** vs pad height **{ctx['elevation']:.1f} ft**, "
                f"wind **{ctx['wind']:.0f} mph**). Open the site and decide Reduce load or Shut down."
            )
        else:
            reply = (
                f"**{name}** has no attention flag right now. "
                "The top banner clears as you handle each flagged site."
            )
    elif "surge" in msg or "flood" in msg or "elevation" in msg or "water" in msg:
        over = ctx["surge"] > ctx["elevation"]
        reply = (
            f"Flood water is **{ctx['surge']:.1f} ft** and the site pad is **{ctx['elevation']:.1f} ft**. "
            + (
                "Water is above the pad, so flooding risk is why we ask you to act."
                if over
                else "Water is still below the pad. Keep watching as the storm moves."
            )
        )
    elif "wind" in msg:
        high = ctx["wind"] > _THRESHOLDS["wind_mph"]
        reply = (
            f"Wind at **{name}** is **{ctx['wind']:.0f} mph**. "
            + (
                f"That is above the **{_THRESHOLDS['wind_mph']:.0f} mph** caution level used in this demo."
                if high
                else f"That is at or under the **{_THRESHOLDS['wind_mph']:.0f} mph** caution level."
            )
        )
    elif "oil" in msg or "temp" in msg:
        hot = ctx["oil"] > _THRESHOLDS["oil_c"]
        reply = (
            f"Oil temperature is **{ctx['oil']:.1f} C**. "
            + (
                f"Above **{_THRESHOLDS['oil_c']:.0f} C** means thermal stress in this demo."
                if hot
                else f"Under the **{_THRESHOLDS['oil_c']:.0f} C** thermal caution level."
            )
        )
    elif "load" in msg:
        reply = (
            f"Electrical load on **{name}** is **{ctx['load']:.2f}** (0 to 1 scale). "
            "Submitting **Reduce load** multiplies it by about 0.8 in this demo so Readings change."
        )
    elif "threat" in msg or "critical" in msg or "risk" in msg or "serious" in msg:
        how = "High" if ctx["conflict"] or ctx["risk"] > 0.7 else (
            "Watch" if ctx["risk"] > 0.3 else "Low"
        )
        reply = (
            f"**{name}** looks **{how}** right now. "
            "The top Threat level also looks at wind and how many sites still need a decision, "
            "so one quiet site can still sit under a CRITICAL banner."
        )
    else:
        reply = (
            f"**{name}**: wind **{ctx['wind']:.0f} mph**, flood water **{ctx['surge']:.1f} ft**, "
            f"pad **{ctx['elevation']:.1f} ft**, load **{ctx['load']:.2f}**, "
            f"oil **{ctx['oil']:.1f} C**.\n\n"
            "Ask why a number is high, what the warning means, or what you should do next."
        )

    return {
        "reply": reply,
        "proposed_action": proposed,
        "proposed_action_label": _plain_action(proposed) if proposed else None,
        "context_snapshot": {
            "asset_id": ctx["asset_id"],
            "risk": ctx["risk"],
            "conflict": ctx["conflict"],
            "suggested": ctx["suggested"],
        },
    }


def _live_reply(message: str, ctx: dict[str, Any]) -> dict[str, Any] | None:
    if use_fake_llm():
        return None
    try:
        from api.services.llm import _nvidia_chat  # noqa: PLC0415
    except Exception:  # noqa: BLE001
        return None

    system = (
        "You are AEGIS Ask, a calm utility incident assistant for executives and operators. "
        "Use plain English only. Never invent sensor values. "
        "Never claim you tripped a breaker. Never mention XGBoost, Isolation Forest, "
        "LangGraph, NetworkX, SCADA, or CapEx. "
        "Suggest Reduce load / Reroute / Shut down only."
    )
    user = (
        f"Site: {ctx['name']} ({ctx['asset_id']})\n"
        f"Seriousness risk={ctx['risk']:.3f} needs_attention={ctx['conflict']}\n"
        f"Wind={ctx['wind']} mph FloodWater={ctx['surge']} ft Pad={ctx['elevation']} ft\n"
        f"Oil={ctx['oil']} C Load={ctx['load']}\n"
        f"Suggested action: {ctx['suggested']}\n"
        f"Thresholds: wind>{_THRESHOLDS['wind_mph']} oil>{_THRESHOLDS['oil_c']} "
        f"flood water > pad height\n"
        f"Operator question: {message}"
    )
    try:
        text = _nvidia_chat(system, user, max_tokens=400)
    except Exception:  # noqa: BLE001
        return None
    if not text or not str(text).strip():
        return None
    return {
        "reply": str(text).strip(),
        "proposed_action": None,
        "proposed_action_label": None,
        "context_snapshot": {
            "asset_id": ctx["asset_id"],
            "risk": ctx["risk"],
            "conflict": ctx["conflict"],
            "suggested": ctx["suggested"],
        },
        "provider": "nvidia",
    }


def answer_assistant(
    *,
    asset_id: str,
    message: str,
    history: list[dict[str, str]] | None = None,
    mode: str | None = None,
) -> dict[str, Any]:
    _ = history
    try:
        asset = Asset.objects.get(external_id=asset_id)
    except Asset.DoesNotExist as exc:
        raise ValueError(f"Asset {asset_id} not found") from exc

    ctx = build_site_context(asset)
    want_live = (mode or "").strip().lower() == "live"
    if want_live:
        live = _live_reply(message, ctx)
        if live:
            return live
    out = _fake_reply(message, ctx)
    out["provider"] = "fake"
    return out
