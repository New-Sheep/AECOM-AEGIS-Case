"""HTTP helpers for AEGIS Command Center."""

from __future__ import annotations

import os
from typing import Any

import requests
import streamlit as st

API_BASE = os.environ.get("AEGIS_API_BASE", "http://127.0.0.1:8000").rstrip("/")


def _get_spinner_message(path: str) -> str:
    p = path.lower()
    if "/dashboard/header" in p:
        return "Loading storm status…"
    if "/risk_map" in p:
        return "Loading site risk map…"
    if "/health" in p:
        return "Checking API connection…"
    if "/forecast" in p:
        return "Loading site forecast…"
    if "/action_brief" in p:
        return "Building site summary…"
    return "Loading data…"


def _post_spinner_message(path: str) -> str:
    p = path.lower()
    if "/assistant/chat" in p:
        return "Ask AEGIS is answering…"
    if "/control/" in p or "/shutdown" in p:
        return "Recording your decision…"
    if "/scenario/" in p:
        return "Updating the live scenario…"
    if "/anomaly" in p:
        return "Checking sensors…"
    return "Working…"


@st.cache_data(ttl=8, show_spinner=False)
def _cached_get(path: str, params_items: tuple[tuple[str, Any], ...] | None) -> dict:
    url = f"{API_BASE}{path}"
    params = dict(params_items) if params_items else None
    resp = requests.get(url, params=params, timeout=45)
    resp.raise_for_status()
    return resp.json()


def fetch_json(path: str, params: dict | None = None) -> dict:
    """GET JSON with a plain-language spinner (not the raw function name)."""
    items = tuple(sorted((params or {}).items())) if params else None
    with st.spinner(_get_spinner_message(path)):
        return _cached_get(path, items)


def post_json(
    path: str,
    payload: dict,
    *,
    spinner: str | bool | None = None,
) -> tuple[bool, dict, int]:
    """POST JSON. Pass spinner=False to suppress (e.g. quiet background ticks)."""
    if spinner is False:
        return _do_post(path, payload)
    msg = spinner if isinstance(spinner, str) else _post_spinner_message(path)
    with st.spinner(msg):
        return _do_post(path, payload)


def _do_post(path: str, payload: dict) -> tuple[bool, dict, int]:
    url = f"{API_BASE}{path}"
    resp = requests.post(url, json=payload, timeout=90)
    try:
        body = resp.json()
    except Exception:  # noqa: BLE001
        body = {"detail": resp.text}
    return resp.ok or resp.status_code == 202, body, resp.status_code


def clear_cache() -> None:
    _cached_get.clear()
