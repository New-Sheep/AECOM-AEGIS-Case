"""
Pull Ian-window weather for each asset: Open-Meteo wind + NOAA CO-OPS surge.

Writes data/raw/weather_ian_by_asset.csv and caches Open-Meteo JSON under
data/raw/open_meteo_ian/.

Usage (repo root):
  python scripts/build_weather_from_apis.py
  python scripts/build_weather_from_apis.py --cache-only
  python scripts/build_weather_from_apis.py --refresh-coops
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import time
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
RAW = DATA / "raw"
CACHE = RAW / "open_meteo_ian"
ASSETS = DATA / "assets.csv"
OUT = RAW / "weather_ian_by_asset.csv"
COOPS_PATH = RAW / "coops_ian_peaks.json"
TELEMETRY = DATA / "telemetry.csv"

OPEN_METEO = "https://archive-api.open-meteo.com/v1/archive"
START, END = "2022-09-28", "2022-09-29"
BBOX_LON = (-82.8, -81.2)  # west coast → inland for coastal factor


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    r = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dl = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def grid_key(lat: float, lon: float) -> str:
    return f"{round(lat, 1):.1f}_{round(lon, 1):.1f}"


def refresh_coops() -> dict:
    stations = {
        "8725520": ("Fort Myers", 26.6478, -81.8711),
        "8726724": ("Clearwater Beach", 27.9783, -82.8317),
        "8726674": ("St Petersburg", 27.7606, -82.6269),
    }
    out = {
        "storm": "Hurricane Ian (AL092022)",
        "peak_window": "2022-09-28/29 UTC",
        "stations": {},
        "retrieved_note": "Live refresh from NOAA CO-OPS API.",
    }
    for sid, (name, lat, lon) in stations.items():
        r = requests.get(
            "https://api.tidesandcurrents.noaa.gov/api/prod/datagetter",
            params={
                "product": "water_level",
                "application": "AEGIS",
                "begin_date": "20220928",
                "end_date": "20220929",
                "datum": "MSL",
                "station": sid,
                "time_zone": "gmt",
                "units": "english",
                "format": "json",
            },
            timeout=60,
        )
        r.raise_for_status()
        vals = [
            float(d["v"])
            for d in (r.json().get("data") or [])
            if d.get("v") not in (None, "")
        ]
        peak = max(vals) if vals else None
        out["stations"][sid] = {
            "name": name,
            "lat": lat,
            "lon": lon,
            "peak_ft_msl": peak,
            "source": "NOAA CO-OPS water_level MSL",
        }
        print(f"CO-OPS {sid} {name} peak={peak}")
    COOPS_PATH.write_text(json.dumps(out, indent=2), encoding="utf-8")
    return out


def load_coops() -> dict:
    if not COOPS_PATH.exists():
        raise SystemExit(f"Missing {COOPS_PATH}; run with --refresh-coops once.")
    return json.loads(COOPS_PATH.read_text(encoding="utf-8"))


def fetch_open_meteo_wind(lat: float, lon: float, cache_only: bool) -> tuple[float, str]:
    key = grid_key(lat, lon)
    path = CACHE / f"{key}.json"
    data = None
    if path.exists():
        data = json.loads(path.read_text(encoding="utf-8"))
        source = f"open-meteo-cache:{key}"
    elif cache_only:
        return _fallback_wind(lat, lon)
    else:
        params = {
            "latitude": round(lat, 1),
            "longitude": round(lon, 1),
            "start_date": START,
            "end_date": END,
            "hourly": "wind_speed_10m",
            "wind_speed_unit": "mph",
            "timezone": "UTC",
        }
        try:
            r = requests.get(OPEN_METEO, params=params, timeout=60)
            r.raise_for_status()
            data = r.json()
            CACHE.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps(data), encoding="utf-8")
            source = f"open-meteo:{key}"
            time.sleep(0.15)
        except Exception as exc:  # noqa: BLE001
            print(f"  Open-Meteo fail {key}: {exc}; using fallback")
            return _fallback_wind(lat, lon)

    hourly = (data or {}).get("hourly") or {}
    winds = hourly.get("wind_speed_10m") or []
    winds = [float(w) for w in winds if w is not None]
    if not winds:
        return _fallback_wind(lat, lon)
    # Peak wind during Ian window
    return round(max(winds), 1), source


def _fallback_wind(lat: float, lon: float) -> tuple[float, str]:
    """Ian-track style fallback from existing telemetry if present."""
    if TELEMETRY.exists():
        with TELEMETRY.open(newline="", encoding="utf-8") as f:
            # need scada from assets — approximate by lat distance not available
            pass
    # Distance from Ian landfall ~26.6, -82.2
    d = haversine_km(lat, lon, 26.6, -82.2)
    wind = 130.0 * math.exp(-d / 180.0)
    return round(max(25.0, min(160.0, wind)), 1), "ian-track-fallback"


def surge_for_point(lat: float, lon: float, elev: float, coops: dict) -> tuple[float, str]:
    stations = coops.get("stations") or {}
    if not stations:
        return 2.0, "coops-missing"

    # Inverse-distance weighted peak
    num = 0.0
    den = 0.0
    names = []
    for sid, st in stations.items():
        peak = st.get("peak_ft_msl")
        if peak is None:
            continue
        d = haversine_km(lat, lon, float(st["lat"]), float(st["lon"]))
        w = 1.0 / max(d, 1.0) ** 2
        num += w * float(peak)
        den += w
        names.append(st.get("name", sid))
    if den <= 0:
        return 2.0, "coops-missing"
    base = num / den

    coastal = (BBOX_LON[1] - lon) / (BBOX_LON[1] - BBOX_LON[0])
    coastal = max(0.0, min(1.0, coastal))
    surge = base * (0.55 + 0.55 * coastal) * (1.0 - 0.03 * max(elev, 0.0))
    surge = max(0.3, min(14.0, surge))
    return round(surge, 2), f"coops-idw:{','.join(names[:3])}"


def load_assets() -> list[dict]:
    with ASSETS.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--cache-only",
        action="store_true",
        help="Do not call Open-Meteo; use cache or Ian-track fallback",
    )
    parser.add_argument("--refresh-coops", action="store_true")
    args = parser.parse_args()

    if args.refresh_coops:
        try:
            coops = refresh_coops()
        except Exception as exc:  # noqa: BLE001
            print(f"CO-OPS refresh failed ({exc}); using cache")
            coops = load_coops()
    else:
        coops = load_coops()

    assets = load_assets()
    # Prefetch unique grids
    grids: dict[str, tuple[float, float]] = {}
    for a in assets:
        lat, lon = float(a["lat"]), float(a["lon"])
        grids[grid_key(lat, lon)] = (round(lat, 1), round(lon, 1))

    print(f"Fetching Open-Meteo for {len(grids)} grid cells (cache_only={args.cache_only})")
    wind_by_grid: dict[str, tuple[float, str]] = {}
    for key, (lat, lon) in sorted(grids.items()):
        wind_by_grid[key] = fetch_open_meteo_wind(lat, lon, args.cache_only)
        print(f"  {key}: wind={wind_by_grid[key][0]} ({wind_by_grid[key][1]})")

    rows = []
    for a in assets:
        lat, lon = float(a["lat"]), float(a["lon"])
        elev = float(a.get("elevation") or 10.0)
        key = grid_key(lat, lon)
        wind, wsrc = wind_by_grid[key]
        surge, ssrc = surge_for_point(lat, lon, elev, coops)
        rows.append(
            {
                "id": a["id"],
                "scada_link_id": a["scada_link_id"],
                "wind_speed": f"{wind:.1f}",
                "surge_level": f"{surge:.2f}",
                "wind_source": wsrc,
                "surge_source": ssrc,
            }
        )

    RAW.mkdir(parents=True, exist_ok=True)
    with OUT.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(
            f,
            fieldnames=[
                "id",
                "scada_link_id",
                "wind_speed",
                "surge_level",
                "wind_source",
                "surge_source",
            ],
        )
        w.writeheader()
        w.writerows(rows)
    print(f"Wrote {OUT} ({len(rows)} rows)")


if __name__ == "__main__":
    main()
