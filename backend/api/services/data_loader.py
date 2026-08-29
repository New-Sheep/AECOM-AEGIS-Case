"""Shared paths and CSV loading for AEGIS Sprint 1."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[3]
DATA_DIR = REPO_ROOT / "data"
ARTIFACTS_DIR = REPO_ROOT / "artifacts"
MODEL_PATH = ARTIFACTS_DIR / "xgb_risk.joblib"

FEATURE_COLS = ["load", "oil_temp", "wind_speed", "surge_level"]


def load_joined_frame() -> pd.DataFrame:
    assets = pd.read_csv(DATA_DIR / "assets.csv")
    telem = pd.read_csv(DATA_DIR / "telemetry.csv")
    return assets.merge(telem, on="scada_link_id", how="inner")


@lru_cache(maxsize=1)
def cached_joined_frame() -> pd.DataFrame:
    return load_joined_frame()


def clear_data_cache() -> None:
    cached_joined_frame.cache_clear()
