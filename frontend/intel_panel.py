"""Intelligence panel: Summary / Readings / Why / Status."""

from __future__ import annotations

import html
from typing import Any

import pandas as pd
import streamlit as st

from theme import chip_row, display_name, seriousness

_ACTION_LABELS = {
    "deenergize": "Shut down",
    "DE-ENERGIZE": "Shut down",
    "reroute": "Reroute power",
    "REROUTE": "Reroute power",
    "load_shed": "Reduce load",
    "LOAD_SHED": "Reduce load",
    "monitor": "Keep monitoring",
    "MONITOR": "Keep monitoring",
    "reenergize": "Re-energize",
    "restore_load": "Restore load",
}

_STEP_PLAIN = {
    "normalize": "Loaded site data",
    "anomaly": "Checked for unusual sensors",
    "manual_audit": "Waiting for your approval",
    "predict": "Scored how serious it looks",
    "impact": "Checked nearby sites that may lose power",
    "brief": "Wrote site summary",
}

_FACTOR_PLAIN = {
    "oil_temp": "Oil temperature",
    "wind_speed": "Wind",
    "surge_level": "Flood water",
    "flood_surge_level": "Flood water",
    "load": "Electrical load",
}


def _action_label(raw: Any) -> str:
    if raw is None or raw == "" or raw == "-":
        return "-"
    s = str(raw)
    return _ACTION_LABELS.get(s, s.replace("_", " ").title())


def _plain_number(value: Any, digits: int = 2) -> str:
    if value is None or value == "":
        return "-"
    try:
        return f"{float(value):.{digits}f}"
    except (TypeError, ValueError):
        return str(value)


def _downstream_names(ids: list[str], by_name: dict[str, str] | None = None) -> str:
    if not ids:
        return "no nearby dependent sites listed"
    labels = []
    for i in ids[:4]:
        labels.append(display_name((by_name or {}).get(i), i))
    extra = f" and {len(ids) - 4} more" if len(ids) > 4 else ""
    return ", ".join(labels) + extra


def _driver_value(feat: str, sensors: dict, weather: dict, selected: dict) -> Any:
    """Resolve a driver feature name to a live reading."""
    key = str(feat or "").strip()
    aliases = {
        "surge_level": ("flood_surge_level",),
        "flood_surge_level": ("flood_surge_level", "surge_level"),
        "wind_speed": ("wind_speed",),
        "oil_temp": ("oil_temp",),
        "load": ("load",),
        "voltage": ("voltage",),
        "elevation": ("elevation",),
    }
    if key in ("elevation",):
        return selected.get("elevation")
    for src in (sensors, weather):
        if key in src and src[key] is not None:
            return src[key]
        for alt in aliases.get(key, ()):
            if alt in src and src[alt] is not None:
                return src[alt]
    return None


def _format_driver_value(feat: str, value: Any) -> str:
    if value is None or value == "":
        return "—"
    try:
        num = float(value)
    except (TypeError, ValueError):
        return str(value)
    key = str(feat or "")
    if key in {"wind_speed"}:
        return f"{num:.0f} mph"
    if key in {"surge_level", "flood_surge_level", "elevation"}:
        return f"{num:.1f} ft"
    if key == "oil_temp":
        return f"{num:.1f} C"
    if key == "load":
        return f"{num:.2f}"
    return f"{num:.3f}" if abs(num) < 10 else f"{num:.1f}"


def render_intel_panel(
    *,
    selected: dict,
    brief: dict | None,
    forecast: dict | None,
    agent: dict | None,
    live_ai: bool = False,
    name_by_id: dict[str, str] | None = None,
) -> None:
    agent_plan = None
    if agent and agent.get("status") == "completed" and agent.get("action_plan"):
        agent_plan = agent

    structured = (brief or {}).get("structured") or {}
    facts = (brief or {}).get("facts") or {}
    sensors = dict(facts.get("sensors") or {})
    weather = dict(facts.get("weather") or {})
    if agent and agent.get("raw_telemetry"):
        rt = agent["raw_telemetry"]
        sensors = {
            "load": rt.get("load", sensors.get("load")),
            "oil_temp": rt.get("oil_temp", sensors.get("oil_temp")),
            "voltage": rt.get("voltage", sensors.get("voltage")),
            **{
                k: v
                for k, v in sensors.items()
                if k not in ("load", "oil_temp", "voltage")
            },
        }
        weather = {
            "wind_speed": rt.get("wind_speed", weather.get("wind_speed")),
            "flood_surge_level": rt.get(
                "surge_level",
                rt.get("flood_surge_level", weather.get("flood_surge_level")),
            ),
            **{
                k: v
                for k, v in weather.items()
                if k not in ("wind_speed", "flood_surge_level")
            },
        }

    site = display_name(selected.get("name"), selected.get("id", ""))
    tab_sum, tab_read, tab_why, tab_status = st.tabs(
        ["Summary", "Readings", "Why this score", "Status"]
    )

    with tab_sum:
        op_state = str(selected.get("operational_state") or "normal")
        if selected.get("conflict_flag") and op_state == "normal":
            st.warning(
                "Caution: flood or high wind at this site. "
                "Check Readings, then use Site actions under the map."
            )

        rec = structured.get("recommended_action") or (
            (agent_plan or {}).get("recommendation") or "-"
        )
        # Respect live control state — never suggest Keep monitoring while shut down.
        if op_state == "deenergized":
            rec = "reenergize"
        elif op_state == "load_reduced" and str(rec).lower() in {"monitor", "-"}:
            rec = "restore_load"

        source = (
            "Freer AI summary"
            if live_ai and (brief or {}).get("provider") == "nvidia"
            else "Standard summary"
        )
        if agent_plan:
            source = "Latest check"
        chip_row(
            [
                (
                    f"Suggested: {_action_label(rec)}",
                    "ok"
                    if str(rec).lower() in {"monitor", "reenergize", "restore_load"}
                    else (
                        "warn"
                        if "shut" in _action_label(rec).lower()
                        or str(rec).lower() == "deenergize"
                        else "cyan"
                    ),
                ),
                (source, "muted"),
            ]
        )

        risk = float(selected.get("current_risk") or 0)
        how = seriousness(risk, bool(selected.get("conflict_flag")))
        cust = selected.get("customers_served")
        cost = float(selected.get("replacement_cost") or 0)
        downs = structured.get("downstream_ids") or selected.get("downstream_ids") or []
        near = _downstream_names(list(downs), name_by_id)

        if op_state == "deenergized":
            happening = f"{site} is shut down (demo). Restore power when safe."
            why_bits = [
                f"How serious before shut-down: {how}.",
            ]
            if cust is not None:
                why_bits.append(f"About {int(cust):,} customers tied to this site.")
            next_note = "Use Re-energize under the map when ready."
            trade = ""
        else:
            happening = structured.get("summary") or f"{site} needs a quick review."
            happening = (
                str(happening)
                .replace("Models disagree", "Caution")
                .replace(" — ", ". ")
                .replace("—", ". ")
            )
            why_bits = [f"How serious: {how}."]
            if cust is not None:
                why_bits.append(f"About {int(cust):,} customers tied to this site.")
            if selected.get("critical_lifeline"):
                why_bits.append("Hospital or water plant (critical service).")
            elev = selected.get("elevation")
            surge = weather.get("flood_surge_level")
            try:
                if surge is not None and elev is not None and float(surge) > float(elev):
                    why_bits.append(
                        f"Flood water above pad "
                        f"({float(surge):.1f} ft vs {float(elev):.1f} ft) — see Readings."
                    )
            except (TypeError, ValueError):
                pass
            if str(rec).lower() == "monitor":
                next_note = "No control action needed unless conditions worsen."
            else:
                next_note = "Use Site actions under the map to confirm."
            trade = (
                f"About USD {cost:,.0f} equipment at this site "
                f"vs power loss at: {near}."
            )

        trade_html = (
            f'<div style="margin-top:0.45rem;color:#9eb6d0;font-size:0.9rem">'
            f"{html.escape(trade)}</div>"
            if trade
            else ""
        )
        st.markdown(
            f"""
            <div class="aegis-card"><h4>What's happening</h4>
              <div>{html.escape(str(happening))}</div></div>
            <div class="aegis-card"><h4>Why it matters</h4>
              <div>{html.escape(" ".join(why_bits))}</div></div>
            <div class="aegis-card"><h4>Suggested next step</h4>
              <div><b>{html.escape(_action_label(rec))}</b>. {html.escape(next_note)}</div>
              {trade_html}
            </div>
            """,
            unsafe_allow_html=True,
        )

        with st.expander("Full written brief", expanded=False):
            st.caption(
                "Long form of the Summary above — same points, more detail."
            )
            md = (brief or {}).get("markdown") or "_No brief available_"
            st.markdown('<div class="aegis-eng-details">', unsafe_allow_html=True)
            if agent_plan and agent_plan.get("action_plan"):
                st.caption("Latest check plan")
                st.markdown(agent_plan.get("action_plan"))
            st.markdown(md)
            st.markdown("</div>", unsafe_allow_html=True)

    with tab_read:
        st.caption("This site’s sensors (not territory-wide KPIs above).")
        c1, c2, c3 = st.columns(3)
        with c1:
            st.metric("Load", _plain_number(sensors.get("load"), 2))
            st.metric("Site wind (mph)", _plain_number(weather.get("wind_speed"), 0))
        with c2:
            st.metric("Oil temp (C)", _plain_number(sensors.get("oil_temp"), 1))
            st.metric(
                "Site flood water (ft)",
                _plain_number(weather.get("flood_surge_level"), 1),
            )
        with c3:
            st.metric("Voltage", _plain_number(sensors.get("voltage"), 1))
            st.metric("Site pad (ft)", _plain_number(selected.get("elevation"), 1))
        if forecast and forecast.get("series"):
            with st.expander("Next hours (illustrative)", expanded=False):
                df = pd.DataFrame(forecast["series"])
                st.line_chart(df.set_index("hour_offset")[["oil_temp", "load"]])
                st.caption("Short illustrative trend. Not a trained forecast.")

    with tab_why:
        st.caption("What most influenced how serious this site looks.")
        # Prefer scored drivers from the latest agent/predict pass; else risk_map strings.
        drivers = (
            (agent or {}).get("drivers")
            or selected.get("drivers")
            or structured.get("drivers")
            or []
        )
        # Fall back to weather/sensor factors when diversify left only string tags.
        if not drivers:
            drivers = ["surge_level", "wind_speed", "oil_temp", "load"]
        rows = []
        for idx, d in enumerate(drivers):
            if isinstance(d, dict):
                feat = str(d.get("feature") or d.get("name") or "?")
                label = _FACTOR_PLAIN.get(feat, feat.replace("_", " ").title())
                raw_val = d.get("value")
                if raw_val is None:
                    raw_val = _driver_value(feat, sensors, weather, selected)
                imp = d.get("importance")
                if imp is None:
                    imp = f"#{idx + 1}"
                else:
                    try:
                        imp = f"{float(imp):.2f}"
                    except (TypeError, ValueError):
                        imp = str(imp)
                rows.append(
                    {
                        "Factor": label,
                        "Value": _format_driver_value(feat, raw_val),
                        "Importance": imp,
                    }
                )
            else:
                feat = str(d)
                label = _FACTOR_PLAIN.get(feat, feat.replace("_", " ").title())
                raw_val = _driver_value(feat, sensors, weather, selected)
                rows.append(
                    {
                        "Factor": label,
                        "Value": _format_driver_value(feat, raw_val),
                        "Importance": f"#{idx + 1}",
                    }
                )
        if rows:
            st.dataframe(pd.DataFrame(rows), width="stretch", hide_index=True)
        else:
            st.caption("No factor breakdown for this site.")

    with tab_status:
        if not agent:
            st.caption(
                "No status check yet. Use the sidebar: **Refresh this site's analysis** "
                "(optionally enable demo unusual sensors under Advanced)."
            )
        else:
            status = agent.get("status")
            status_label = {
                "completed": "Complete",
                "interrupted": "Waiting for your approval",
            }.get(str(status), str(status))
            chip_row(
                [
                    (status_label, "cyan"),
                    (
                        "Unusual readings" if agent.get("is_anomaly") else "Readings normal",
                        "warn" if agent.get("is_anomaly") else "ok",
                    ),
                    (
                        f"Suggested: {_action_label(agent.get('recommendation'))}",
                        "muted",
                    ),
                ]
            )
            downs = agent.get("impact_nodes") or []
            near = _downstream_names(list(downs), name_by_id)
            st.write(f"Nearby sites that may lose power: **{near}**")
            if agent.get("messages"):
                with st.expander("Check steps", expanded=False):
                    for m in agent["messages"]:
                        plain = str(m)
                        for key, label in _STEP_PLAIN.items():
                            if key in plain.lower():
                                plain = label
                                break
                        st.write(f"- {plain}")
