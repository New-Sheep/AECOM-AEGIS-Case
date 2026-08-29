"""InferenceService — score assets and compute drivers."""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from api.services.data_loader import FEATURE_COLS
from api.services.predict import load_model, score_features


def top_drivers(model: Any, row: pd.Series, k: int = 3) -> list[dict[str, float | str]]:
    """Simple attribution: |feature_importance * feature_value| ranked."""
    try:
        importances = np.asarray(model.feature_importances_, dtype=float)
    except Exception:
        importances = np.ones(len(FEATURE_COLS)) / len(FEATURE_COLS)

    scored = []
    for name, imp in zip(FEATURE_COLS, importances):
        val = float(row[name])
        scored.append((name, abs(float(imp) * val), val, float(imp)))
    scored.sort(key=lambda x: x[1], reverse=True)
    out = []
    for name, _, val, imp in scored[:k]:
        out.append({"feature": name, "value": round(val, 3), "importance": round(imp, 4)})
    return out


def score_dataframe(frame: pd.DataFrame, model: Any | None = None) -> np.ndarray:
    model = model or load_model()
    return score_features(model, frame)
