"""Train XGBoost + Isolation Forest with preprocess + retrain-only-when-needed."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler
from xgboost import XGBRegressor

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
sys.path.insert(0, str(BACKEND))

from api.services.anomaly import IFOREST_PATH  # noqa: E402
from api.services.data_loader import (  # noqa: E402
    ARTIFACTS_DIR,
    FEATURE_COLS,
    MODEL_PATH,
    load_joined_frame,
)
from api.services.predict import synthetic_risk_label  # noqa: E402
from api.services.preprocess import (  # noqa: E402
    fingerprint,
    fit_preprocess,
    save_preprocess_bundle,
    save_scaler,
    should_retrain,
    write_fingerprint,
)


def _labels_for_cleaned(df: pd.DataFrame, X_clean: pd.DataFrame) -> pd.Series:
    """Align synthetic labels with cleaned feature rows (same drop-all-NaN mask)."""
    raw = df[FEATURE_COLS].apply(pd.to_numeric, errors="coerce")
    mask = ~raw.isna().all(axis=1)
    label_frame = X_clean.copy()
    if "elevation" in df.columns:
        elev = df.loc[mask, "elevation"].reset_index(drop=True)
        if len(elev) != len(X_clean):
            elev = elev.iloc[: len(X_clean)].reset_index(drop=True)
        label_frame["elevation"] = elev.to_numpy()
    else:
        label_frame["elevation"] = 10.0
    return label_frame.apply(synthetic_risk_label, axis=1).astype(float)


def main() -> None:
    parser = argparse.ArgumentParser(description="Train AEGIS risk models")
    parser.add_argument(
        "--force",
        action="store_true",
        help="Retrain even if training fingerprint is unchanged",
    )
    args = parser.parse_args()

    df = load_joined_frame()
    X_clean, bundle, report = fit_preprocess(df)
    print(report.summary())
    for w in report.warnings:
        print(f"  warn: {w}")

    if X_clean.empty:
        raise SystemExit("Preprocess left zero rows; cannot train.")

    fp = fingerprint(X_clean)
    if not should_retrain(X_clean, force=args.force):
        print(
            f"Skipping train (fingerprint unchanged: {fp[:12]}…); "
            "pass --force to retrain."
        )
        return

    y = _labels_for_cleaned(df, X_clean)

    model = XGBRegressor(
        n_estimators=40,
        max_depth=3,
        learning_rate=0.15,
        objective="reg:squarederror",
        random_state=42,
    )
    model.fit(X_clean[FEATURE_COLS], y)
    pred = np.clip(model.predict(X_clean[FEATURE_COLS]), 0.0, 1.0)
    mae = float(np.mean(np.abs(pred - y.to_numpy())))

    ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)
    joblib.dump(model, MODEL_PATH)
    save_preprocess_bundle(bundle)
    write_fingerprint(fp)

    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X_clean[FEATURE_COLS])
    save_scaler(scaler)

    iforest = IsolationForest(
        n_estimators=100,
        contamination=0.08,
        random_state=42,
    )
    iforest.fit(X_scaled)
    joblib.dump(iforest, IFOREST_PATH)

    print(f"Saved {MODEL_PATH}")
    print(f"Saved preprocess + scaler + fingerprint ({fp[:12]}…)")
    print(f"Saved {IFOREST_PATH}")
    print(f"Train MAE vs synthetic labels: {mae:.4f}")
    print(f"Sample scores: {pred[:5].round(3).tolist()}")


if __name__ == "__main__":
    main()
