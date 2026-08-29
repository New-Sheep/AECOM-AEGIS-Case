"""Load Ian weather + ETT SCADA provenance sidecars for UI captions."""

from __future__ import annotations

import csv
from functools import lru_cache
from pathlib import Path
from typing import Any

from api.services.data_loader import REPO_ROOT

RAW = REPO_ROOT / "data" / "raw"
WEATHER_CSV = RAW / "weather_ian_by_asset.csv"
ETT_CSV = RAW / "ett_scada_by_asset.csv"

DATA_STACK = [
    "Open-Meteo wind (Ian window)",
    "NOAA CO-OPS surge (IDW)",
    "ETT oil/load proxy (not SGW SCADA)",
    "XGBoost + Isolation Forest",
    "LangGraph + NVIDIA NIM briefs",
]

SCENARIO = "Hurricane Ian · SW Florida"


@lru_cache(maxsize=1)
def _weather_by_key() -> dict[str, dict[str, str]]:
    if not WEATHER_CSV.exists():
        return {}
    out: dict[str, dict[str, str]] = {}
    with WEATHER_CSV.open(newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            rec = {
                "wind_source": row.get("wind_source") or "",
                "surge_source": row.get("surge_source") or "",
            }
            if row.get("id"):
                out[row["id"]] = rec
            if row.get("scada_link_id"):
                out[row["scada_link_id"]] = rec
    return out


@lru_cache(maxsize=1)
def _ett_by_key() -> dict[str, dict[str, str]]:
    if not ETT_CSV.exists():
        return {}
    out: dict[str, dict[str, str]] = {}
    with ETT_CSV.open(newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            rec = {"scada_source": row.get("scada_source") or ""}
            if row.get("id"):
                out[row["id"]] = rec
            if row.get("scada_link_id"):
                out[row["scada_link_id"]] = rec
    return out


def asset_provenance(
    *, asset_id: str | None = None, scada_link_id: str | None = None
) -> dict[str, Any]:
    """Return wind/surge/scada source tags for an asset (best-effort)."""
    wx = _weather_by_key()
    ett = _ett_by_key()
    w = {}
    e = {}
    for key in (asset_id, scada_link_id):
        if key and key in wx:
            w = wx[key]
            break
    for key in (asset_id, scada_link_id):
        if key and key in ett:
            e = ett[key]
            break
    return {
        "wind_source": w.get("wind_source") or "unknown",
        "surge_source": w.get("surge_source") or "unknown",
        "scada_source": e.get("scada_source") or "unknown",
    }


def clear_provenance_cache() -> None:
    _weather_by_key.cache_clear()
    _ett_by_key.cache_clear()
