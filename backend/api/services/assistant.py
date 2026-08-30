"""Operator Q&A — grounded crisis strategist with tool runners (doc 17)."""

from __future__ import annotations

import json
from typing import Any

from api.models import Asset, AuditLog
from api.services.briefing import build_asset_facts
from api.services.graph import cached_graph, downstream_impact
from api.services.impact_economy import (
    customer_impact,
    dependency_impact,
    finance_breakdown,
    region_situation,
    risk_band,
    site_explain,
)
from api.services.llm import suggest_action_level, use_fake_llm

_THRESHOLDS = {
    "wind_mph": 100.0,
    "oil_c": 95.0,
}

_WRITE_PENDING = {
    "load_shed": {
        "name": "reduce_load",
        "label": "Reduce load",
        "action_level": "load_shed",
        "requires_confirm": True,
    },
    "deenergize": {
        "name": "shutdown",
        "label": "Shut down",
        "action_level": "deenergize",
        "requires_confirm": True,
    },
    "reroute": {
        "name": "reroute",
        "label": "Reroute power",
        "action_level": "reroute",
        "requires_confirm": True,
    },
    "restore_load": {
        "name": "restore_load",
        "label": "Restore load",
        "action_level": "restore_load",
        "requires_confirm": True,
    },
    "reenergize": {
        "name": "reenergize",
        "label": "Re-energize",
        "action_level": "reenergize",
        "requires_confirm": True,
    },
}

# conversation_id -> last tool snapshots (demo in-memory)
_CONV_SNAPSHOTS: dict[str, dict[str, Any]] = {}


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
        "monitor": "Keep monitoring",
        "restore_load": "Restore load",
        "reenergize": "Re-energize",
    }.get(code, code)


def _short(name: str) -> str:
    n = name.replace(" (Ian conflict demo)", "").replace(" (conflict demo)", "")
    if n.endswith(" Tap"):
        n = n[: -len(" Tap")]
    return n.strip() or name


def _seriousness(risk: float, conflict: bool) -> str:
    if conflict or risk > 0.7:
        return "High"
    if risk > 0.3:
        return "Watch"
    return "Low"


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
        "operational_state": str(
            facts.get("operational_state") or asset.operational_state or "normal"
        ),
        "customers_served": int(facts.get("customers_served") or 0),
        "asset": asset,
    }


def _pending_for_suggested(suggested: str) -> list[dict[str, Any]]:
    if suggested in {"monitor", ""}:
        return []
    item = _WRITE_PENDING.get(suggested)
    if not item:
        return []
    out = [dict(item)]
    if suggested == "deenergize":
        out.insert(0, dict(_WRITE_PENDING["load_shed"]))
    return out


def run_tool(name: str, args: dict[str, Any], ctx: dict[str, Any]) -> dict[str, Any]:
    """Execute a grounded read tool; returns JSON-serializable dict."""
    aid = str(args.get("asset_id") or ctx["asset_id"])
    if name == "get_site_explain":
        asset = ctx.get("asset")
        if not asset or asset.external_id != aid:
            asset = Asset.objects.get(external_id=aid)
        return site_explain(asset)
    if name == "get_region_situation":
        return region_situation()
    if name == "get_customer_impact":
        return customer_impact(asset_id=aid)
    if name == "get_finance_breakdown":
        return finance_breakdown()
    if name == "get_dependency_impact":
        asset = Asset.objects.get(external_id=aid)
        return dependency_impact(asset)
    if name == "list_attention_sites":
        rows = list(
            Asset.objects.filter(conflict_flag=True)
            .order_by("external_id")
            .only("name", "external_id")
        )
        return {
            "count": len(rows),
            "sites": [
                {"asset_id": a.external_id, "name": _short(a.name)} for a in rows
            ],
        }
    if name == "list_priority_sites":
        assets = list(Asset.objects.all().only(
            "external_id", "name", "risk_score", "conflict_flag"
        ))
        ranked: list[dict[str, Any]] = []
        for a in assets:
            band = risk_band(float(a.risk_score), bool(a.conflict_flag))
            if band not in {"Needs attention", "High", "Watch"}:
                continue
            ranked.append(
                {
                    "asset_id": a.external_id,
                    "name": _short(a.name),
                    "band": band,
                    "risk": round(float(a.risk_score), 3),
                }
            )
        order = {"High": 0, "Needs attention": 1, "Watch": 2}
        ranked.sort(key=lambda r: (order[r["band"]], -float(r["risk"])))
        return {"count": len(ranked), "sites": ranked}
    if name == "say_unknown":
        return {"unknown": True, "reason": args.get("reason") or "no matching tool"}
    # legacy aliases
    if name in {"get_site_status", "explain_warning", "list_impact"}:
        asset = Asset.objects.get(external_id=aid)
        if name == "list_impact":
            return dependency_impact(asset)
        return site_explain(asset)
    return {"unknown": True, "reason": f"unknown tool {name}"}


def _prose_site(data: dict[str, Any], ctx: dict[str, Any]) -> str:
    name = _short(str(data.get("name") or ctx["name"]))
    how = _seriousness(_f(data.get("risk")), bool(data.get("conflict_flag")))
    cust = int(data.get("customers_served") or 0)
    weather = data.get("weather") or {}
    conflict = bool(data.get("conflict_flag"))

    if conflict:
        verdict = f"**{name} — decision needed** (looks **{how}**)"
    elif how == "High":
        verdict = f"**{name} — under watch** (looks **{how}**)"
    else:
        verdict = f"**{name} — stable for now** (looks **{how}**)"

    why: list[str] = []
    if conflict:
        why.append("Weather and sensors disagree with the risk score — review before acting.")
    else:
        why.append("No decision flag on this site right now.")
    wind = weather.get("wind_speed")
    surge = weather.get("flood_surge_level")
    if wind is not None:
        why.append(f"Wind **{_f(wind):.0f} mph**; flood water **{_f(surge):.1f} ft**.")
    if data.get("critical_lifeline"):
        why.append("This is a hospital or water plant (critical service).")

    stakes: list[str] = []
    if cust:
        stakes.append(f"About **{cust:,}** customers tied to this site (demo estimate).")
    downs = data.get("downstream_names") or []
    if downs:
        stakes.append(f"If it fails, nearby sites at risk: **{', '.join(downs[:4])}**.")
    cost = data.get("replacement_cost")
    if cost is not None:
        stakes.append(f"Equipment replacement cost about **USD {_f(cost):,.0f}**.")
    op = str(data.get("operational_state") or "normal").replace("_", " ")
    stakes.append(f"Current control: **{op}**.")

    lines = [verdict, "", "**Why**"]
    lines.extend(f"- {w}" for w in why[:4])
    lines.extend(["", "**Stakes**"])
    lines.extend(f"- {s}" for s in stakes[:4])
    return "\n".join(lines)


def _prose_region(data: dict[str, Any]) -> str:
    hist = data.get("risk_histogram") or {}
    n_dec = int(data.get("conflict_count") or 0)
    if n_dec > 0:
        verdict = f"**Region — {n_dec} site(s) need a decision**"
    else:
        verdict = "**Region — no sites waiting on a decision**"
    lines = [
        verdict,
        "",
        "**Situation**",
        f"- Threat level: **{data.get('threat_level')}** "
        f"({data.get('sim_phase')}, {data.get('sim_time_label')})",
        f"- Customers in territory (demo): **{int(data.get('territory_customers') or 0):,}**",
        f"- Of those, critical services: **{int(data.get('customers_critical') or 0):,}**; "
        f"other: **{int(data.get('customers_residential') or 0):,}**",
        "",
        "**Map mix**",
        f"- Low {hist.get('Low', 0)} · Watch {hist.get('Watch', 0)} · "
        f"High {hist.get('High', 0)} · Needs decision {hist.get('Needs attention', 0)}",
    ]
    return "\n".join(lines)


def _prose_customers(data: dict[str, Any]) -> str:
    region = data.get("region") or {}
    site = data.get("site")
    lines = [
        "**Who is affected** (demo numbers)",
        "",
        f"- Whole territory: **{int(region.get('territory_customers') or 0):,}** customers",
        f"- On sites that need attention now: **{int(region.get('customers_at_risk') or 0):,}**",
    ]
    if site:
        label = _short(str(site.get("name") or ""))
        lines.append(
            f"- At **{label}**: **{int(site.get('customers_served') or 0):,}**"
            + (
                " (hospital/water)"
                if site.get("critical_lifeline")
                else ""
            )
        )
        lines.append(
            f"- If this site fails, downstream customers ~ "
            f"**{int(site.get('downstream_customers') or 0):,}**"
        )
    lines.extend(
        [
            "",
            "_Demo allocation across sites — not a live meter count._",
        ]
    )
    return "\n".join(lines)


def _prose_finance(data: dict[str, Any]) -> str:
    voll = _f((data.get("constants") or {}).get("voll_per_customer_hour_usd"))
    lines = [
        "**How money is calculated** (demo)",
        "",
        "**Equipment at risk**",
        f"- **USD {_f(data.get('capex_at_risk_usd')):,.0f}** — sum of replacement cost "
        "for sites that are high-risk or need a decision",
        "",
        "**Customer outage estimate**",
        f"- **USD {_f(data.get('illustrative_outage_cost_usd')):,.0f}**",
        f"- Math: **{int(data.get('customers_at_risk') or 0):,}** customers on those sites "
        f"× **{_f(data.get('hours_at_risk')):.0f}** hours "
        f"× **USD {voll:.2f}** per customer-hour",
        "",
        "_Not a regulatory damage study — transparent demo math only._",
    ]
    return "\n".join(lines)


def _prose_deps(data: dict[str, Any]) -> str:
    cascade = data.get("cascade") or []
    name = _short(str(data.get("name") or ""))
    lines = [
        f"**If {name} loses power**",
        "",
        f"- **{int(data.get('downstream_count') or 0)}** nearby site(s) may go dark",
        f"- About **{int(data.get('downstream_customers_sum') or 0):,}** customers downstream",
    ]
    if cascade:
        lines.append("- Next sites:")
        for c in cascade[:5]:
            lines.append(
                f"  - {_short(c.get('name') or c.get('asset_id'))} "
                f"({int(c.get('customers_served') or 0):,} customers)"
            )
    else:
        lines.append("- No dependent sites listed.")
    return "\n".join(lines)


def _prose_attention(data: dict[str, Any]) -> str:
    sites = data.get("sites") or []
    n = int(data.get("count") or len(sites))
    if not sites:
        return "**No sites need a decision right now.**"
    lines = [f"**{n} site(s) need a decision**", ""]
    for s in sites[:12]:
        lines.append(f"- {_short(s.get('name') or s.get('asset_id'))}")
    if n > 12:
        lines.append(f"- …and {n - 12} more")
    return "\n".join(lines)


def _score_plain(risk: float) -> str:
    """Operator-facing severity word for a 0–1 model score."""
    r = _f(risk)
    if r >= 0.7:
        return "severe"
    if r >= 0.5:
        return "serious"
    if r >= 0.3:
        return "moderate"
    return "lower"


def _prose_priority(data: dict[str, Any]) -> str:
    sites = data.get("sites") or []
    n = int(data.get("count") or len(sites))
    if not sites:
        return "**No red or orange sites right now.**"

    groups: dict[str, list[dict[str, Any]]] = {
        "High": [],
        "Needs attention": [],
        "Watch": [],
    }
    for s in sites:
        band = str(s.get("band") or "")
        if band in groups:
            groups[band].append(s)

    lines = [
        f"**Handle in this order** ({n} sites)",
        "_Highest model risk first, then decision-needed, then watch._",
        "",
    ]

    caps = {"High": 5, "Needs attention": 5, "Watch": 3}
    titles = {
        "High": "1. High risk",
        "Needs attention": "2. Decision needed",
        "Watch": "3. Watch",
    }

    for band_key in ("High", "Needs attention", "Watch"):
        rows = groups[band_key]
        if not rows:
            continue
        cap = caps[band_key]
        lines.append(f"**{titles[band_key]}** ({len(rows)})")
        for s in rows[:cap]:
            risk = _f(s.get("risk"))
            lines.append(
                f"- {_short(s.get('name') or s.get('asset_id'))} — "
                f"{_score_plain(risk)} ({risk:.2f})"
            )
        extra = len(rows) - cap
        if extra > 0:
            lines.append(f"- _{extra} more…_")
        lines.append("")

    return "\n".join(lines).rstrip()


def _pack(
    *,
    reply: str,
    tool_calls: list[dict[str, Any]],
    tool_results: dict[str, Any] | None = None,
    pending_actions: list[dict[str, Any]] | None = None,
    proposed: str | None = None,
    ctx: dict[str, Any],
    conversation_id: str | None = None,
) -> dict[str, Any]:
    if conversation_id and tool_results:
        snap = _CONV_SNAPSHOTS.setdefault(conversation_id, {})
        snap.update(tool_results)
        _CONV_SNAPSHOTS[conversation_id] = snap
    return {
        "reply": reply,
        "tool_calls": tool_calls,
        "tool_results": tool_results or {},
        "pending_actions": pending_actions or [],
        "proposed_action": proposed,
        "proposed_action_label": _plain_action(proposed) if proposed else None,
        "conversation_id": conversation_id,
        "context_snapshot": {
            "asset_id": ctx["asset_id"],
            "risk": ctx["risk"],
            "conflict": ctx["conflict"],
            "suggested": ctx["suggested"],
            "customers_served": ctx.get("customers_served"),
        },
    }


def _run_and_narrate(
    tool_name: str,
    ctx: dict[str, Any],
    *,
    args: dict[str, Any] | None = None,
    conversation_id: str | None = None,
    pending: list[dict[str, Any]] | None = None,
    proposed: str | None = None,
) -> dict[str, Any]:
    args = args or {"asset_id": ctx["asset_id"]}
    data = run_tool(tool_name, args, ctx)
    prose_map = {
        "get_site_explain": lambda d: _prose_site(d, ctx),
        "get_site_status": lambda d: _prose_site(d, ctx),
        "explain_warning": lambda d: _prose_site(d, ctx),
        "get_region_situation": _prose_region,
        "get_customer_impact": _prose_customers,
        "get_finance_breakdown": _prose_finance,
        "get_dependency_impact": _prose_deps,
        "list_impact": _prose_deps,
        "list_attention_sites": _prose_attention,
        "list_priority_sites": _prose_priority,
        "say_unknown": lambda d: (
            "I don't know that from the tools on this screen yet.\n\n"
            "Try: this site, the region, who is affected, who loses power, "
            "site priority list, or how money is calculated."
        ),
    }
    reply = prose_map.get(tool_name, prose_map["say_unknown"])(data)
    return _pack(
        reply=reply,
        tool_calls=[{"name": tool_name, "args": args}],
        tool_results={tool_name: data},
        pending_actions=pending,
        proposed=proposed,
        ctx=ctx,
        conversation_id=conversation_id,
    )


def _append_action_brief(site_pack: dict[str, Any], *, suggested: str) -> dict[str, Any]:
    """Add a scannable next-step section without jargon."""
    if suggested == "monitor":
        site_pack["reply"] += (
            "\n\n**Next step**\n"
            "- **Keep monitoring** — no Reduce load or Shut down unless conditions worsen."
        )
        site_pack["pending_actions"] = []
        site_pack["proposed_action"] = None
        site_pack["proposed_action_label"] = None
        return site_pack
    pending = _pending_for_suggested(suggested)
    site_pack["reply"] += (
        f"\n\n**Next step**\n"
        f"- Suggested: **{_plain_action(suggested)}**\n"
        f"- Pick it under **Optional next step** and tap Confirm — "
        f"Ask AEGIS never trips breakers on its own."
    )
    site_pack["pending_actions"] = pending
    site_pack["proposed_action"] = suggested
    site_pack["proposed_action_label"] = _plain_action(suggested)
    return site_pack


def _fake_reply(
    message: str,
    ctx: dict[str, Any],
    *,
    conversation_id: str | None = None,
    history: list[dict[str, str]] | None = None,
) -> dict[str, Any]:
    msg = (message or "").strip().lower()
    name = ctx["name"]
    aid = ctx["asset_id"]
    snaps = _CONV_SNAPSHOTS.get(conversation_id or "", {})

    # Follow-ups that reuse last finance/customer snapshots
    if any(k in msg for k in ("why that", "explain that $", "that dollar", "that cost")):
        if "get_finance_breakdown" in snaps:
            return _pack(
                reply=_prose_finance(snaps["get_finance_breakdown"]),
                tool_calls=[{"name": "get_finance_breakdown", "args": {}, "cached": True}],
                tool_results={"get_finance_breakdown": snaps["get_finance_breakdown"]},
                ctx=ctx,
                conversation_id=conversation_id,
            )
        return _run_and_narrate(
            "get_finance_breakdown", ctx, conversation_id=conversation_id
        )

    if any(
        k in msg
        for k in (
            "who is affected",
            "who are affected",
            "customers",
            "consumers",
            "8 million",
            "million resident",
            "people affected",
        )
    ):
        return _run_and_narrate(
            "get_customer_impact",
            ctx,
            args={"asset_id": aid},
            conversation_id=conversation_id,
        )

    if any(
        k in msg
        for k in (
            "how is $",
            "how is the $",
            "how is money",
            "dollar",
            "finance",
            "capex",
            "calculated",
            "voll",
            "at risk",
            "outage cost",
            "methodology",
        )
    ):
        return _run_and_narrate(
            "get_finance_breakdown", ctx, conversation_id=conversation_id
        )

    if any(
        k in msg
        for k in (
            "region",
            "territory",
            "overall situation",
            "network",
            "whole system",
            "outlook",
        )
    ):
        return _run_and_narrate(
            "get_region_situation", ctx, conversation_id=conversation_id
        )

    if any(k in msg for k in ("who lose", "who goes", "downstream", "impact", "dark", "nearby")):
        return _run_and_narrate(
            "get_dependency_impact",
            ctx,
            args={"asset_id": aid},
            conversation_id=conversation_id,
        )

    if any(
        k in msg
        for k in (
            "priority",
            "most critical",
            "priority list",
            "from most critical",
            "red and orange",
            "order",
        )
    ):
        return _run_and_narrate(
            "list_priority_sites", ctx, args={}, conversation_id=conversation_id
        )

    if any(
        k in msg
        for k in (
            "sites needing",
            "need attention",
            "need a decision",
            "flagged sites",
            "attention sites",
        )
    ):
        return _run_and_narrate(
            "list_attention_sites", ctx, args={}, conversation_id=conversation_id
        )

    if any(k in msg for k in ("what should", "what do", "next step", "recommend", "choice")):
        suggested = ctx["suggested"]
        site_pack = _run_and_narrate(
            "get_site_explain", ctx, conversation_id=conversation_id
        )
        return _append_action_brief(site_pack, suggested=suggested)
    if any(
        k in msg
        for k in (
            "warning",
            "conflict",
            "disagree",
            "banner",
            "caution",
            "explain this site",
            "what's going on",
            "what is going on",
            "site strategist",
        )
    ):
        pending = _pending_for_suggested(ctx["suggested"]) if ctx["conflict"] else []
        return _run_and_narrate(
            "get_site_explain",
            ctx,
            conversation_id=conversation_id,
            pending=pending,
            proposed=ctx["suggested"] if ctx["conflict"] else None,
        )

    if any(k in msg for k in ("status", "how serious", "site status", "this site")):
        return _run_and_narrate(
            "get_site_explain", ctx, conversation_id=conversation_id
        )

    # Sensor-ish questions still grounded via site explain
    if any(k in msg for k in ("surge", "flood", "elevation", "water", "wind", "oil", "temp", "load")):
        return _run_and_narrate(
            "get_site_explain", ctx, conversation_id=conversation_id
        )

    if any(k in msg for k in ("threat", "critical", "risk", "serious")):
        # Prefer region for network threat language
        if "region" in msg or "network" in msg or "overall" in msg:
            return _run_and_narrate(
                "get_region_situation", ctx, conversation_id=conversation_id
            )
        return _run_and_narrate(
            "get_site_explain", ctx, conversation_id=conversation_id
        )

    # Unknown → say so (no invented numbers)
    if history and len(history) > 0 and any(
        k in msg for k in ("what about", "and the", "also", "follow")
    ):
        # follow-up without clear intent: region if last was finance else site
        if "get_finance_breakdown" in snaps:
            return _run_and_narrate(
                "get_customer_impact",
                ctx,
                args={"asset_id": aid},
                conversation_id=conversation_id,
            )

    return _run_and_narrate(
        "say_unknown",
        ctx,
        args={"reason": "no matching tool for this question"},
        conversation_id=conversation_id,
    )


def _live_reply(
    message: str,
    ctx: dict[str, Any],
    *,
    conversation_id: str | None = None,
) -> dict[str, Any] | None:
    msg_l = (message or "").strip().lower()

    # Structured list tools: always use deterministic prose (even when cloud AI
    # is available). Avoids the model refusing "red/orange" for High/Watch bands.
    if any(
        k in msg_l
        for k in (
            "priority",
            "most critical",
            "priority list",
            "red and orange",
        )
    ):
        out = _run_and_narrate(
            "list_priority_sites", ctx, args={}, conversation_id=conversation_id
        )
        out["provider"] = "tools"
        return out
    if any(
        k in msg_l
        for k in (
            "sites needing",
            "need attention",
            "need a decision",
            "flagged sites",
            "attention sites",
        )
    ):
        out = _run_and_narrate(
            "list_attention_sites", ctx, args={}, conversation_id=conversation_id
        )
        out["provider"] = "tools"
        return out

    if use_fake_llm():
        return None
    try:
        from api.services.llm import _nvidia_chat  # noqa: PLC0415
    except Exception:  # noqa: BLE001
        return None

    # Always gather tool facts first (1–2 tools)
    tools_to_run: list[str] = ["get_site_explain"]
    if any(k in msg_l for k in ("region", "territory", "overall")):
        tools_to_run = ["get_region_situation"]
    if any(k in msg_l for k in ("customer", "affected", "million", "people")):
        tools_to_run = ["get_customer_impact"]
    if any(k in msg_l for k in ("dollar", "finance", "capex", "calculated", "$")):
        tools_to_run = ["get_finance_breakdown"]
    if any(k in msg_l for k in ("downstream", "lose power", "impact")):
        tools_to_run = ["get_dependency_impact"]

    results: dict[str, Any] = {}
    calls: list[dict[str, Any]] = []
    for tname in tools_to_run[:2]:
        args = {"asset_id": ctx["asset_id"]} if tname != "get_region_situation" else {}
        if tname in {
            "get_finance_breakdown",
            "get_region_situation",
        }:
            args = {}
        results[tname] = run_tool(tname, args, ctx)
        calls.append({"name": tname, "args": args})

    system = (
        "You are AEGIS crisis strategist for utility incident command. "
        "Use plain English. Cite ONLY numbers from the Tool JSON. "
        "Never invent customers, dollars, wind, or surge. "
        "Map colors to bands: Needs attention and High = red; Watch = orange; "
        "Low = green. When the operator says red/orange, use those bands. "
        "If a fact is missing, say you don't know. "
        "Never claim you tripped a breaker. Keep answers concise."
    )
    user = (
        f"Operator question: {message}\n\n"
        f"Tool JSON:\n{json.dumps(results, indent=2)}"
    )
    try:
        text = _nvidia_chat(system, user, max_tokens=500)
    except Exception:  # noqa: BLE001
        return None
    if not text or not str(text).strip():
        return None

    pending = []
    proposed = None
    if any(k in msg_l for k in ("what should", "recommend", "next step")):
        pending = _pending_for_suggested(ctx["suggested"])
        proposed = ctx["suggested"] if ctx["suggested"] != "monitor" else None

    out = _pack(
        reply=str(text).strip(),
        tool_calls=calls,
        tool_results=results,
        pending_actions=pending,
        proposed=proposed,
        ctx=ctx,
        conversation_id=conversation_id,
    )
    out["provider"] = "nvidia"
    return out


def answer_assistant(
    *,
    asset_id: str,
    message: str,
    history: list[dict[str, str]] | None = None,
    mode: str | None = None,
    conversation_id: str | None = None,
) -> dict[str, Any]:
    try:
        asset = Asset.objects.get(external_id=asset_id)
    except Asset.DoesNotExist as exc:
        raise ValueError(f"Asset {asset_id} not found") from exc

    ctx = build_site_context(asset)
    want_live = (mode or "").strip().lower() == "live"
    if want_live:
        live = _live_reply(message, ctx, conversation_id=conversation_id)
        if live:
            return live
    out = _fake_reply(
        message, ctx, conversation_id=conversation_id, history=history
    )
    out["provider"] = "fake"
    return out
