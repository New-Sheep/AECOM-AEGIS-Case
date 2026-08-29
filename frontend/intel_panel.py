"""Intelligence panel — Brief / Sensors / Drivers / Agent tabs."""

from __future__ import annotations

from typing import Any

import pandas as pd
import streamlit as st

from theme import chip_row


def _metric_tile(label: str, value: Any, unit: str = "") -> None:
    if value is None or value == "":
        display = "—"
    else:
        try:
            display = f"{float(value):.2f}{unit}"
        except (TypeError, ValueError):
            display = f"{value}{unit}"
    st.markdown(
        f"""
        <div class="aegis-card" style="min-height:4.2rem">
          <h4>{label}</h4>
          <div style="font-family:'IBM Plex Mono',monospace;font-size:1.25rem;color:#f2f6fb">
            {display}
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_intel_panel(
    *,
    selected: dict,
    brief: dict | None,
    forecast: dict | None,
    agent: dict | None,
) -> None:
    agent_plan = None
    if agent and agent.get("status") == "completed" and agent.get("action_plan"):
        agent_plan = agent

    structured = (brief or {}).get("structured") or {}
    grounding = (brief or {}).get("grounding_issues") or []
    provenance = (brief or {}).get("provenance") or {}
    facts = (brief or {}).get("facts") or {}
    sensors = dict(facts.get("sensors") or {})
    weather = dict(facts.get("weather") or {})
    if agent and agent.get("raw_telemetry"):
        rt = agent["raw_telemetry"]
        sensors = {
            "load": rt.get("load", sensors.get("load")),
            "oil_temp": rt.get("oil_temp", sensors.get("oil_temp")),
            "voltage": rt.get("voltage", sensors.get("voltage")),
            **{k: v for k, v in sensors.items() if k not in ("load", "oil_temp", "voltage")},
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

    tab_brief, tab_sensors, tab_drivers, tab_agent = st.tabs(
        ["Brief", "Sensors", "Drivers", "Agent"]
    )

    with tab_brief:
        if selected.get("conflict_flag"):
            st.warning(
                "L3 gate: Old Guard vs model mismatch — review sensors before L4."
            )
        provider = (brief or {}).get("provider") or (
            "langgraph" if agent_plan else "?"
        )
        rec = structured.get("recommended_action") or (
            (agent_plan or {}).get("recommendation") or "—"
        )
        ground_ok = len(grounding) == 0
        chip_row(
            [
                (f"rec={rec}", "warn" if str(rec).lower() == "deenergize" else "cyan"),
                (f"provider={provider}", "muted"),
                (
                    "Grounding PASS" if ground_ok else "Grounding FAIL",
                    "ok" if ground_ok else "crit",
                ),
            ]
        )
        if grounding:
            st.caption("Issues: " + "; ".join(str(x) for x in grounding[:4]))
        if structured.get("conflict_warning") or selected.get("conflict_flag"):
            st.error(
                structured.get("conflict_warning")
                or "ConflictFlag active — physics critical while model band is Safe."
            )
        trade = structured.get("trade_off")
        if trade:
            st.info(f"**Trade-off:** {trade}")

        if agent_plan:
            st.markdown("**LangGraph action plan**")
            st.markdown(agent_plan.get("action_plan") or "_No plan_")
        else:
            st.markdown((brief or {}).get("markdown") or "_No brief available_")

    with tab_sensors:
        c1, c2, c3 = st.columns(3)
        with c1:
            _metric_tile("Load", sensors.get("load"))
            _metric_tile("Wind (mph)", weather.get("wind_speed"))
        with c2:
            _metric_tile("Oil temp (°C)", sensors.get("oil_temp"))
            _metric_tile("Surge (ft)", weather.get("flood_surge_level"))
        with c3:
            _metric_tile("Voltage", sensors.get("voltage"))
            _metric_tile("Elevation (ft)", selected.get("elevation"))
        st.caption(
            f"SCADA source: `{provenance.get('scada_source', 'unknown')}` · "
            f"Wind: `{provenance.get('wind_source', 'unknown')}` · "
            f"Surge: `{provenance.get('surge_source', 'unknown')}`"
        )
        if forecast and forecast.get("series"):
            with st.expander("Short-horizon forecast", expanded=False):
                df = pd.DataFrame(forecast["series"])
                st.line_chart(df.set_index("hour_offset")[["oil_temp", "load"]])
                st.caption(forecast.get("note", ""))

    with tab_drivers:
        st.metric("Confidence", f"{selected.get('confidence', 0):.3f}")
        drivers = selected.get("drivers") or structured.get("drivers") or []
        rows = []
        for d in drivers:
            if isinstance(d, dict):
                rows.append(
                    {
                        "feature": d.get("feature") or d.get("name") or "?",
                        "value": d.get("value"),
                        "importance": d.get("importance"),
                    }
                )
            else:
                rows.append({"feature": str(d), "value": None, "importance": None})
        if rows:
            st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
        else:
            st.caption("No driver attributions on this asset.")

    with tab_agent:
        if not agent:
            st.caption(
                "No agent run yet. Use sidebar **Refresh agent (weather update)** "
                "(optionally Force Anomaly Shield)."
            )
        else:
            chip_row(
                [
                    (f"status={agent.get('status')}", "cyan"),
                    (
                        f"anomaly={agent.get('is_anomaly')}",
                        "warn" if agent.get("is_anomaly") else "ok",
                    ),
                    (f"rec={agent.get('recommendation') or '—'}", "muted"),
                ]
            )
            st.write(
                f"risk_score=`{agent.get('risk_score')}` · "
                f"impact_nodes=`{agent.get('impact_nodes')}`"
            )
            if agent.get("messages"):
                with st.expander("LangGraph trail", expanded=True):
                    for m in agent["messages"]:
                        st.write(f"- {m}")
