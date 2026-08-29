"""AEGIS Command Center — SOC visual theme (charcoal / amber / cyan)."""

from __future__ import annotations

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
div[data-testid="stMetric"] {
  background: #121c28; border: 1px solid #243246; border-radius: 10px;
  padding: 0.65rem 0.85rem;
}
div[data-testid="stMetric"] label { color: #8aa0b8 !important; }
div[data-testid="stMetric"] [data-testid="stMetricValue"] {
  color: #f2f6fb !important; font-family: 'IBM Plex Mono', monospace;
  font-size: 1.35rem !important;
}
.threat-CRITICAL div[data-testid="stMetricValue"] { color: #ff8a7a !important; }
.threat-ELEVATED div[data-testid="stMetricValue"] { color: #f0b429 !important; }
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
  margin-top: 0.35rem;
}
.aegis-dot {
  display: inline-block; width: 9px; height: 9px; border-radius: 50%;
  margin-right: 0.3rem; vertical-align: middle;
}
.stTabs [data-baseweb="tab-list"] {
  gap: 0.25rem; background: transparent; border-bottom: 1px solid #243246;
}
.stTabs [data-baseweb="tab"] {
  color: #8aa0b8; background: transparent;
}
.stTabs [aria-selected="true"] {
  color: #5ec8e8 !important; border-bottom: 2px solid #5ec8e8 !important;
}
.stAlert { border-radius: 8px; }
hr { border-color: #243246 !important; }
</style>
"""


def inject_theme() -> None:
    st.markdown(CSS, unsafe_allow_html=True)


def brand_header(*, api_ok: bool, api_base: str) -> None:
    pill = "ok" if api_ok else "crit"
    status = "API ONLINE" if api_ok else "API DOWN"
    st.markdown(
        f"""
        <div class="aegis-brand">
          <span class="mark">AEGIS</span>
          <span class="sub">Shield · Southeastern Grid &amp; Water</span>
          <span class="aegis-pill {pill}">{status}</span>
          <span class="aegis-pill muted">{api_base}</span>
        </div>
        """,
        unsafe_allow_html=True,
    )


def scenario_strip(*, scenario: str, conflict_count: int, data_stack: list[str]) -> None:
    chips = " ".join(
        f'<span class="aegis-chip muted">{s}</span>' for s in (data_stack or [])[:5]
    )
    conflict_chip = (
        f'<span class="aegis-chip crit">ConflictFlag ×{conflict_count}</span>'
        if conflict_count
        else '<span class="aegis-chip ok">No conflicts</span>'
    )
    st.markdown(
        f"""
        <div class="aegis-scenario">
          <span class="aegis-chip cyan">{scenario}</span>
          {conflict_chip}
          {chips}
        </div>
        """,
        unsafe_allow_html=True,
    )


def chip_row(items: list[tuple[str, str]]) -> None:
    """items: list of (label, class) where class in warn|crit|ok|muted|cyan."""
    html = " ".join(
        f'<span class="aegis-chip {cls}">{label}</span>' for label, cls in items
    )
    st.markdown(html, unsafe_allow_html=True)
