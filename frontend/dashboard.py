"""AEGIS Command Center — Sprint 4 redesign (SOC ops console)."""

from __future__ import annotations

import requests
import streamlit as st

from agent_banner import render_agent_banner
from api_client import API_BASE, clear_cache, fetch_json, post_json
from hitl_panel import render_hitl_panel
from intel_panel import render_intel_panel
from map_panel import render_map
from theme import brand_header, inject_theme, scenario_strip


def main() -> None:
    st.set_page_config(
        page_title="AEGIS Command Center",
        layout="wide",
        initial_sidebar_state="expanded",
        page_icon="⚡",
    )
    inject_theme()

    if "selected_id" not in st.session_state:
        st.session_state.selected_id = "SUB-001"
    if "last_audit" not in st.session_state:
        st.session_state.last_audit = None
    if "agent_state" not in st.session_state:
        st.session_state.agent_state = None

    hospital_only = st.sidebar.checkbox("Hospital-linked only", value=False)
    force_anomaly = st.sidebar.checkbox(
        "Force Anomaly Shield (demo interrupt)", value=False
    )
    st.sidebar.caption(f"API `{API_BASE}`")

    try:
        header = fetch_json("/api/v1/dashboard/header/")
        data = fetch_json(
            "/api/v1/assets/risk_map/",
            {"hospital_linked": "true"} if hospital_only else None,
        )
        health = fetch_json("/api/v1/health/")
    except requests.RequestException as exc:
        brand_header(api_ok=False, api_base=API_BASE)
        st.error(
            f"Cannot reach API at `{API_BASE}`.\n\n"
            "Run: `python backend/manage.py runserver 127.0.0.1:8000`\n\n"
            f"Detail: {exc}"
        )
        return

    brand_header(api_ok=health.get("status") == "ok", api_base=API_BASE)

    assets = data.get("assets", [])
    by_id = {a["id"]: a for a in assets}
    conflict_count = int(data.get("conflict_count") or header.get("conflict_count") or 0)

    scenario_strip(
        scenario=header.get("scenario") or "Hurricane Ian · SW Florida",
        conflict_count=conflict_count,
        data_stack=header.get("data_stack") or [],
    )

    threat = header.get("threat_level", "—")
    mrow = st.container()
    with mrow:
        h1, h2, h3, h4, h5 = st.columns(5)
        with h1:
            st.markdown(f'<div class="threat-{threat}">', unsafe_allow_html=True)
            st.metric("Threat", threat)
            st.markdown("</div>", unsafe_allow_html=True)
        h2.metric("Storm", header.get("storm_category", "—"))
        h3.metric(
            "Wind / Surge",
            f"{header.get('wind_speed', 0):.0f} / {header.get('surge_level', 0):.1f}",
        )
        h4.metric("$ at risk", f"${header.get('dollars_at_risk', 0):,.0f}")
        h5.metric("Impact tally", header.get("impact_tally", 0))

    if conflict_count:
        st.error(
            f"**ConflictFlag:** {conflict_count} asset(s) — physics critical but model "
            "score is in the Safe band. Review Old Guard before trusting a low risk score."
        )

    if not assets:
        st.warning("No assets. Run seed_aegis + run_heartbeat.")
        return

    labels = {
        f"{'⚠ ' if a.get('conflict_flag') else ''}{a['id']} — {a['name']} "
        f"(risk {a['current_risk']:.3f})": a["id"]
        for a in assets
    }
    default_idx = 0
    id_list = list(labels.values())
    if st.session_state.selected_id in id_list:
        default_idx = id_list.index(st.session_state.selected_id)
    pick = st.sidebar.selectbox("Selected asset", list(labels.keys()), index=default_idx)
    st.session_state.selected_id = labels[pick]
    selected = by_id.get(st.session_state.selected_id) or assets[0]

    st.sidebar.markdown("---")
    st.sidebar.subheader("LangGraph agent")
    if st.sidebar.button("Refresh agent (weather update)", type="primary"):
        ok, body, _ = post_json(
            "/api/v1/agent/run/",
            {
                "asset_id": selected["id"],
                "force_anomaly": force_anomaly,
            },
        )
        if ok:
            st.session_state.agent_state = body
            clear_cache()
        else:
            st.sidebar.error(body.get("detail") or body)

    agent = st.session_state.agent_state
    render_agent_banner(agent)

    try:
        brief = fetch_json(f"/api/v1/assets/{selected['id']}/action_brief/")
        forecast = fetch_json(f"/api/v1/assets/{selected['id']}/forecast/")
    except requests.RequestException as exc:
        st.error(f"Brief/forecast failed: {exc}")
        brief = None
        forecast = None

    col_map, col_right = st.columns([1.35, 1.0], gap="large")
    with col_map:
        st.markdown("### Predictive GIS")
        render_map(assets, selected, by_id)
    with col_right:
        st.markdown(f"### Intelligence · `{selected['id']}`")
        render_intel_panel(
            selected=selected, brief=brief, forecast=forecast, agent=agent
        )

    st.markdown("---")
    render_hitl_panel(selected=selected, brief=brief, agent=agent)


if __name__ == "__main__":
    main()
