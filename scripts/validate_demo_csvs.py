"""Validate joined demo CSVs through preprocess (no training)."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from api.services.data_loader import load_joined_frame  # noqa: E402
from api.services.preprocess import fit_preprocess  # noqa: E402


def main() -> None:
    df = load_joined_frame()
    X, _, report = fit_preprocess(df)
    print(report.summary())
    for w in report.warnings:
        print(f"  warn: {w}")
    if report.n_out == 0:
        raise SystemExit("FAIL: no usable feature rows")
    print(f"OK: {len(X)} feature rows ready for train/infer")


if __name__ == "__main__":
    main()
