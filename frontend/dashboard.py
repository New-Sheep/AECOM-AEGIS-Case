"""AEGIS Command Center: plain-language ops console."""

from __future__ import annotations

import time

import requests
import streamlit as st

from agent_banner import render_agent_banner
from api_client import API_BASE, clear_cache, fetch_json, post_json
from assistant_panel import render_ask_widget
from hitl_panel import render_hitl_panel
from intel_panel import render_intel_panel
from map_panel import render_map
from site_finder import FILTER_LABELS, filter_sites
from theme import brand_header, display_name, inject_theme, kpi_row, scenario_strip

LIVE_INTERVAL_SEC = 20


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


def _render_coach() -> None:
    # Persist dismissal across refresh via query params.
    try:
        if st.query_params.get("coach") == "done":
            st.session_state["coach_done"] = True
    except Exception:  # noqa: BLE001
        pass
    if st.session_state.get("coach_done"):
        return
    with st.container():
        st.info(
            "**Quick start:** (1) Pick a high-risk (red) map site → "
            "(2) Read the Summary → (3) Use **Site actions** under the map."
        )
        if st.button("Got it", key="coach_dismiss"):
            st.session_state["coach_done"] = True
            try:
                st.query_params["coach"] = "done"
            except Exception:  # noqa: BLE001
                pass
            st.rerun()


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
    if "last_live_tick_at" not in st.session_state:
        st.session_state.last_live_tick_at = 0.0
    if "coach_done" not in st.session_state:
        st.session_state.coach_done = False
    try:
        if st.query_params.get("coach") == "done":
            st.session_state.coach_done = True
    except Exception:  # noqa: BLE001
        pass

    hospital_only = st.sidebar.checkbox(
        "Only sites feeding hospitals",
        value=False,
        help="Filter the map to sites that can feed a hospital.",
    )

    st.sidebar.markdown("### Live scenario")
    live_mon = st.sidebar.checkbox(
        "Live monitoring",
        value=False,
        help="When on, advances the demo clock about every 20s. "
        "Leave off while you decide — use Tick once instead.",
    )
    c_tick, c_pause = st.sidebar.columns(2)
    with c_tick:
        if st.button("Tick once", width="stretch"):
            ok, body, _ = post_json("/api/v1/scenario/tick/", {"force": True})
            if ok:
                clear_cache()
                st.session_state.brief_cache = {}
                st.session_state.last_live_tick_at = time.time()
                st.sidebar.success(
                    f"Tick {body.get('sim_tick')} · {body.get('sim_phase')}"
                )
                st.rerun()
            else:
                st.sidebar.error(body.get("detail") or body)
    with c_pause:
        paused_now = bool(
            (st.session_state.get("header_cache") or {}).get("sim_paused")
        )
        label = "Resume" if paused_now else "Pause"
        if st.button(label, width="stretch"):
            ok, body, _ = post_json(
                "/api/v1/scenario/pause/",
                {"paused": not paused_now},
            )
            if ok:
                clear_cache()
                st.rerun()
            else:
                st.sidebar.error(body.get("detail") or body)
    if st.sidebar.button("Demo reset", width="stretch"):
        ok, body, _ = post_json("/api/v1/scenario/reset/", {"seed": 42})
        if ok:
            clear_cache()
            st.session_state.brief_cache = {}
            st.session_state.last_audit = None
            st.session_state.last_live_tick_at = time.time()
            st.sidebar.success(
                f"Reset · conflicts={body.get('conflict_count')} · "
                f"{body.get('sim_phase')} {body.get('sim_time_label')}"
            )
            st.rerun()
        else:
            st.sidebar.error(body.get("detail") or body)

    with st.sidebar.expander("Advanced", expanded=False):
        live_ai = st.checkbox(
            "Freer AI phrasing",
            value=False,
            help=(
                "Off (default): clear answers built directly from AEGIS tools — "
                "best for demos. On: optionally rephrase with the cloud language "
                "model when available; may sound different and can stumble on "
                "wording. Leave off unless you want freer prose."
            ),
        )
        force_anomaly = st.checkbox(
            "Simulate unusual sensors",
            value=False,
            help="Demo only: forces an unusual-sensor check on Refresh.",
        )
        with st.expander("Developer", expanded=False):
            st.caption(f"API: `{API_BASE}`")
            st.caption(
                "Demo stack: weather + equipment readings; risk scoring; dependency map."
            )

    if live_mon and (
        time.time() - float(st.session_state.last_live_tick_at)
    ) >= LIVE_INTERVAL_SEC:
        try:
            ok, body, _ = post_json(
                "/api/v1/scenario/tick/",
                {"force": False},
                spinner=False,
            )
            if ok and body.get("advanced"):
                clear_cache()
                st.session_state.brief_cache = {}
            st.session_state.last_live_tick_at = time.time()
        except Exception:
            st.session_state.last_live_tick_at = time.time()

    try:
        header = fetch_json("/api/v1/dashboard/header/")
        st.session_state.header_cache = header
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

    storm = str(header.get("storm_category") or "Active severe weather")
    scenario = header.get("scenario") or "Active emergency · service territory"
    phase = header.get("sim_phase") or ""
    tlab = header.get("sim_time_label") or ""
    sim_label = f"{phase} · {tlab}".strip(" ·") if (phase or tlab) else None
    if header.get("sim_paused"):
        sim_label = f"{sim_label or 'sim'} · paused"
    scenario_strip(
        scenario=str(scenario),
        conflict_count=conflict_count,
        high_risk_count=int(header.get("high_risk_count") or 0),
        sim_label=sim_label,
    )

    _render_coach()

    with st.expander("About AEGIS", expanded=False):
        st.write(
            "AEGIS is built for any forecasted emergency: predict risk, protect assets, "
            "and restore service. This UI helps operators see which sites need a decision, "
            "then record Reduce load, Shut down, or Restore. Sample map data currently "
            "reflects a coastal hurricane case study with a living scenario clock, "
            "not live utility controls."
        )

    threat = header.get("threat_level", "-")
    kpi_row(
        threat=str(threat),
        storm=storm,
        wind=f"{header.get('wind_speed', 0):.0f} mph",
        flood_water=f"{header.get('surge_level', 0):.1f} ft",
        dollars=f"${header.get('dollars_at_risk', 0):,.0f}",
        downstream=str(header.get("impact_tally", 0)),
    )
    outage = float(header.get("illustrative_outage_cost_usd") or 0)
    if outage:
        st.caption(
            f"Demo customer-outage estimate ~ USD {outage:,.0f}. "
            "Est. $ at risk = equipment replacement on flagged sites. "
            "Ask AEGIS → How is money calculated?"
        )

    severe = bool(header.get("severe_weather"))
    if conflict_count == 0 and (severe or str(threat) in {"ELEVATED", "CRITICAL"}):
        st.caption(
            "Severe weather is active. No sites are waiting for a decision."
        )
    # Decision count lives in the header chip only — no duplicate red banner.

    if not assets:
        st.warning("No sites loaded. Ask an engineer to run seed + heartbeat.")
        return

    def _option_label(a: dict) -> str:
        return (
            f"{'! ' if a.get('conflict_flag') else ''}"
            f"{display_name(a.get('name'), a['id'])}"
        )

    def _select_site_external(aid: str) -> None:
        """Map / match-button / Ask jump — force Open-site picker to follow."""
        st.session_state.selected_id = aid
        # Invalidate sync so the main selectbox label is rewritten next run.
        st.session_state.pop("_synced_site_id", None)
        st.session_state.pop("site_pick_main", None)

    # Clear must run BEFORE the search widget is instantiated.
    if st.session_state.pop("_clear_site_search", False):
        st.session_state.site_search_q = ""
        st.session_state.pop("site_pick_main", None)
        st.session_state.pop("_synced_site_id", None)

    # --- Find site (main page) ---
    st.markdown("### Find site")
    c_search, c_show, c_order, c_clear = st.columns([2.2, 1.0, 1.1, 0.7])
    with c_search:
        site_query = st.text_input(
            "Search by name or ID",
            key="site_search_q",
            placeholder="Start typing a name… e.g. Tampa",
            type="search",
            help="Type a name, then click a match below. Use Clear to reset.",
        )
    with c_show:
        show_band = st.selectbox(
            "Show",
            options=list(FILTER_LABELS.keys()),
            key="site_show_band",
        )
    with c_order:
        order_mode = st.selectbox(
            "Order",
            options=["Priority", "Name A–Z", "Severity high→low"],
            key="site_order_mode",
            help="Priority = High → Decision needed → Watch → Low.",
        )
    with c_clear:
        st.write("")  # align with inputs
        if st.button(
            "Clear",
            key="site_search_clear",
            width="stretch",
            help="Clear the search box and show all sites again.",
        ):
            st.session_state["_clear_site_search"] = True
            st.rerun()

    q = (site_query or st.session_state.get("site_search_q") or "").strip()
    filtered = filter_sites(
        assets,
        query=q,
        show_band=str(show_band),
        order_mode=str(order_mode),
        keep_id=None,
        inject_keep_when_searching=False,
    )

    if q and not filtered:
        st.warning(f"No sites match “{q}”. Click Clear or change Show.")
        selected = by_id.get(st.session_state.selected_id) or assets[0]
    elif q:
        st.caption(f"{len(filtered)} match(es) — click one to open on the map:")
        show_n = min(8, len(filtered))
        cols = st.columns(min(4, max(show_n, 1)))
        clicked_id: str | None = None
        for i, a in enumerate(filtered[:show_n]):
            label = display_name(a.get("name"), a["id"])
            is_open = a["id"] == st.session_state.selected_id
            with cols[i % len(cols)]:
                if st.button(
                    f"{'✓ ' if is_open else ''}{label}",
                    key=f"site_match_btn_{a['id']}",
                    type="primary" if is_open else "secondary",
                    width="stretch",
                ):
                    clicked_id = a["id"]
        if clicked_id:
            _select_site_external(clicked_id)
            st.rerun()
        selected = by_id.get(st.session_state.selected_id) or assets[0]
        # While searching, match buttons are the only picker (no selectbox fight).
    else:
        st.caption(
            f"{len(filtered)} of {len(assets)} sites · "
            "type a name above, or choose from the list below."
        )
        pick_pool = filtered if filtered else list(assets)
        labels = {_option_label(a): a["id"] for a in pick_pool}
        cur_id = st.session_state.selected_id
        if cur_id and cur_id not in labels.values() and cur_id in by_id:
            labels = {_option_label(by_id[cur_id]): cur_id, **labels}
        if labels:
            want_lab = next(
                (lab for lab, aid in labels.items() if aid == cur_id),
                None,
            )
            if st.session_state.get("_synced_site_id") != cur_id:
                if want_lab is not None:
                    st.session_state["site_pick_main"] = want_lab
                st.session_state["_synced_site_id"] = cur_id
            pick = st.selectbox(
                "Open site",
                options=list(labels.keys()),
                key="site_pick_main",
            )
            if pick in labels:
                st.session_state.selected_id = labels[pick]
                st.session_state["_synced_site_id"] = labels[pick]
        selected = by_id.get(st.session_state.selected_id) or assets[0]

    # Sidebar: read-only current site + clear search (no competing dropdown).
    st.sidebar.markdown("### Open site")
    st.sidebar.markdown(f"**{display_name(selected.get('name'), selected['id'])}**")
    if q:
        st.sidebar.caption(f"Search: “{q}” · {len(filtered)} match(es)")
        if st.sidebar.button("Clear search", key="sidebar_clear_search", width="stretch"):
            st.session_state["_clear_site_search"] = True
            st.rerun()
    else:
        st.sidebar.caption("Use Find site on the main page to search.")

    st.sidebar.markdown("---")
    if st.sidebar.button(
        "Refresh this site's analysis",
        type="primary",
        help="Re-run the site check (optional unusual-sensor demo under Advanced).",
    ):
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
    render_hitl_panel(
        selected=selected,
        brief=brief,
        agent=agent,
        name_by_id=name_by_id,
    )

    render_ask_widget(
        selected=selected,
        live_ai=live_ai,
        name_by_id=name_by_id,
    )

    if live_mon and not header.get("sim_paused"):
        remaining = max(
            0,
            int(
                LIVE_INTERVAL_SEC
                - (time.time() - float(st.session_state.last_live_tick_at))
            ),
        )
        st.caption(
            f"Live monitoring on · next auto-tick in ~{remaining}s "
            "(or click Tick once)."
        )
        if remaining <= 0:
            st.rerun()


if __name__ == "__main__":
    main()
