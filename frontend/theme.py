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
  /* Allow left-edge collapsedControl to paint; clip only horizontal page scroll */
  overflow-x: clip;
}
html, body, [data-testid="stAppViewContainer"], [data-testid="stMain"], .main {
  max-width: 100vw !important;
}
[data-testid="stMainBlockContainer"] {
  max-width: 100% !important;
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
  grid-template-columns: repeat(6, minmax(0, 1fr));
  gap: 0.55rem;
  margin: 0.35rem 0 0.85rem 0;
}
@media (max-width: 1200px) {
  .aegis-kpi-row { grid-template-columns: repeat(3, minmax(0, 1fr)); }
}
@media (max-width: 700px) {
  .aegis-kpi-row { grid-template-columns: repeat(2, minmax(0, 1fr)); }
}
.aegis-eng-details {
  font-size: 0.85rem;
  line-height: 1.45;
  color: #c5d4e4;
}
.aegis-eng-details h1,
.aegis-eng-details h2,
.aegis-eng-details h3 {
  font-size: 0.95rem !important;
  font-weight: 600;
  margin: 0.55rem 0 0.25rem 0;
  color: #e8eef6;
}
.aegis-eng-details p { margin: 0.25rem 0; }
.aegis-weather-note {
  font-size: 0.82rem; color: #9eb6d0; margin: -0.35rem 0 0.75rem 0;
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
  max-width: 100% !important;
  width: 100% !important;
}
.aegis-map-wrap,
.aegis-map-wrap iframe,
.aegis-map-wrap div[data-testid="stCustomComponentV1"] {
  max-width: 100% !important;
  width: 100% !important;
}

/* Ask AEGIS floating dock — pin ONLY the innermost vertical block that
   directly contains the float marker (never stVerticalBlock ancestors). */
div[data-testid="stVerticalBlock"]:has(> div[data-testid="stElementContainer"] .aegis-ask-float-root) {
  position: fixed !important;
  bottom: 1.1rem !important;
  right: 1.1rem !important;
  width: min(380px, calc(100vw - 2rem)) !important;
  max-height: min(70vh, 640px) !important;
  overflow-x: hidden !important;
  overflow-y: auto !important;
  z-index: 1000 !important;
  background: #0c121a !important;
  border: 1px solid #c0392b !important;
  border-radius: 14px !important;
  padding: 0.65rem 0.75rem 0.85rem 0.75rem !important;
  box-shadow: 0 16px 48px rgba(0, 0, 0, 0.55) !important;
}
div[data-testid="stVerticalBlock"]:has(> div[data-testid="stElementContainer"] .aegis-ask-float-root.aegis-ask-collapsed) {
  width: min(220px, calc(100vw - 2rem)) !important;
  max-height: none !important;
  overflow: visible !important;
  padding: 0.55rem 0.65rem !important;
}
.aegis-ask-float-root {
  display: none;
}
.aegis-ask-shell {
  border: 1px solid #5a2a28;
  border-radius: 10px;
  background: linear-gradient(180deg, #1a1214 0%, #0f1722 100%);
  padding: 0.55rem 0.7rem 0.55rem 0.7rem;
  margin: 0 0 0.45rem 0;
}
.aegis-ask-pill-label {
  margin-bottom: 0.35rem;
}
.aegis-ask-title {
  font-weight: 800; color: #ffe8e4; font-size: 1.05rem;
  letter-spacing: 0.02em;
  margin-bottom: 0.12rem;
}
.aegis-ask-sub {
  color: #c9b4ae; font-size: 0.78rem; margin-bottom: 0;
  line-height: 1.35;
}
.aegis-ask-answer {
  background: #121a24;
  border: 1px solid #2a3b50;
  border-radius: 10px;
  padding: 0.55rem 0.65rem;
  margin: 0.35rem 0 0.55rem 0;
}
/* Hide Streamlit input/form keyboard hints in the dock */
div[data-testid="stVerticalBlock"]:has(> div[data-testid="stElementContainer"] .aegis-ask-float-root)
  [data-testid="InputInstructions"],
div[data-testid="stVerticalBlock"]:has(> div[data-testid="stElementContainer"] .aegis-ask-float-root)
  .stTextInput + div,
div[data-testid="stVerticalBlock"]:has(> div[data-testid="stElementContainer"] .aegis-ask-float-root)
  [data-testid="stCaptionContainer"]:has(+ [data-testid="stTextInput"]) {
  display: none !important;
}
[data-testid="stStatusWidget"] {
  visibility: hidden !important;
  height: 0 !important;
}
/* Do NOT hide stToolbar — Streamlit puts the collapsed-sidebar reopen
   control there. Keep Deploy/Share quieter without removing the host. */
[data-testid="stToolbar"] [data-testid="stAppDeployButton"],
[data-testid="stToolbar"] .stAppDeployButton,
header[data-testid="stHeader"] a[href*="share"] {
  display: none !important;
}
[data-testid="collapsedControl"] {
  visibility: visible !important;
  display: flex !important;
  z-index: 100000 !important;
  opacity: 1 !important;
}
</style>
"""

_PAREN_SUFFIX = re.compile(
    r"\s*\((?:[^)]*demo[^)]*|Ian[^)]*|conflict[^)]*)\)\s*",
    re.IGNORECASE,
)


def display_name(name: str | None, fallback: str = "") -> str:
    """Short operator-facing site label (strip demo / Ian suffixes only)."""
    raw = (name or "").strip() or (fallback or "").strip() or "-"
    cleaned = _PAREN_SUFFIX.sub("", raw).strip()
    return cleaned or raw


def seriousness(risk: float, conflict: bool = False) -> str:
    if conflict or risk > 0.7:
        return "High"
    if risk > 0.3:
        return "Watch"
    return "Low"


def risk_band_label(risk: float, conflict: bool = False) -> str:
    """Match backend impact_economy.risk_band for filters / finders."""
    if conflict:
        return "Needs attention"
    if risk < 0.3:
        return "Low"
    if risk <= 0.7:
        return "Watch"
    return "High"


def inject_theme() -> None:
    st.markdown(CSS, unsafe_allow_html=True)


def brand_header(*, api_ok: bool, api_base: str | None = None) -> None:
    _ = api_base
    # Doc 16: demote healthy API status; only shout when DOWN
    if api_ok:
        st.markdown(
            """
            <div class="aegis-brand">
              <span class="mark">AEGIS</span>
              <span class="sub">Shield · Southeastern Grid &amp; Water</span>
            </div>
            """,
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            """
            <div class="aegis-brand">
              <span class="mark">AEGIS</span>
              <span class="sub">Shield · Southeastern Grid &amp; Water</span>
              <span class="aegis-pill crit">API DOWN</span>
            </div>
            """,
            unsafe_allow_html=True,
        )


def kpi_row(
    *,
    threat: str,
    storm: str,
    wind: str,
    flood_water: str,
    dollars: str,
    downstream: str,
) -> None:
    t = html.escape(str(threat or "-"))
    threat_cls = f"threat-{t}" if t in {"CRITICAL", "ELEVATED", "WATCH"} else ""
    cells = [
        ("Threat level", t, threat_cls),
        ("Storm / scenario", html.escape(str(storm or "-")), ""),
        ("Territory wind", html.escape(str(wind or "-")), ""),
        ("Territory flood", html.escape(str(flood_water or "-")), ""),
        ("Est. $ at risk", html.escape(str(dollars or "-")), ""),
        ("Cascade links", html.escape(str(downstream or "-")), ""),
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


def scenario_strip(
    *,
    scenario: str,
    conflict_count: int,
    high_risk_count: int = 0,
    data_stack: list[str] | None = None,
    sim_label: str | None = None,
) -> None:
    """Top strip: scenario + high-risk count + decision-needed count."""
    _ = data_stack
    if high_risk_count == 1:
        high_chip = '<span class="aegis-chip crit">1 high-risk site</span>'
    elif high_risk_count > 1:
        high_chip = (
            f'<span class="aegis-chip crit">{high_risk_count} high-risk sites</span>'
        )
    else:
        high_chip = ""
    if conflict_count == 1:
        conflict_chip = '<span class="aegis-chip warn">1 site needs a decision</span>'
    elif conflict_count > 1:
        conflict_chip = (
            f'<span class="aegis-chip warn">{conflict_count} sites need a decision</span>'
        )
    else:
        conflict_chip = '<span class="aegis-chip ok">No sites need a decision</span>'
    sim_chip = ""
    if sim_label:
        sim_chip = (
            f'<span class="aegis-chip muted">{html.escape(sim_label)}</span>'
        )
    st.markdown(
        f"""
        <div class="aegis-scenario">
          <span class="aegis-chip cyan">{html.escape(scenario)}</span>
          {sim_chip}
          {high_chip}
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
