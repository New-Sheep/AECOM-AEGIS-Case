"""XGBoost risk scoring helpers (cleaned raw features, no IF scaler)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd

from api.services.data_loader import FEATURE_COLS, MODEL_PATH
from api.services.preprocess import load_preprocess_bundle, transform_feature_dict, transform_preprocess


def synthetic_risk_label(row: pd.Series) -> float:
    """Physics-ish label so XGBoost has a learnable surface (demo only)."""
    elev = float(row["elevation"]) if "elevation" in row.index else 10.0
    surge = float(row["surge_level"])
    wind = float(row["wind_speed"])
    oil = float(row["oil_temp"])
    load = float(row["load"])

    flood = max(0.0, (surge - elev) / 10.0)
    wind_f = max(0.0, (wind - 60.0) / 80.0)
    thermal = max(0.0, (oil - 70.0) / 50.0)
    load_f = max(0.0, (load - 0.5) / 0.6)
    raw = 0.35 * flood + 0.25 * wind_f + 0.25 * thermal + 0.15 * load_f
    return float(np.clip(raw, 0.0, 1.0))


def load_model(path: Path | None = None) -> Any:
    model_path = path or MODEL_PATH
    if not model_path.exists():
        raise FileNotFoundError(
            f"Model not found at {model_path}. Run: python scripts/train_xgb.py"
        )
    return joblib.load(model_path)


def score_features(model: Any, frame: pd.DataFrame) -> np.ndarray:
    cleaned, _ = transform_preprocess(frame, load_preprocess_bundle())
    if cleaned.empty:
        return np.array([], dtype=float)
    pred = model.predict(cleaned[FEATURE_COLS])
    return np.clip(np.asarray(pred, dtype=float), 0.0, 1.0)


def score_row(
    model: Any,
    load: float,
    oil_temp: float,
    wind_speed: float,
    surge_level: float,
) -> float:
    feat = transform_feature_dict(
        {
            "load": load,
            "oil_temp": oil_temp,
            "wind_speed": wind_speed,
            "surge_level": surge_level,
        }
    )
    X = pd.DataFrame([[feat[c] for c in FEATURE_COLS]], columns=FEATURE_COLS)
    pred = model.predict(X)
    return float(np.clip(np.asarray(pred, dtype=float)[0], 0.0, 1.0))
