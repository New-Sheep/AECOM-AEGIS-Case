"""
Orchestrate realistic telemetry refresh: weather APIs + ETT SCADA proxy → telemetry.csv

Usage:
  python scripts/refresh_telemetry_realistic.py
  python scripts/refresh_telemetry_realistic.py --weather-cache-only
  python scripts/refresh_telemetry_realistic.py --skip-validate
"""

from __future__ import annotations

import argparse
import csv
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
RAW = DATA / "raw"
ASSETS = DATA / "assets.csv"
TELEMETRY = DATA / "telemetry.csv"
WEATHER = RAW / "weather_ian_by_asset.csv"
ETT_SCADA = RAW / "ett_scada_by_asset.csv"
PY = sys.executable


def run(script: str, extra: list[str] | None = None) -> None:
    cmd = [PY, str(ROOT / "scripts" / script), *(extra or [])]
    print(">", " ".join(cmd))
    subprocess.check_call(cmd, cwd=str(ROOT))


def merge_telemetry() -> list[dict]:
    with ASSETS.open(newline="", encoding="utf-8") as f:
        assets = {r["scada_link_id"]: r for r in csv.DictReader(f)}
    with WEATHER.open(newline="", encoding="utf-8") as f:
        weather = {r["scada_link_id"]: r for r in csv.DictReader(f)}
    with ETT_SCADA.open(newline="", encoding="utf-8") as f:
        scada = {r["scada_link_id"]: r for r in csv.DictReader(f)}

    rows = []
    for scada_id, a in assets.items():
        w = weather.get(scada_id)
        s = scada.get(scada_id)
        if not w or not s:
            raise SystemExit(f"Missing weather or ETT row for {scada_id}")
        wind = float(w["wind_speed"])
        surge = float(w["surge_level"])
        # SUB-001 ConflictFlag demo: physics-critical weather
        if a["id"] == "SUB-001":
            wind = max(wind, 115.0)
            surge = max(surge, 12.0)
        rows.append(
            {
                "scada_link_id": scada_id,
                "load": s["load"],
                "oil_temp": s["oil_temp"],
                "voltage": s["voltage"],
                "battery_voltage": s["battery_voltage"],
                "wind_speed": f"{wind:.1f}",
                "surge_level": f"{surge:.2f}",
            }
        )
    return rows


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--weather-cache-only", action="store_true")
    parser.add_argument("--refresh-coops", action="store_true")
    parser.add_argument("--force-ett-download", action="store_true")
    parser.add_argument("--skip-validate", action="store_true")
    args = parser.parse_args()

    wx_extra: list[str] = []
    if args.weather_cache_only:
        wx_extra.append("--cache-only")
    if args.refresh_coops:
        wx_extra.append("--refresh-coops")
    run("build_weather_from_apis.py", wx_extra)

    ett_extra = ["--force-download"] if args.force_ett_download else []
    run("map_ett_to_telemetry.py", ett_extra)

    rows = merge_telemetry()
    with TELEMETRY.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(
            f,
            fieldnames=[
                "scada_link_id",
                "load",
                "oil_temp",
                "voltage",
                "battery_voltage",
                "wind_speed",
                "surge_level",
            ],
        )
        w.writeheader()
        w.writerows(rows)

    winds = [float(r["wind_speed"]) for r in rows]
    surges = [float(r["surge_level"]) for r in rows]
    oils = [float(r["oil_temp"]) for r in rows]
    print(f"Wrote {TELEMETRY} ({len(rows)} rows)")
    print(
        f"  wind mph: mean={sum(winds)/len(winds):.1f} "
        f"min={min(winds):.1f} max={max(winds):.1f}"
    )
    print(
        f"  surge ft: mean={sum(surges)/len(surges):.2f} "
        f"min={min(surges):.2f} max={max(surges):.2f}"
    )
    print(
        f"  oil_temp C: mean={sum(oils)/len(oils):.1f} "
        f"min={min(oils):.1f} max={max(oils):.1f}"
    )
    sub1 = next(r for r in rows if r["scada_link_id"] == "SCADA-0001")
    print(
        f"  SUB-001/SCADA-0001 forced weather: "
        f"wind={sub1['wind_speed']} surge={sub1['surge_level']}"
    )

    if not args.skip_validate:
        run("validate_demo_csvs.py")


if __name__ == "__main__":
    main()
