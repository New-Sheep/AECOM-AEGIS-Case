"""AEGIS Command Center: plain-language ops console."""

from __future__ import annotations

import requests
import streamlit as st

from agent_banner import render_agent_banner
from api_client import API_BASE, clear_cache, fetch_json, post_json
from hitl_panel import render_hitl_panel
from intel_panel import render_intel_panel
from map_panel import render_map
from theme import brand_header, display_name, inject_theme, kpi_row, scenario_strip


def _get_brief_cached(asset_id: str, mode: str) -> dict | None:
    cache = st.session_state.setdefault("brief_cache", {})
    key = f"{asset_id}:{mode}"
    if key in cache:
        return cache[key]
    body = fetch_json(
        f"/api/v1/assets/{asset_id}/action_brief/",
        {"mode": mode},
    )
    cache[key] = body
    if len(cache) > 40:
        cache.pop(next(iter(cache)))
    return body


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
    if "brief_cache" not in st.session_state:
        st.session_state.brief_cache = {}

    hospital_only = st.sidebar.checkbox(
        "Only sites feeding hospitals",
        value=False,
    )

    with st.sidebar.expander("Advanced", expanded=False):
        live_ai = st.checkbox(
            "Live AI brief / Ask AEGIS",
            value=False,
            help="Off = fast standard answers. On = call NVIDIA when configured.",
        )
        force_anomaly = st.checkbox(
            "Demo: fake unusual sensors",
            value=False,
        )
        st.caption(f"API: `{API_BASE}`")
        st.caption(
            "Engineer notes (hidden from the main screen): "
            "demo weather + equipment readings; risk scoring; dependency map."
        )

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
            f"Cannot reach the API at `{API_BASE}`.\n\n"
            "Start it with: `python backend/manage.py runserver 127.0.0.1:8000`\n\n"
            f"Detail: {exc}"
        )
        return

    brand_header(api_ok=health.get("status") == "ok", api_base=API_BASE)

    assets = data.get("assets", [])
    by_id = {a["id"]: a for a in assets}
    name_by_id = {a["id"]: display_name(a.get("name"), a["id"]) for a in assets}
    conflict_count = int(data.get("conflict_count") or header.get("conflict_count") or 0)

    storm = str(header.get("storm_category") or "Active storm")
    scenario = header.get("scenario") or f"Active emergency: {storm}"
    scenario = (
        str(scenario)
        .replace(" · ", ": ")
        .replace(" — ", ": ")
        .replace("SW Florida", "Southwest Florida")
    )
    scenario_strip(scenario=scenario, conflict_count=conflict_count)

    with st.expander("About AEGIS", expanded=False):
        st.write(
            "AEGIS helps incident commanders see which sites need attention during "
            "a storm or other emergency, then record Reduce load or Shut down decisions. "
            "Map locations and readings are a realistic demo, not live utility controls."
        )

    threat = header.get("threat_level", "-")
    kpi_row(
        threat=str(threat),
        storm=storm,
        wind_surge=(
            f"{header.get('wind_speed', 0):.0f} mph / "
            f"{header.get('surge_level', 0):.1f} ft"
        ),
        dollars=f"${header.get('dollars_at_risk', 0):,.0f}",
        downstream=str(header.get("impact_tally", 0)),
    )

    if conflict_count == 1:
        st.error(
            "**Attention needed at 1 site.** Weather and sensors look dangerous there. "
            "Open it and decide."
        )
    elif conflict_count > 1:
        st.error(
            f"**Attention needed at {conflict_count} sites.** "
            "Weather and sensors look dangerous there. Open each site and decide."
        )

    if not assets:
        st.warning("No sites loaded. Ask an engineer to run seed + heartbeat.")
        return

    labels = {
        f"{'! ' if a.get('conflict_flag') else ''}"
        f"{display_name(a.get('name'), a['id'])}": a["id"]
        for a in assets
    }
    default_idx = 0
    id_list = list(labels.values())
    if st.session_state.selected_id in id_list:
        default_idx = id_list.index(st.session_state.selected_id)
    pick = st.sidebar.selectbox("Selected site", list(labels.keys()), index=default_idx)
    st.session_state.selected_id = labels[pick]
    selected = by_id.get(st.session_state.selected_id) or assets[0]

    st.sidebar.markdown("---")
    if st.sidebar.button("Refresh this site's analysis", type="primary"):
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
            st.session_state.brief_cache = {}
        else:
            st.sidebar.error(body.get("detail") or body)

    agent = st.session_state.agent_state
    render_agent_banner(agent)

    brief_mode = "live" if live_ai else "fake"
    brief = None
    forecast = None
    try:
        brief = _get_brief_cached(selected["id"], brief_mode)
    except requests.RequestException as exc:
        st.error(f"Could not load the site brief: {exc}")

    col_map, col_right = st.columns([1.35, 1.0], gap="medium")
    with col_map:
        st.markdown("### Map")
        render_map(assets, selected, by_id)
    with col_right:
        st.markdown(f"### {display_name(selected.get('name'), selected['id'])}")
        try:
            forecast = fetch_json(f"/api/v1/assets/{selected['id']}/forecast/")
        except requests.RequestException:
            forecast = None
        render_intel_panel(
            selected=selected,
            brief=brief,
            forecast=forecast,
            agent=agent,
            live_ai=live_ai,
            name_by_id=name_by_id,
        )

    st.markdown("---")
    render_hitl_panel(selected=selected, brief=brief, agent=agent)


if __name__ == "__main__":
    main()
