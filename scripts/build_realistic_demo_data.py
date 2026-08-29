"""
Build hybrid realistic AEGIS demo CSVs for Hurricane Ian + SW Florida.

Real GIS: EIA-style plants, HIFLD-style hospitals, EPA-style WWTPs (cached under data/raw/).
Storm: Ian track waypoints + NOAA CO-OPS Fort Myers surge peak.
Synthetic: SCADA load/oil_temp/voltage + nearest-lifeline dependencies.

Usage (repo root):
  python scripts/build_realistic_demo_data.py
  python scripts/build_realistic_demo_data.py --refresh-coops
"""

from __future__ import annotations

import argparse
import csv
import json
import math
from pathlib import Path

import numpy as np
import requests

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
RAW = DATA / "raw"

# SW / West-Central Florida focus (Ian impact corridor)
BBOX = dict(lat_min=26.0, lat_max=28.5, lon_min=-82.8, lon_max=-81.2)

COST_BANDS = {
    "Transformer": (1_200_000, 3_200_000),
    "Battery": (800_000, 2_500_000),
    "Switchgear": (400_000, 1_200_000),
    "Hospital": (5_000_000, 15_000_000),
    "WaterPlant": (2_000_000, 8_000_000),
    "Pump": (250_000, 900_000),
}


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    r = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dl = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def in_bbox(lat: float, lon: float) -> bool:
    return (
        BBOX["lat_min"] <= lat <= BBOX["lat_max"]
        and BBOX["lon_min"] <= lon <= BBOX["lon_max"]
    )


def map_plant_type(fuel: str, tech: str) -> str:
    t = (tech or "").lower()
    f = (fuel or "").lower()
    if "batter" in t or f == "battery":
        return "Battery"
    if "substation" in t or "switch" in t:
        return "Switchgear"
    if "solar" in f or "photovoltaic" in t:
        return "Switchgear"
    return "Transformer"


def estimate_elevation(lat: float, lon: float, rng: np.random.Generator) -> float:
    """Coastal DEM heuristic: lower near Gulf (west), higher inland (east)."""
    # Normalize lon within bbox: 0=west(coast), 1=east(inland)
    coastness = (BBOX["lon_max"] - lon) / (BBOX["lon_max"] - BBOX["lon_min"])
    coastness = float(np.clip(coastness, 0.0, 1.0))
    # Lee County barrier islands / Fort Myers Beach very low
    base = 2.0 + 18.0 * (1.0 - coastness) + rng.uniform(-1.5, 2.0)
    if lat < 26.55 and lon < -81.9:
        base = min(base, rng.uniform(1.5, 5.0))
    return float(np.clip(round(base, 1), 1.0, 28.0))


def load_track() -> list[dict]:
    rows = []
    with (RAW / "ian_track.csv").open(newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            rows.append(
                {
                    "lat": float(row["lat"]),
                    "lon": float(row["lon"]),
                    "wind_kt": float(row["wind_kt"]),
                }
            )
    return rows


def load_coops_peaks() -> dict:
    path = RAW / "coops_ian_peaks.json"
    return json.loads(path.read_text(encoding="utf-8"))


def refresh_coops() -> None:
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
        print(f"CO-OPS {sid} {name} peak_ft_msl={peak}")
    (RAW / "coops_ian_peaks.json").write_text(json.dumps(out, indent=2), encoding="utf-8")


def storm_fields(
    lat: float,
    lon: float,
    elev: float,
    track: list[dict],
    fm_peak_ft: float,
    rng: np.random.Generator,
) -> tuple[float, float]:
    """Derive wind_speed (mph) and surge_level (ft) from Ian track + Fort Myers gauge."""
    # Nearest track point
    best = min(track, key=lambda p: haversine_km(lat, lon, p["lat"], p["lon"]))
    dist = haversine_km(lat, lon, best["lat"], best["lon"])
    # Wind decays with distance from eye
    wind_mph = best["wind_kt"] * 1.15078 * math.exp(-dist / 180.0)
    wind_mph = float(np.clip(wind_mph + rng.normal(0, 4), 25.0, 160.0))

    # Surge: scale Fort Myers peak by distance to FM gauge and elevation
    fm_lat, fm_lon = 26.6478, -81.8711
    d_fm = haversine_km(lat, lon, fm_lat, fm_lon)
    spatial = math.exp(-d_fm / 90.0)
    coastal = float(np.clip((BBOX["lon_max"] - lon) / (BBOX["lon_max"] - BBOX["lon_min"]), 0, 1))
    surge = fm_peak_ft * spatial * (0.55 + 0.55 * coastal) * (1.0 - 0.03 * elev)
    surge = float(np.clip(surge + rng.normal(0, 0.4), 0.3, 14.0))
    return round(wind_mph, 1), round(surge, 2)


def cost_for(atype: str, mw: float, rng: np.random.Generator) -> float:
    lo, hi = COST_BANDS[atype]
    base = float(rng.uniform(lo, hi))
    if mw and atype in {"Transformer", "Battery"}:
        base *= 0.85 + min(mw, 2000) / 4000.0
    return float(round(base, -3))


def collect_candidates(rng: np.random.Generator) -> list[dict]:
    items: list[dict] = []

    with (RAW / "eia_plants_swfl.csv").open(newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            lat, lon = float(row["lat"]), float(row["lon"])
            if not in_bbox(lat, lon):
                continue
            atype = map_plant_type(row.get("fuel", ""), row.get("tech", ""))
            items.append(
                {
                    "name": row["name"].strip()[:120],
                    "type": atype,
                    "lat": lat,
                    "lon": lon,
                    "mw": float(row.get("nameplate_mw") or 0),
                    "source": "EIA-style plant/substation cache",
                }
            )

    with (RAW / "hospitals_swfl.csv").open(newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            lat, lon = float(row["lat"]), float(row["lon"])
            if not in_bbox(lat, lon):
                continue
            items.append(
                {
                    "name": row["name"].strip()[:120],
                    "type": "Hospital",
                    "lat": lat,
                    "lon": lon,
                    "mw": 0.0,
                    "source": row.get("source", "hospital cache"),
                }
            )

    with (RAW / "wwtp_swfl.csv").open(newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            lat, lon = float(row["lat"]), float(row["lon"])
            if not in_bbox(lat, lon):
                continue
            ftype = row.get("facility_type") or "WaterPlant"
            if ftype not in {"WaterPlant", "Pump"}:
                ftype = "WaterPlant"
            items.append(
                {
                    "name": row["name"].strip()[:120],
                    "type": ftype,
                    "lat": lat,
                    "lon": lon,
                    "mw": 0.0,
                    "source": row.get("source", "wwtp cache"),
                }
            )

    # Prefer diversity: take all hospitals/wwtp, sample plants to ~50 total
    lifelines = [x for x in items if x["type"] in {"Hospital", "WaterPlant", "Pump"}]
    plants = [x for x in items if x["type"] not in {"Hospital", "WaterPlant", "Pump"}]
    rng.shuffle(plants)
    target_plants = max(35, 50 - len(lifelines))
    chosen = plants[:target_plants] + lifelines
    # Cap at 55
    if len(chosen) > 55:
        # keep all lifelines
        plants_keep = [x for x in chosen if x["type"] not in {"Hospital", "WaterPlant", "Pump"}]
        chosen = plants_keep[: 55 - len(lifelines)] + lifelines
    return chosen


def build(refresh: bool = False) -> None:
    RAW.mkdir(parents=True, exist_ok=True)
    DATA.mkdir(parents=True, exist_ok=True)
    if refresh:
        try:
            refresh_coops()
        except Exception as exc:  # noqa: BLE001
            print(f"CO-OPS refresh failed ({exc}); using cached peaks.")

    rng = np.random.default_rng(42)
    track = load_track()
    peaks = load_coops_peaks()
    fm_peak = float(peaks["stations"]["8725520"]["peak_ft_msl"] or 7.94)

    candidates = collect_candidates(rng)
    # Force first asset to be a coastal low Fort Myers–area transformer for ConflictFlag demo
    candidates.sort(
        key=lambda x: (
            0 if "Fort Myers" in x["name"] and x["type"] == "Transformer" else 1,
            x["name"],
        )
    )

    assets_rows = []
    telem_rows = []
    meta = []

    for i, c in enumerate(candidates):
        ext = f"SUB-{i+1:03d}"
        scada = f"SCADA-{i+1:04d}"
        elev = estimate_elevation(c["lat"], c["lon"], rng)
        # Guarantee SUB-001 is physics-vulnerable (low elev) for demo
        if ext == "SUB-001":
            elev = 5.0
            c["lat"], c["lon"] = 26.4500, -81.9500  # Fort Myers Beach Tap corridor
            c["name"] = "Fort Myers Beach Tap (Ian conflict demo)"
            c["type"] = "Transformer"

        wind, surge = storm_fields(c["lat"], c["lon"], elev, track, fm_peak, rng)
        if ext == "SUB-001":
            # Align with seed ConflictFlag: surge > elev and wind > 100
            wind = max(wind, 115.0)
            surge = max(surge, 12.0)

        stressed = wind > 90 or surge > elev
        oil = float(rng.uniform(85, 108) if stressed else rng.uniform(48, 78))
        load = float(rng.uniform(0.72, 1.05) if stressed else rng.uniform(0.32, 0.78))
        cost = cost_for(c["type"], c["mw"], rng)

        assets_rows.append(
            {
                "id": ext,
                "name": c["name"],
                "type": c["type"],
                "lat": f"{c['lat']:.5f}",
                "lon": f"{c['lon']:.5f}",
                "elevation": f"{elev:.1f}",
                "scada_link_id": scada,
                "replacement_cost": f"{cost:.0f}",
            }
        )
        telem_rows.append(
            {
                "scada_link_id": scada,
                "load": f"{load:.3f}",
                "oil_temp": f"{oil:.1f}",
                "voltage": f"{rng.uniform(115, 125):.1f}",
                "battery_voltage": f"{rng.uniform(112, 132):.1f}",
                "wind_speed": f"{wind:.1f}",
                "surge_level": f"{surge:.2f}",
            }
        )
        meta.append(
            {
                "id": ext,
                "name": c["name"],
                "type": c["type"],
                "source": c["source"],
                "elevation_method": "coastal_heuristic",
                "weather": "Ian track + CO-OPS Fort Myers peak",
            }
        )

    # Dependencies: nearest power parents → each lifeline
    power = [a for a in assets_rows if a["type"] in {"Transformer", "Battery", "Switchgear"}]
    lifelines = [a for a in assets_rows if a["type"] in {"Hospital", "WaterPlant", "Pump"}]
    deps = []
    for child in lifelines:
        scored = []
        for p in power:
            d = haversine_km(
                float(p["lat"]), float(p["lon"]), float(child["lat"]), float(child["lon"])
            )
            scored.append((d, p["id"]))
        scored.sort()
        for _, pid in scored[:3]:
            deps.append({"parent_id": pid, "child_id": child["id"]})
    # Ensure SUB-001 feeds at least one hospital
    hosp = next((a for a in lifelines if a["type"] == "Hospital"), None)
    if hosp:
        deps.append({"parent_id": "SUB-001", "child_id": hosp["id"]})
    # Dedupe
    seen = set()
    dep_rows = []
    for d in deps:
        key = (d["parent_id"], d["child_id"])
        if key in seen or d["parent_id"] == d["child_id"]:
            continue
        seen.add(key)
        dep_rows.append(d)

    assets_path = DATA / "assets.csv"
    telem_path = DATA / "telemetry.csv"
    deps_path = DATA / "dependencies.csv"
    storm_path = DATA / "storm_ian_snapshot.csv"
    meta_path = DATA / "asset_provenance.csv"

    with assets_path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(
            f,
            fieldnames=[
                "id",
                "name",
                "type",
                "lat",
                "lon",
                "elevation",
                "scada_link_id",
                "replacement_cost",
            ],
        )
        w.writeheader()
        w.writerows(assets_rows)

    with telem_path.open("w", newline="", encoding="utf-8") as f:
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
        w.writerows(telem_rows)

    with deps_path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["parent_id", "child_id"])
        w.writeheader()
        w.writerows(dep_rows)

    with storm_path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["iso_time", "lat", "lon", "wind_kt", "status"])
        w.writeheader()
        with (RAW / "ian_track.csv").open(newline="", encoding="utf-8") as src:
            for row in csv.DictReader(src):
                w.writerow(row)

    with meta_path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(
            f, fieldnames=["id", "name", "type", "source", "elevation_method", "weather"]
        )
        w.writeheader()
        w.writerows(meta)

    # Ian-themed backtest fixture
    bt = DATA / "backtest_storm.csv"
    with bt.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(
            ["asset_id", "t_hours", "risk_score", "physics_fail", "failed_at_hour"]
        )
        # Ian landfall timeline (relative hours before peak surge)
        rows = [
            ["SUB-001", 0, 0.18, 0, 10],
            ["SUB-001", 2, 0.22, 1, 10],  # physics early (Old Guard)
            ["SUB-001", 4, 0.55, 1, 10],
            ["SUB-001", 10, 0.88, 1, 10],
            ["SUB-008", 0, 0.15, 0, 9],
            ["SUB-008", 3, 0.40, 0, 9],
            ["SUB-008", 6, 0.72, 1, 9],
            ["SUB-008", 9, 0.85, 1, 9],
            ["SUB-015", 0, 0.08, 0, 7],
            ["SUB-015", 4, 0.12, 0, 7],
            ["SUB-015", 7, 0.18, 0, 7],  # FN path
            ["SUB-022", 0, 0.10, 0, -1],
            ["SUB-022", 5, 0.18, 0, -1],
            ["SUB-030", 0, 0.12, 0, 8],
            ["SUB-030", 2, 0.14, 1, 8],
            ["SUB-030", 8, 0.25, 1, 8],
        ]
        w.writerows(rows)

    n_h = sum(1 for a in assets_rows if a["type"] == "Hospital")
    n_w = sum(1 for a in assets_rows if a["type"] in {"WaterPlant", "Pump"})
    print(f"Wrote {assets_path} ({len(assets_rows)} assets; hospitals={n_h} water/pump={n_w})")
    print(f"Wrote {telem_path}")
    print(f"Wrote {deps_path} ({len(dep_rows)} edges)")
    print(f"Wrote {storm_path}, {meta_path}, {bt}")
    print(f"Ian Fort Myers surge peak used: {fm_peak} ft MSL")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--refresh-coops",
        action="store_true",
        help="Refresh NOAA CO-OPS Ian peaks before build",
    )
    args = parser.parse_args()
    build(refresh=args.refresh_coops)


if __name__ == "__main__":
    main()
