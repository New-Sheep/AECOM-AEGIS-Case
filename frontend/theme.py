"""AEGIS Command Center visual theme (charcoal / amber / cyan)."""

from __future__ import annotations

import html
import re

import streamlit as st

CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@400;500;600;700&family=IBM+Plex+Mono:wght@400;500&display=swap');

html, body, [class*="css"] {
  font-family: 'IBM Plex Sans', system-ui, sans-serif;
}
.stApp {
  background: linear-gradient(165deg, #0b1017 0%, #121a24 42%, #0e1520 100%);
  color: #e8eef6;
}
[data-testid="stSidebar"] {
  background: #0a0f16;
  border-right: 1px solid #1e2a3a;
}
[data-testid="stSidebar"] * { color: #c9d4e3; }
h1, h2, h3 { letter-spacing: 0.02em; color: #f2f6fb !important; }
.aegis-brand {
  display: flex; align-items: baseline; gap: 0.75rem; flex-wrap: wrap;
  margin-bottom: 0.35rem;
}
.aegis-brand .mark {
  font-size: 1.85rem; font-weight: 700; color: #f4f7fb;
  letter-spacing: 0.08em;
}
.aegis-brand .sub {
  font-size: 0.85rem; color: #7f93ab; font-weight: 500;
}
.aegis-pill {
  display: inline-block; padding: 0.15rem 0.55rem; border-radius: 999px;
  font-size: 0.7rem; font-weight: 600; letter-spacing: 0.04em;
  border: 1px solid #2a3b50; background: #152031; color: #9eb6d0;
  font-family: 'IBM Plex Mono', monospace;
}
.aegis-pill.ok { border-color: #1f6f5a; color: #5ddea8; background: #0f2a22; }
.aegis-pill.crit { border-color: #6b2a2a; color: #ff7b72; background: #3a1515; }
.aegis-scenario {
  display: flex; gap: 0.6rem; flex-wrap: wrap; align-items: center;
  margin: 0.4rem 0 0.9rem 0; padding: 0.55rem 0.75rem;
  border: 1px solid #243246; background: rgba(18, 28, 40, 0.85);
  border-radius: 8px;
}
.aegis-chip {
  font-size: 0.72rem; font-weight: 600; padding: 0.2rem 0.5rem;
  border-radius: 4px; font-family: 'IBM Plex Mono', monospace;
}
.aegis-chip.warn { background: #3a2a12; color: #f0b429; border: 1px solid #6a4c14; }
.aegis-chip.crit { background: #3a1515; color: #ff7b72; border: 1px solid #6b2a2a; }
.aegis-chip.ok { background: #123028; color: #5ddea8; border: 1px solid #1f6f5a; }
.aegis-chip.muted { background: #152031; color: #9eb6d0; border: 1px solid #2a3b50; }
.aegis-chip.cyan { background: #0f2a36; color: #5ec8e8; border: 1px solid #1f5f78; }
.aegis-kpi-row {
  display: grid;
  grid-template-columns: repeat(5, minmax(0, 1fr));
  gap: 0.55rem;
  margin: 0.35rem 0 0.85rem 0;
}
@media (max-width: 1100px) {
  .aegis-kpi-row { grid-template-columns: repeat(2, minmax(0, 1fr)); }
}
.aegis-kpi {
  background: #121c28; border: 1px solid #243246; border-radius: 10px;
  padding: 0.55rem 0.7rem; min-width: 0;
}
.aegis-kpi .lbl {
  font-size: 0.72rem; color: #8aa0b8; text-transform: uppercase;
  letter-spacing: 0.05em; margin-bottom: 0.25rem;
}
.aegis-kpi .val {
  font-family: 'IBM Plex Mono', monospace;
  font-size: clamp(0.85rem, 1.4vw, 1.15rem);
  color: #f2f6fb; line-height: 1.25;
  white-space: normal; overflow-wrap: anywhere; word-break: break-word;
}
.aegis-kpi.threat-CRITICAL .val { color: #ff8a7a; }
.aegis-kpi.threat-ELEVATED .val { color: #f0b429; }
.aegis-kpi.threat-WATCH .val { color: #5ec8e8; }
div[data-testid="stMetric"] {
  background: #121c28; border: 1px solid #243246; border-radius: 10px;
  padding: 0.65rem 0.85rem;
}
div[data-testid="stMetric"] label { color: #8aa0b8 !important; }
div[data-testid="stMetric"] [data-testid="stMetricValue"] {
  color: #f2f6fb !important; font-family: 'IBM Plex Mono', monospace;
  font-size: 1.15rem !important; white-space: nowrap;
}
.aegis-card {
  background: #121c28; border: 1px solid #243246; border-radius: 10px;
  padding: 0.85rem 1rem; margin-bottom: 0.75rem;
}
.aegis-card h4 {
  margin: 0 0 0.45rem 0; font-size: 0.8rem; text-transform: uppercase;
  letter-spacing: 0.06em; color: #8aa0b8 !important;
}
.aegis-legend {
  display: flex; gap: 0.85rem; flex-wrap: wrap; font-size: 0.75rem; color: #9eb6d0;
  margin-top: 0.15rem; margin-bottom: 0.35rem;
}
.aegis-dot {
  display: inline-block; width: 9px; height: 9px; border-radius: 50%;
  margin-right: 0.3rem; vertical-align: middle;
}
.stTabs [data-baseweb="tab-list"] {
  gap: 0.15rem; background: transparent; border-bottom: 1px solid #243246;
  flex-wrap: wrap;
}
.stTabs [data-baseweb="tab"] {
  color: #8aa0b8; background: transparent;
  padding-left: 0.55rem; padding-right: 0.55rem;
  font-size: 0.85rem;
}
.stTabs [aria-selected="true"] {
  color: #5ec8e8 !important; border-bottom: 2px solid #5ec8e8 !important;
}
.stAlert { border-radius: 8px; }
hr { border-color: #243246 !important; }

/* Collapse Folium dead space under the map */
.aegis-map-wrap {
  max-height: 320px !important;
  overflow: hidden !important;
  margin-bottom: 0.15rem !important;
  padding-bottom: 0 !important;
}
.aegis-map-wrap iframe,
.aegis-map-wrap div[data-testid="stCustomComponentV1"],
.aegis-map-wrap div[data-testid="stIFrame"] {
  height: 300px !important;
  max-height: 300px !important;
  overflow: hidden !important;
  margin-bottom: 0 !important;
}
div[data-testid="stVerticalBlockBorderWrapper"]:has(.aegis-map-wrap),
div[data-testid="element-container"]:has(.aegis-map-wrap),
.element-container:has(.aegis-map-wrap) {
  margin-bottom: 0 !important;
  padding-bottom: 0 !important;
  gap: 0 !important;
}
iframe[title*="streamlit_folium"],
iframe[title*="folium"] {
  height: 300px !important;
  max-height: 300px !important;
}
</style>
"""

_PAREN_SUFFIX = re.compile(
    r"\s*\((?:[^)]*demo[^)]*|Ian[^)]*|conflict[^)]*)\)\s*",
    re.IGNORECASE,
)
_TAP_SUFFIX = re.compile(r"\s+Tap\s*$", re.IGNORECASE)


def display_name(name: str | None, fallback: str = "") -> str:
    """Short operator-facing site label (strip demo / Ian suffixes)."""
    raw = (name or "").strip() or (fallback or "").strip() or "-"
    cleaned = _PAREN_SUFFIX.sub("", raw).strip()
    cleaned = _TAP_SUFFIX.sub("", cleaned).strip()
    return cleaned or raw


def seriousness(risk: float, conflict: bool = False) -> str:
    if conflict or risk > 0.7:
        return "High"
    if risk > 0.3:
        return "Watch"
    return "Low"


def inject_theme() -> None:
    st.markdown(CSS, unsafe_allow_html=True)


def brand_header(*, api_ok: bool, api_base: str | None = None) -> None:
    _ = api_base
    pill = "ok" if api_ok else "crit"
    status = "API ONLINE" if api_ok else "API DOWN"
    st.markdown(
        f"""
        <div class="aegis-brand">
          <span class="mark">AEGIS</span>
          <span class="sub">Shield · Southeastern Grid &amp; Water</span>
          <span class="aegis-pill {pill}">{status}</span>
        </div>
        """,
        unsafe_allow_html=True,
    )


def kpi_row(
    *,
    threat: str,
    storm: str,
    wind_surge: str,
    dollars: str,
    downstream: str,
) -> None:
    t = html.escape(str(threat or "-"))
    threat_cls = f"threat-{t}" if t in {"CRITICAL", "ELEVATED", "WATCH"} else ""
    cells = [
        ("Threat level", t, threat_cls),
        ("Storm name", html.escape(str(storm or "-")), ""),
        ("Wind / Surge", html.escape(str(wind_surge or "-")), ""),
        ("Est. $ at risk", html.escape(str(dollars or "-")), ""),
        ("Sites affected", html.escape(str(downstream or "-")), ""),
    ]
    parts = []
    for label, value, extra in cells:
        parts.append(
            f'<div class="aegis-kpi {extra}"><div class="lbl">{label}</div>'
            f'<div class="val">{value}</div></div>'
        )
    st.markdown(
        f'<div class="aegis-kpi-row">{"".join(parts)}</div>',
        unsafe_allow_html=True,
    )


def scenario_strip(*, scenario: str, conflict_count: int, data_stack: list[str] | None = None) -> None:
    _ = data_stack
    if conflict_count == 1:
        conflict_chip = '<span class="aegis-chip crit">1 site needs a decision</span>'
    elif conflict_count > 1:
        conflict_chip = (
            f'<span class="aegis-chip crit">{conflict_count} sites need a decision</span>'
        )
    else:
        conflict_chip = '<span class="aegis-chip ok">No sites need attention</span>'
    st.markdown(
        f"""
        <div class="aegis-scenario">
          <span class="aegis-chip cyan">{html.escape(scenario)}</span>
          {conflict_chip}
        </div>
        """,
        unsafe_allow_html=True,
    )


def chip_row(items: list[tuple[str, str]]) -> None:
    html_bits = " ".join(
        f'<span class="aegis-chip {cls}">{html.escape(label)}</span>'
        for label, cls in items
    )
    st.markdown(html_bits, unsafe_allow_html=True)
