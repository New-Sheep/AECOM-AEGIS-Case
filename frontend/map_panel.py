"""Folium GIS map panel."""

from __future__ import annotations

import folium
import streamlit as st
from streamlit_folium import st_folium


def risk_color(risk: float, conflict: bool = False) -> str:
    if conflict:
        return "#c23b22"
    if risk < 0.3:
        return "#2f9e44"
    if risk <= 0.7:
        return "#e8590c"
    return "#fa5252"


def render_map(assets: list[dict], selected: dict, by_id: dict) -> None:
    lats = [a["coords"][0] for a in assets]
    lons = [a["coords"][1] for a in assets]
    center = [sum(lats) / len(lats), sum(lons) / len(lons)]
    fmap = folium.Map(
        location=center,
        zoom_start=7,
        tiles="CartoDB dark_matter",
    )
    for a in assets:
        lat, lon = a["coords"]
        risk = float(a["current_risk"])
        conflict = bool(a.get("conflict_flag"))
        anomaly = bool(a.get("is_anomaly"))
        color = risk_color(risk, conflict)
        is_sel = a["id"] == selected["id"]
        radius = 14 if is_sel else (11 if conflict else 8)
        folium.CircleMarker(
            location=[lat, lon],
            radius=radius,
            color="#f4f7fb" if is_sel else color,
            weight=4 if is_sel else (3 if conflict else 1),
            fill=True,
            fill_color=color,
            fill_opacity=0.92,
            popup=folium.Popup(
                f"<b>{a['name']}</b> ({a['type']})<br/>"
                f"risk={risk:.3f} · conf={a.get('confidence', 0):.2f}<br/>"
                f"conflict={conflict} · anomaly={anomaly}<br/>"
                f"impact={a.get('impact_count', 0)}",
                max_width=300,
            ),
            tooltip=(
                f"{a['id']} · {risk:.2f}"
                + (" · CONFLICT" if conflict else "")
                + (" · ANOMALY" if anomaly else "")
            ),
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

    st_folium(fmap, width=None, height=460, returned_objects=[], key="aegis_map_v2")
    st.markdown(
        """
        <div class="aegis-legend">
          <span><span class="aegis-dot" style="background:#2f9e44"></span>Low (&lt;0.3)</span>
          <span><span class="aegis-dot" style="background:#e8590c"></span>Watch (0.3–0.7)</span>
          <span><span class="aegis-dot" style="background:#fa5252"></span>High (&gt;0.7)</span>
          <span><span class="aegis-dot" style="background:#c23b22"></span>ConflictFlag</span>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.caption(
        "GIS: public SW FL facilities · Weather: Open-Meteo / CO-OPS · "
        "SCADA: ETT oil/load proxy (not utility OT)"
    )
