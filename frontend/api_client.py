"""HTTP helpers for AEGIS Command Center."""

from __future__ import annotations

import os

import requests
import streamlit as st

API_BASE = os.environ.get("AEGIS_API_BASE", "http://127.0.0.1:8000").rstrip("/")


@st.cache_data(ttl=8)
def fetch_json(path: str, params: dict | None = None) -> dict:
    url = f"{API_BASE}{path}"
    resp = requests.get(url, params=params, timeout=45)
    resp.raise_for_status()
    return resp.json()


def post_json(path: str, payload: dict) -> tuple[bool, dict, int]:
    url = f"{API_BASE}{path}"
    resp = requests.post(url, json=payload, timeout=90)
    try:
        body = resp.json()
    except Exception:  # noqa: BLE001
        body = {"detail": resp.text}
    return resp.ok or resp.status_code == 202, body, resp.status_code


def clear_cache() -> None:
    fetch_json.clear()
