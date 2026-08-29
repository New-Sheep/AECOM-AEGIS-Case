"""Folium GIS map panel. OpenStreetMap, click to select, quick actions under map."""

from __future__ import annotations

import folium
import streamlit as st
from streamlit_folium import st_folium

from api_client import clear_cache, post_json
from theme import display_name

EXEC_TOKEN = "AEGIS-EXEC-DEMO"
MAP_HEIGHT = 300


def risk_color(risk: float, conflict: bool = False) -> str:
    if conflict:
        return "#c23b22"
    if risk < 0.3:
        return "#2f9e44"
    if risk <= 0.7:
        return "#e8590c"
    return "#fa5252"


def _nearest_asset(lat: float, lon: float, assets: list[dict]) -> str | None:
    best_id = None
    best_d = 1e18
    for a in assets:
        alat, alon = a["coords"]
        d = (alat - lat) ** 2 + (alon - lon) ** 2
        if d < best_d:
            best_d = d
            best_id = a["id"]
    if best_id is None or best_d > 0.08**2:
        return None
    return best_id


def _quick_action(asset_id: str, action: str, *, reason: str) -> None:
    token = EXEC_TOKEN if action == "deenergize" else "AEGIS-OPS"
    ok, body, _ = post_json(
        "/api/v1/control/shutdown/",
        {
            "asset_id": asset_id,
            "action_level": action,
            "authorization_token": token,
            "reason_text": reason,
            "user_id": "demo-ic",
            "human_override": False,
        },
    )
    if ok:
        st.session_state.last_audit = body
        st.session_state.brief_cache = {}
        clear_cache()
        st.success(body.get("human_summary") or "Action recorded.")
        st.rerun()
    else:
        st.error(body.get("detail") or body)


def render_map(assets: list[dict], selected: dict, by_id: dict) -> None:
    lats = [a["coords"][0] for a in assets]
    lons = [a["coords"][1] for a in assets]
    center = [sum(lats) / len(lats), sum(lons) / len(lons)]
    fmap = folium.Map(
        location=center,
        zoom_start=7,
        tiles="OpenStreetMap",
    )
    for a in assets:
        lat, lon = a["coords"]
        risk = float(a["current_risk"])
        conflict = bool(a.get("conflict_flag"))
        color = risk_color(risk, conflict)
        is_sel = a["id"] == selected["id"]
        radius = 14 if is_sel else (11 if conflict else 8)
        label = display_name(a.get("name"), a["id"])
        status = "Needs attention" if conflict else "OK"
        folium.CircleMarker(
            location=[lat, lon],
            radius=radius,
            color="#111111" if is_sel else color,
            weight=4 if is_sel else (3 if conflict else 1),
            fill=True,
            fill_color=color,
            fill_opacity=0.92,
            popup=folium.Popup(
                f"<b>{label}</b><br/>{status}<br/>Click the dot to select this site.",
                max_width=260,
            ),
            tooltip=f"{label}: {status}",
        ).add_to(fmap)

        if a["id"] == selected["id"]:
            for did in a.get("downstream_ids") or []:
                child = by_id.get(did)
                if not child:
                    continue
                folium.PolyLine(
                    locations=[a["coords"], child["coords"]],
                    color="#5ec8e8",
                    weight=3,
                    opacity=0.85,
                ).add_to(fmap)

    st.markdown('<div class="aegis-map-wrap">', unsafe_allow_html=True)
    event = st_folium(
        fmap,
        width=None,
        height=MAP_HEIGHT,
        returned_objects=["last_object_clicked"],
        key="aegis_map_osm",
    )
    st.markdown("</div>", unsafe_allow_html=True)

    clicked = (event or {}).get("last_object_clicked") if isinstance(event, dict) else None
    if clicked and clicked.get("lat") is not None and clicked.get("lng") is not None:
        nid = _nearest_asset(float(clicked["lat"]), float(clicked["lng"]), assets)
        if nid and nid != st.session_state.get("selected_id"):
            st.session_state.selected_id = nid
            st.rerun()

    st.markdown(
        """
        <div class="aegis-legend">
          <span><span class="aegis-dot" style="background:#2f9e44"></span>Low</span>
          <span><span class="aegis-dot" style="background:#e8590c"></span>Watch</span>
          <span><span class="aegis-dot" style="background:#fa5252"></span>High</span>
          <span><span class="aegis-dot" style="background:#c23b22"></span>Needs attention</span>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.caption("Click a dot to select that site. Lines show where power may go out next.")

    site = display_name(selected.get("name"), selected.get("id", ""))
    st.markdown(f"**Site actions:** {site}")
    c1, c2, c3 = st.columns([1, 1, 1.2])
    with c1:
        if st.button("Reduce load", key="map_quick_l1", use_container_width=True):
            _quick_action(
                selected["id"],
                "load_shed",
                reason="Map quick action: reduce load",
            )
    with c2:
        if st.button("Shut down", key="map_quick_l4", type="primary", use_container_width=True):
            _quick_action(
                selected["id"],
                "deenergize",
                reason="Map quick action: shut down",
            )
    with c3:
        st.caption("Uses demo authorization. Full form with reason is below.")
