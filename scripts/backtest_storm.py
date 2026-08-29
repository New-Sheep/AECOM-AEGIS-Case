"""
AEGIS Sprint 2 backtest — minimize False Negatives.

Lead-time definition (demo):
  For each true failure event, lead_time_hours = max(0, t_failure - t_first_alert)
  where t_first_alert is the first timestep the model risk >= threshold OR physics rule fires.
  We report mean lead_time_hours across true failures that were detected.

Recall = TP / (TP + FN) with positive class = failure within horizon.
"""

from __future__ import annotations

import csv
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "backtest_storm.csv"
THRESHOLD = 0.3


def ensure_fixture() -> None:
    """Synthetic storm timeline if missing."""
    if DATA.exists():
        return
    DATA.parent.mkdir(parents=True, exist_ok=True)
    # asset_id, t_hours, risk_score, physics_fail, failed_at_hour (label)
    rows = [
        # Detected early (good lead time)
        ["A1", 0, 0.2, 0, 10],
        ["A1", 2, 0.45, 0, 10],
        ["A1", 4, 0.7, 1, 10],
        ["A1", 10, 0.9, 1, 10],
        # Detected late
        ["A2", 0, 0.1, 0, 8],
        ["A2", 6, 0.35, 0, 8],
        ["A2", 8, 0.8, 1, 8],
        # False negative: never alerted before failure
        ["A3", 0, 0.05, 0, 5],
        ["A3", 3, 0.15, 0, 5],
        ["A3", 5, 0.2, 0, 5],
        # True negative path (no failure)
        ["A4", 0, 0.1, 0, -1],
        ["A4", 4, 0.2, 0, -1],
        # Physics catches what model misses (counts as detection for ops)
        ["A5", 0, 0.1, 0, 6],
        ["A5", 2, 0.12, 1, 6],
        ["A5", 6, 0.2, 1, 6],
    ]
    with DATA.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(
            ["asset_id", "t_hours", "risk_score", "physics_fail", "failed_at_hour"]
        )
        w.writerows(rows)
    print(f"Wrote fixture {DATA}")


def main() -> None:
    ensure_fixture()
    by_asset: dict[str, list[dict]] = {}
    with DATA.open(newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            by_asset.setdefault(row["asset_id"], []).append(
                {
                    "t": float(row["t_hours"]),
                    "risk": float(row["risk_score"]),
                    "physics": int(row["physics_fail"]) == 1,
                    "fail_at": float(row["failed_at_hour"]),
                }
            )

    tp = fp = fn = tn = 0
    lead_times: list[float] = []

    for asset_id, series in by_asset.items():
        series = sorted(series, key=lambda r: r["t"])
        fail_at = series[0]["fail_at"]
        will_fail = fail_at >= 0

        first_alert_t = None
        for r in series:
            alert = r["risk"] >= THRESHOLD or r["physics"]
            if alert and first_alert_t is None:
                first_alert_t = r["t"]

        predicted_fail = first_alert_t is not None

        if will_fail and predicted_fail:
            tp += 1
            lead_times.append(max(0.0, fail_at - first_alert_t))
        elif will_fail and not predicted_fail:
            fn += 1
        elif not will_fail and predicted_fail:
            fp += 1
        else:
            tn += 1

    recall = tp / (tp + fn) if (tp + fn) else 0.0
    mean_lead = float(np.mean(lead_times)) if lead_times else 0.0

    print("AEGIS backtest (FN-minimization oriented)")
    print(f"  threshold_risk={THRESHOLD}")
    print(f"  TP={tp} FP={fp} FN={fn} TN={tn}")
    print(f"  Recall={recall:.3f}  (goal: maximize; FN are catastrophic)")
    print(f"  Lead-time_hours_mean={mean_lead:.2f}  (t_failure - t_first_alert)")
    print(f"  fixture={DATA}")


if __name__ == "__main__":
    main()
