"""Anomaly detection via Isolation Forest (scaled features)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest

from api.services.data_loader import ARTIFACTS_DIR, FEATURE_COLS
from api.services.preprocess import (
    load_scaler,
    transform_feature_dict,
)

IFOREST_PATH = ARTIFACTS_DIR / "isolation_forest.joblib"


def train_isolation_forest(
    frame: pd.DataFrame,
    path: Path | None = None,
    *,
    already_scaled: bool = False,
) -> Any:
    """Fit IF. Prefer train_xgb.py (scaled). This helper supports heartbeat --retrain-iforest."""
    if already_scaled:
        X = frame[FEATURE_COLS].astype(float).to_numpy()
    else:
        from sklearn.preprocessing import StandardScaler

        from api.services.preprocess import (
            fit_preprocess,
            save_preprocess_bundle,
            save_scaler,
        )

        X_clean, bundle, _ = fit_preprocess(frame)
        save_preprocess_bundle(bundle)
        scaler = StandardScaler()
        X = scaler.fit_transform(X_clean[FEATURE_COLS])
        save_scaler(scaler)

    model = IsolationForest(
        n_estimators=100,
        contamination=0.08,
        random_state=42,
    )
    model.fit(X)
    out = path or IFOREST_PATH
    out.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(model, out)
    return model


def load_isolation_forest(path: Path | None = None) -> Any:
    model_path = path or IFOREST_PATH
    if not model_path.exists():
        raise FileNotFoundError(
            f"Isolation Forest not found at {model_path}. Run train_xgb.py / heartbeat train."
        )
    return joblib.load(model_path)


def predict_anomaly(model: Any, row: dict[str, float]) -> bool:
    """Preprocess → scale → IsolationForest (-1 = anomaly)."""
    cleaned = transform_feature_dict(row)
    X = pd.DataFrame([[cleaned[c] for c in FEATURE_COLS]], columns=FEATURE_COLS)
    scaler = load_scaler()
    if scaler is not None:
        X_in = scaler.transform(X)
    else:
        X_in = X.to_numpy()
    return int(model.predict(X_in)[0]) == -1


def anomaly_score(model: Any, row: dict[str, float]) -> float:
    """Higher = more anomalous (negated decision_function on scaled space)."""
    cleaned = transform_feature_dict(row)
    X = pd.DataFrame([[cleaned[c] for c in FEATURE_COLS]], columns=FEATURE_COLS)
    scaler = load_scaler()
    X_in = scaler.transform(X) if scaler is not None else X.to_numpy()
    try:
        return float(-model.decision_function(X_in)[0])
    except Exception:  # noqa: BLE001
        return 1.0 if predict_anomaly(model, row) else 0.0
