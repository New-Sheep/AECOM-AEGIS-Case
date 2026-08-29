"""Feature preprocess: validate / impute / clip + train fingerprint gate."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd
from sklearn.preprocessing import StandardScaler

from api.services.data_loader import ARTIFACTS_DIR, FEATURE_COLS, MODEL_PATH

PREPROCESS_VERSION = "1"
PREPROCESS_PATH = ARTIFACTS_DIR / "preprocess.joblib"
SCALER_PATH = ARTIFACTS_DIR / "iforest_scaler.joblib"
FINGERPRINT_PATH = ARTIFACTS_DIR / "train_fingerprint.txt"
IFOREST_PATH = ARTIFACTS_DIR / "isolation_forest.joblib"

FEATURE_RANGES: dict[str, tuple[float, float]] = {
    "load": (0.0, 1.5),
    "oil_temp": (0.0, 150.0),
    "wind_speed": (0.0, 200.0),
    "surge_level": (0.0, 20.0),
}


@dataclass
class PreprocessReport:
    n_in: int = 0
    n_out: int = 0
    n_imputed: int = 0
    n_clipped: int = 0
    warnings: list[str] = field(default_factory=list)

    def summary(self) -> str:
        return (
            f"preprocess: in={self.n_in} out={self.n_out} "
            f"imputed_cells={self.n_imputed} clipped_cells={self.n_clipped}"
        )


def _ensure_feature_frame(frame: pd.DataFrame) -> pd.DataFrame:
    missing = [c for c in FEATURE_COLS if c not in frame.columns]
    if missing:
        raise ValueError(f"Missing feature columns: {missing}")
    return frame[FEATURE_COLS].copy()


def fit_preprocess(
    frame: pd.DataFrame,
) -> tuple[pd.DataFrame, dict[str, Any], PreprocessReport]:
    """Fit medians on training features; return cleaned X + bundle + report."""
    report = PreprocessReport()
    raw = _ensure_feature_frame(frame)
    report.n_in = len(raw)

    X = raw.apply(pd.to_numeric, errors="coerce")
    all_nan = X.isna().all(axis=1)
    if all_nan.any():
        report.warnings.append(f"dropped {int(all_nan.sum())} rows with all-NaN features")
        X = X.loc[~all_nan].copy()

    medians = {c: float(X[c].median()) if X[c].notna().any() else 0.0 for c in FEATURE_COLS}
    # If entire column NaN after drop, median is 0.0
    n_imputed = int(X.isna().sum().sum())
    X = X.fillna(medians)
    report.n_imputed = n_imputed

    n_clipped = 0
    for col, (lo, hi) in FEATURE_RANGES.items():
        before = X[col].copy()
        X[col] = X[col].clip(lo, hi)
        n_clipped += int((before != X[col]).sum())
    report.n_clipped = n_clipped
    report.n_out = len(X)

    if report.n_out == 0:
        report.warnings.append("no rows left after preprocess")

    bundle = {
        "version": PREPROCESS_VERSION,
        "medians": medians,
        "ranges": FEATURE_RANGES,
        "feature_cols": list(FEATURE_COLS),
    }
    return X.reset_index(drop=True), bundle, report


def transform_preprocess(
    frame: pd.DataFrame,
    bundle: dict[str, Any] | None = None,
) -> tuple[pd.DataFrame, PreprocessReport]:
    """Apply saved medians + clip (inference)."""
    report = PreprocessReport()
    bundle = bundle or load_preprocess_bundle()
    raw = _ensure_feature_frame(frame)
    report.n_in = len(raw)

    X = raw.apply(pd.to_numeric, errors="coerce")
    all_nan = X.isna().all(axis=1)
    if all_nan.any():
        report.warnings.append(f"dropped {int(all_nan.sum())} rows with all-NaN features")
        X = X.loc[~all_nan].copy()

    medians = bundle.get("medians") or {c: 0.0 for c in FEATURE_COLS}
    n_imputed = int(X.isna().sum().sum())
    X = X.fillna({c: float(medians.get(c, 0.0)) for c in FEATURE_COLS})
    report.n_imputed = n_imputed

    ranges = bundle.get("ranges") or FEATURE_RANGES
    n_clipped = 0
    for col in FEATURE_COLS:
        lo, hi = ranges.get(col, FEATURE_RANGES[col])
        before = X[col].copy()
        X[col] = X[col].clip(float(lo), float(hi))
        n_clipped += int((before != X[col]).sum())
    report.n_clipped = n_clipped
    report.n_out = len(X)
    return X.reset_index(drop=True), report


def transform_feature_dict(
    feat: dict[str, float],
    bundle: dict[str, Any] | None = None,
) -> dict[str, float]:
    """Clean a single feature dict for XGB / IF input."""
    frame = pd.DataFrame([{c: feat.get(c) for c in FEATURE_COLS}])
    cleaned, _ = transform_preprocess(frame, bundle)
    if cleaned.empty:
        return {c: 0.0 for c in FEATURE_COLS}
    row = cleaned.iloc[0]
    return {c: float(row[c]) for c in FEATURE_COLS}


def save_preprocess_bundle(bundle: dict[str, Any], path: Path | None = None) -> Path:
    out = path or PREPROCESS_PATH
    out.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(bundle, out)
    return out


def load_preprocess_bundle(path: Path | None = None) -> dict[str, Any]:
    p = path or PREPROCESS_PATH
    if not p.exists():
        # Fallback defaults so inference still clips before first train
        return {
            "version": PREPROCESS_VERSION,
            "medians": {c: 0.0 for c in FEATURE_COLS},
            "ranges": FEATURE_RANGES,
            "feature_cols": list(FEATURE_COLS),
        }
    return joblib.load(p)


def fingerprint(X_clean: pd.DataFrame) -> str:
    """Stable hash of preprocess version + feature schema + rounded matrix."""
    rounded = X_clean[FEATURE_COLS].astype(float).round(6)
    payload = PREPROCESS_VERSION + "|" + ",".join(FEATURE_COLS) + "\n"
    payload += rounded.to_csv(index=False)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def read_fingerprint(path: Path | None = None) -> str | None:
    p = path or FINGERPRINT_PATH
    if not p.exists():
        return None
    return p.read_text(encoding="utf-8").strip() or None


def write_fingerprint(fp: str, path: Path | None = None) -> Path:
    out = path or FINGERPRINT_PATH
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(fp + "\n", encoding="utf-8")
    return out


def required_model_files_exist() -> bool:
    return all(
        p.exists()
        for p in (MODEL_PATH, IFOREST_PATH, PREPROCESS_PATH, SCALER_PATH, FINGERPRINT_PATH)
    )


def should_retrain(X_clean: pd.DataFrame, force: bool = False) -> bool:
    """False when fingerprint matches stamp and all artifacts exist."""
    if force:
        return True
    if not required_model_files_exist():
        return True
    current = fingerprint(X_clean)
    stored = read_fingerprint()
    return stored != current


def save_scaler(scaler: StandardScaler, path: Path | None = None) -> Path:
    out = path or SCALER_PATH
    out.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(scaler, out)
    return out


def load_scaler(path: Path | None = None) -> StandardScaler | None:
    p = path or SCALER_PATH
    if not p.exists():
        return None
    return joblib.load(p)
