"""Intelligence panel: Summary / Readings / Why / Ask AEGIS / Status."""

from __future__ import annotations

import html
from typing import Any

import pandas as pd
import streamlit as st

from assistant_panel import render_assistant_panel
from theme import chip_row, display_name, seriousness

_ACTION_LABELS = {
    "deenergize": "Shut down",
    "DE-ENERGIZE": "Shut down",
    "reroute": "Reroute power",
    "REROUTE": "Reroute power",
    "load_shed": "Reduce load",
    "LOAD_SHED": "Reduce load",
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
    tab_sum, tab_read, tab_why, tab_ask, tab_status = st.tabs(
        ["Summary", "Readings", "Why this score", "Ask AEGIS", "Status"]
    )

    with tab_sum:
        if selected.get("conflict_flag"):
            st.warning(
                "Caution: flood or high wind at this site. "
                "Check readings before you shut anything down."
            )

        rec = structured.get("recommended_action") or (
            (agent_plan or {}).get("recommendation") or "-"
        )
        source = "Live summary" if live_ai and (brief or {}).get("provider") == "nvidia" else "Standard summary"
        if agent_plan:
            source = "Latest check"
        chip_row(
            [
                (
                    f"Suggested: {_action_label(rec)}",
                    "warn"
                    if "shut" in _action_label(rec).lower()
                    or str(rec).lower() == "deenergize"
                    else "cyan",
                ),
                (source, "muted"),
            ]
        )

        if structured.get("conflict_warning") or selected.get("conflict_flag"):
            st.error(
                "Weather and sensors look dangerous here. "
                "Decide Reduce load or Shut down after you review Readings."
            )

        happening = structured.get("summary") or f"{site} needs a quick review."
        # Soften leftover jargon from cached briefs
        happening = (
            str(happening)
            .replace("Models disagree", "Caution")
            .replace(" — ", ". ")
            .replace("—", ". ")
        )

        wind = weather.get("wind_speed")
        surge = weather.get("flood_surge_level")
        elev = selected.get("elevation")
        risk = float(selected.get("current_risk") or 0)
        how = seriousness(risk, bool(selected.get("conflict_flag")))
        why_bits = [f"How serious: {how}."]
        try:
            if wind is not None and float(wind) > 100:
                why_bits.append(f"Wind is high at {float(wind):.0f} mph.")
        except (TypeError, ValueError):
            pass
        try:
            if surge is not None and elev is not None and float(surge) > float(elev):
                why_bits.append(
                    f"Flood water ({float(surge):.1f} ft) is above the site pad "
                    f"({float(elev):.1f} ft)."
                )
        except (TypeError, ValueError):
            pass

        cost = float(selected.get("replacement_cost") or 0)
        downs = structured.get("downstream_ids") or selected.get("downstream_ids") or []
        near = _downstream_names(list(downs), name_by_id)
        trade = (
            f"About ${cost:,.0f} to replace this equipment, or risk losing power at: {near}."
        )

        st.markdown(
            f"""
            <div class="aegis-card"><h4>What's happening</h4>
              <div>{html.escape(str(happening))}</div></div>
            <div class="aegis-card"><h4>Why it matters</h4>
              <div>{html.escape(" ".join(why_bits))}</div></div>
            <div class="aegis-card"><h4>Suggested next step</h4>
              <div><b>{html.escape(_action_label(rec))}</b>. Confirm under Site actions on the map or Approve an action below.</div>
              <div style="margin-top:0.45rem;color:#9eb6d0;font-size:0.9rem">{html.escape(trade)}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        with st.expander("Details for engineers", expanded=False):
            md = (brief or {}).get("markdown") or "_No brief available_"
            if agent_plan and agent_plan.get("action_plan"):
                st.caption("Latest check plan")
                st.markdown(agent_plan.get("action_plan"))
            st.markdown(md)

    with tab_read:
        c1, c2, c3 = st.columns(3)
        with c1:
            st.metric("Load", _plain_number(sensors.get("load"), 2))
            st.metric("Wind (mph)", _plain_number(weather.get("wind_speed"), 0))
        with c2:
            st.metric("Oil temp (C)", _plain_number(sensors.get("oil_temp"), 1))
            st.metric("Flood water (ft)", _plain_number(weather.get("flood_surge_level"), 1))
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
        drivers = selected.get("drivers") or structured.get("drivers") or []
        rows = []
        for d in drivers:
            if isinstance(d, dict):
                feat = d.get("feature") or d.get("name") or "?"
                label = _FACTOR_PLAIN.get(
                    str(feat), str(feat).replace("_", " ").title()
                )
                rows.append(
                    {
                        "Factor": label,
                        "Value": d.get("value"),
                        "Importance": d.get("importance"),
                    }
                )
            else:
                rows.append(
                    {
                        "Factor": _FACTOR_PLAIN.get(str(d), str(d).replace("_", " ")),
                        "Value": None,
                        "Importance": None,
                    }
                )
        if rows:
            st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
        else:
            st.caption("No factor breakdown for this site.")

    with tab_ask:
        render_assistant_panel(selected=selected, live_ai=live_ai)

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
