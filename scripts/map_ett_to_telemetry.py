"""
Map ETT (Electricity Transformer Temperature) samples onto AEGIS telemetry fields.

Downloads ETTh1.csv once into data/raw/ett/, then writes
data/raw/ett_scada_by_asset.csv with oil_temp + load proxies for power assets.

Usage:
  python scripts/map_ett_to_telemetry.py
"""

from __future__ import annotations

import argparse
import csv
import hashlib
from pathlib import Path

import numpy as np
import pandas as pd
import requests

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
RAW = DATA / "raw"
ETT_DIR = RAW / "ett"
ETT_PATH = ETT_DIR / "ETTh1.csv"
ASSETS = DATA / "assets.csv"
OUT = RAW / "ett_scada_by_asset.csv"

# Official mirror used widely in forecasting repos
ETT_URL = (
    "https://raw.githubusercontent.com/zhouhaoyi/ETDataset/main/ETT-small/ETTh1.csv"
)

POWER_TYPES = {"Transformer", "Battery", "Switchgear"}


def ensure_ett(force: bool = False) -> pd.DataFrame:
    ETT_DIR.mkdir(parents=True, exist_ok=True)
    if force or not ETT_PATH.exists():
        print(f"Downloading ETT ETTh1 -> {ETT_PATH}")
        r = requests.get(ETT_URL, timeout=120)
        r.raise_for_status()
        ETT_PATH.write_bytes(r.content)
    df = pd.read_csv(ETT_PATH)
    if "OT" not in df.columns:
        raise SystemExit(f"ETT file missing OT column: {list(df.columns)}")
    return df


def scale_load(raw: float, lo: float, hi: float, out_lo: float = 0.2, out_hi: float = 1.1) -> float:
    if hi <= lo:
        return 0.6
    t = (raw - lo) / (hi - lo)
    t = max(0.0, min(1.0, t))
    return out_lo + t * (out_hi - out_lo)


def asset_index(scada: str, n: int) -> int:
    h = hashlib.sha256(scada.encode("utf-8")).hexdigest()
    return int(h[:8], 16) % n


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--force-download", action="store_true")
    args = parser.parse_args()

    ett = ensure_ett(force=args.force_download)
    load_cols = [c for c in ("HUFL", "HULL", "MUFL", "MULL", "LUFL", "LULL") if c in ett.columns]
    if not load_cols:
        load_cols = [c for c in ett.columns if c not in ("date", "OT")]
    load_series = ett[load_cols].astype(float).mean(axis=1)
    ot = ett["OT"].astype(float)
    load_lo, load_hi = float(load_series.min()), float(load_series.max())
    ot_lo, ot_hi = float(ot.min()), float(ot.max())
    n = len(ett)

    with ASSETS.open(newline="", encoding="utf-8") as f:
        assets = list(csv.DictReader(f))

    rng = np.random.default_rng(42)
    rows = []
    for a in assets:
        scada = a["scada_link_id"]
        atype = a["type"]
        if atype in POWER_TYPES:
            i = asset_index(scada, n)
            # Scale ETT OT into AEGIS oil_temp band (proxy mapping, not Florida SCADA)
            oil = scale_load(float(ot.iloc[i]), ot_lo, ot_hi, out_lo=55.0, out_hi=105.0)
            load = scale_load(float(load_series.iloc[i]), load_lo, load_hi)
            src = f"ETT-ETTh1-row{i}"
        else:
            oil = float(rng.uniform(45.0, 75.0))
            load = float(rng.uniform(0.35, 0.75))
            src = "synthetic-lifeline"

        volt = float(rng.uniform(115.0, 125.0))
        batt = float(rng.uniform(112.0, 132.0))
        rows.append(
            {
                "id": a["id"],
                "scada_link_id": scada,
                "type": atype,
                "load": f"{load:.3f}",
                "oil_temp": f"{oil:.1f}",
                "voltage": f"{volt:.1f}",
                "battery_voltage": f"{batt:.1f}",
                "scada_source": src,
            }
        )

    with OUT.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(
            f,
            fieldnames=[
                "id",
                "scada_link_id",
                "type",
                "load",
                "oil_temp",
                "voltage",
                "battery_voltage",
                "scada_source",
            ],
        )
        w.writeheader()
        w.writerows(rows)
    print(f"Wrote {OUT} ({len(rows)} rows; ETT n={n}, load_cols={load_cols})")


if __name__ == "__main__":
    main()
