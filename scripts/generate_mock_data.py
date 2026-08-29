"""Generate Sprint-1 mock GIS/SCADA CSVs for AEGIS (~50 assets)."""

from __future__ import annotations

import csv
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"

# Southeast-ish coastal bounding box (demo only)
LAT_MIN, LAT_MAX = 27.5, 32.5
LON_MIN, LON_MAX = -88.5, -79.5

TYPES = (
    ["Transformer"] * 34
    + ["Battery"] * 8
    + ["Switchgear"] * 6
    + ["Hospital", "WaterPlant"]  # lifeline targets (may have light telemetry)
)


def main() -> None:
    DATA.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(42)
    n = 50
    assert len(TYPES) == n

    assets_path = DATA / "assets.csv"
    telem_path = DATA / "telemetry.csv"

    with assets_path.open("w", newline="", encoding="utf-8") as fa, telem_path.open(
        "w", newline="", encoding="utf-8"
    ) as ft:
        aw = csv.DictWriter(
            fa,
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
        tw = csv.DictWriter(
            ft,
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
        aw.writeheader()
        tw.writeheader()

        for i in range(n):
            asset_id = f"SUB-{i+1:03d}"
            scada = f"SCADA-{i+1:04d}"
            lat = float(rng.uniform(LAT_MIN, LAT_MAX))
            lon = float(rng.uniform(LON_MIN, LON_MAX))
            # Mix of flood-vulnerable low sites and higher ground
            elevation = float(rng.choice([2.0, 4.0, 6.0, 8.0, 12.0, 18.0, 25.0]))
            atype = TYPES[i]
            cost = float(rng.choice([5e5, 1e6, 2e6, 3e6]))

            aw.writerow(
                {
                    "id": asset_id,
                    "name": f"{atype} {asset_id}",
                    "type": atype,
                    "lat": f"{lat:.5f}",
                    "lon": f"{lon:.5f}",
                    "elevation": f"{elevation:.1f}",
                    "scada_link_id": scada,
                    "replacement_cost": f"{cost:.0f}",
                }
            )

            # Correlated stress: some sites get high surge / wind / oil temp
            stressed = i % 7 == 0
            surge = float(rng.uniform(8.0, 14.0) if stressed else rng.uniform(0.5, 5.0))
            wind = float(rng.uniform(90.0, 130.0) if stressed else rng.uniform(15.0, 55.0))
            oil = float(rng.uniform(85.0, 110.0) if stressed else rng.uniform(45.0, 75.0))
            load = float(rng.uniform(0.7, 1.05) if stressed else rng.uniform(0.3, 0.75))

            tw.writerow(
                {
                    "scada_link_id": scada,
                    "load": f"{load:.3f}",
                    "oil_temp": f"{oil:.1f}",
                    "voltage": f"{rng.uniform(115.0, 125.0):.1f}",
                    "battery_voltage": f"{rng.uniform(110.0, 130.0):.1f}",
                    "wind_speed": f"{wind:.1f}",
                    "surge_level": f"{surge:.2f}",
                }
            )

    print(f"Wrote {assets_path}")
    print(f"Wrote {telem_path}")


if __name__ == "__main__":
    main()
