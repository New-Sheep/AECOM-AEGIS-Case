"""Shared demo map diversify logic (management command + scenario reset)."""

from __future__ import annotations

import random
from typing import Any

from django.db import transaction

from api.models import Asset, Telemetry, WeatherContext


def legend_bucket(risk: float, conflict: bool) -> str:
    if conflict:
        return "Needs attention"
    if risk < 0.3:
        return "Low"
    if risk <= 0.7:
        return "Watch"
    return "High"


def _apply_band(asset: Asset, band: str, rng: random.Random) -> None:
    elev = float(asset.elevation)

    if band == "attention":
        conflict = True
        risk = round(rng.uniform(0.15, 0.40), 3)
        wind = round(rng.uniform(105.0, 130.0), 1)
        surge = round(max(elev + rng.uniform(0.5, 4.0), elev + 0.5), 2)
        oil = round(rng.uniform(70.0, 92.0), 1)
        load = round(rng.uniform(0.45, 0.85), 3)
        drivers = ["surge_level", "wind_speed"]
    elif band == "low":
        conflict = False
        risk = round(rng.uniform(0.05, 0.25), 3)
        wind = round(rng.uniform(25.0, 55.0), 1)
        surge = round(min(elev * 0.4, elev - 0.5) if elev > 1 else 0.3, 2)
        surge = max(0.1, surge)
        oil = round(rng.uniform(45.0, 70.0), 1)
        load = round(rng.uniform(0.35, 0.65), 3)
        drivers = ["load"]
    elif band == "watch":
        conflict = False
        risk = round(rng.uniform(0.35, 0.65), 3)
        wind = round(rng.uniform(60.0, 95.0), 1)
        surge = round(rng.uniform(max(0.5, elev * 0.5), max(elev * 0.9, 1.0)), 2)
        oil = round(rng.uniform(72.0, 90.0), 1)
        load = round(rng.uniform(0.55, 0.85), 3)
        drivers = ["oil_temp", "wind_speed"]
    else:
        conflict = False
        risk = round(rng.uniform(0.75, 0.95), 3)
        wind = round(rng.uniform(85.0, 115.0), 1)
        surge = round(rng.uniform(max(1.0, elev * 0.7), max(elev + 0.2, 2.0)), 2)
        oil = round(rng.uniform(88.0, 105.0), 1)
        load = round(rng.uniform(0.7, 0.95), 3)
        drivers = ["oil_temp", "load", "wind_speed"]

    asset.risk_score = risk
    asset.conflict_flag = conflict
    asset.confidence = round(rng.uniform(0.55, 0.9), 3)
    asset.drivers_json = drivers
    asset.operational_state = Asset.OperationalState.NORMAL
    asset.baseline_load = None
    asset.save(
        update_fields=[
            "risk_score",
            "conflict_flag",
            "confidence",
            "drivers_json",
            "operational_state",
            "baseline_load",
        ]
    )

    tel = Telemetry.objects.filter(asset=asset).order_by("-timestamp").first()
    if tel is None:
        Telemetry.objects.create(
            asset=asset,
            load=load,
            oil_temp=oil,
            voltage=120.0,
            battery_voltage=125.0,
            is_anomaly=band in {"high", "attention"},
        )
    else:
        tel.load = load
        tel.oil_temp = oil
        tel.is_anomaly = band in {"high", "attention"}
        tel.save(update_fields=["load", "oil_temp", "is_anomaly"])

    wx = WeatherContext.objects.filter(asset=asset).order_by("-timestamp").first()
    storm = "Active severe weather"
    if wx is None:
        WeatherContext.objects.create(
            asset=asset,
            wind_speed=wind,
            flood_surge_level=surge,
            storm_category=storm,
            ambient_temp=28.0,
        )
    else:
        wx.wind_speed = wind
        wx.flood_surge_level = surge
        wx.storm_category = storm
        wx.save(update_fields=["wind_speed", "flood_surge_level", "storm_category"])


@transaction.atomic
def diversify_assets(*, seed: int = 42) -> dict[str, Any]:
    """Respread legend colors; reset operational_state to normal. Returns histogram."""
    rng = random.Random(seed)
    assets = list(Asset.objects.all().order_by("external_id"))
    if not assets:
        return {"count": 0, "histogram": {}}

    n = len(assets)
    n_attention = max(3, min(8, max(1, round(n * 0.12))))
    remaining = n - n_attention
    n_low = remaining // 3
    n_watch = remaining // 3
    n_high = remaining - n_low - n_watch

    shuffled = assets[:]
    rng.shuffle(shuffled)

    attention: list[Asset] = []
    rest: list[Asset] = []
    for a in shuffled:
        if a.external_id == "SUB-001" and len(attention) < n_attention:
            attention.append(a)
        else:
            rest.append(a)
    while len(attention) < n_attention and rest:
        attention.append(rest.pop(0))

    low = rest[:n_low]
    watch = rest[n_low : n_low + n_watch]
    high = rest[n_low + n_watch :]

    assignments = (
        [(a, "attention") for a in attention]
        + [(a, "low") for a in low]
        + [(a, "watch") for a in watch]
        + [(a, "high") for a in high]
    )
    for asset, band in assignments:
        _apply_band(asset, band, rng)

    counts = {"Low": 0, "Watch": 0, "High": 0, "Needs attention": 0}
    for asset in Asset.objects.all():
        counts[legend_bucket(float(asset.risk_score), bool(asset.conflict_flag))] += 1
    return {"count": n, "histogram": counts, "seed": seed}
