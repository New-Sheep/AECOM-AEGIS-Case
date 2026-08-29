"""
Evaluate AEGIS XGBoost risk model on cleaned features.

- Continuous: MAE vs synthetic_risk_label
- Binary (threshold): accuracy, precision, recall, F1 (pos=high-risk), macro-F1
- Imbalance: class counts / rates after thresholding labels

Primary product metric remains Recall (minimize false negatives).
Holdout is a small random split for honesty — still synthetic labels on ~50 rows.

Usage (repo root):
  python scripts/eval_risk_model.py
  python scripts/eval_risk_model.py --threshold 0.3 --holdout 0.25
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.metrics import (
    accuracy_score,
    f1_score,
    mean_absolute_error,
    precision_score,
    recall_score,
)
from sklearn.model_selection import train_test_split

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
sys.path.insert(0, str(BACKEND))

from api.services.data_loader import FEATURE_COLS, MODEL_PATH, load_joined_frame  # noqa: E402
from api.services.predict import load_model, synthetic_risk_label  # noqa: E402
from api.services.preprocess import fit_preprocess, load_preprocess_bundle, transform_preprocess  # noqa: E402


def _labels_for_cleaned(df: pd.DataFrame, X_clean: pd.DataFrame) -> np.ndarray:
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
    return label_frame.apply(synthetic_risk_label, axis=1).astype(float).to_numpy()


def _binary_report(y_true: np.ndarray, y_pred: np.ndarray, title: str) -> None:
    # Avoid undefined metrics on empty positive class
    pos = int(y_true.sum())
    print(f"\n{title}")
    print(f"  n={len(y_true)}  positives(label)={pos} ({100.0 * pos / max(len(y_true), 1):.1f}%)")
    print(f"  accuracy = {accuracy_score(y_true, y_pred):.3f}")
    print(
        f"  precision(pos) = {precision_score(y_true, y_pred, zero_division=0):.3f}"
    )
    print(f"  recall(pos)    = {recall_score(y_true, y_pred, zero_division=0):.3f}")
    print(f"  f1(pos)        = {f1_score(y_true, y_pred, zero_division=0):.3f}")
    print(
        f"  macro_f1       = {f1_score(y_true, y_pred, average='macro', zero_division=0):.3f}"
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Eval AEGIS risk model")
    parser.add_argument(
        "--threshold",
        type=float,
        default=0.3,
        help="Risk threshold for binary high-risk class (default 0.3)",
    )
    parser.add_argument(
        "--holdout",
        type=float,
        default=0.25,
        help="Holdout fraction for split metrics (0 = full-sample only)",
    )
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    if not MODEL_PATH.exists():
        raise SystemExit(f"Missing {MODEL_PATH}. Run: python scripts/train_xgb.py --force")

    df = load_joined_frame()
    bundle = load_preprocess_bundle()
    X_clean, report = transform_preprocess(df, bundle)
    # If preprocess was never fit on current data, fit for eval display only
    if report.n_out == 0:
        X_clean, bundle, report = fit_preprocess(df)

    print("AEGIS risk model eval (cleaned features)")
    print(report.summary())
    if X_clean.empty:
        raise SystemExit("No rows after preprocess")

    y_cont = _labels_for_cleaned(df, X_clean)
    model = load_model()
    y_hat = np.clip(model.predict(X_clean[FEATURE_COLS]), 0.0, 1.0)

    thr = float(args.threshold)
    y_bin = (y_cont >= thr).astype(int)
    p_bin = (y_hat >= thr).astype(int)

    n = len(y_bin)
    n_pos = int(y_bin.sum())
    n_neg = n - n_pos
    print("\n=== Imbalance (label risk >= threshold) ===")
    print(f"  threshold = {thr}")
    print(f"  high-risk (1): {n_pos}  ({100.0 * n_pos / n:.1f}%)")
    print(f"  low-risk  (0): {n_neg}  ({100.0 * n_neg / n:.1f}%)")
    if n_pos == 0 or n_neg == 0:
        print("  WARN: single-class labels — F1/precision may be degenerate.")

    print("\n=== Continuous (full sample) ===")
    print(f"  MAE = {mean_absolute_error(y_cont, y_hat):.4f}")
    print(f"  pred mean/std = {float(y_hat.mean()):.3f} / {float(y_hat.std()):.3f}")
    print(f"  label mean/std = {float(y_cont.mean()):.3f} / {float(y_cont.std()):.3f}")

    _binary_report(y_bin, p_bin, "=== Binary metrics (full sample; optimistic) ===")
    print("  note: full-sample metrics overfit easily on ~50 synthetic rows.")

    if args.holdout and 0.0 < args.holdout < 0.5 and n >= 8:
        # Stratify when both classes present
        strat = y_bin if n_pos > 1 and n_neg > 1 else None
        try:
            X_tr, X_te, y_tr, y_te, yt_tr, yt_te = train_test_split(
                X_clean[FEATURE_COLS],
                y_cont,
                y_bin,
                test_size=args.holdout,
                random_state=args.seed,
                stratify=strat,
            )
        except ValueError:
            X_tr, X_te, y_tr, y_te, yt_tr, yt_te = train_test_split(
                X_clean[FEATURE_COLS],
                y_cont,
                y_bin,
                test_size=args.holdout,
                random_state=args.seed,
            )
        # Evaluate *current* saved model on holdout (not refit) — honest for deployed artifact
        y_hat_te = np.clip(model.predict(X_te), 0.0, 1.0)
        p_te = (y_hat_te >= thr).astype(int)
        print(f"\n=== Holdout ({args.holdout:.0%} of rows, seed={args.seed}) ===")
        print(f"  holdout MAE = {mean_absolute_error(y_te, y_hat_te):.4f}")
        _binary_report(np.asarray(yt_te), p_te, "=== Binary metrics (holdout) ===")
        print("  note: model was trained on (mostly) overlapping data; treat as demo QA.")
    elif args.holdout:
        print("\nHoldout skipped (need more rows or set --holdout between 0 and 0.5).")

    print("\nProduct priority: maximize Recall (FN costly); manage precision for trust.")


if __name__ == "__main__":
    main()
