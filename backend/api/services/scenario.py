"""Living scenario clock: tick weather/telemetry and demo reset."""

from __future__ import annotations

import random
from typing import Any

from django.db import transaction

from api.models import Asset, ScenarioClock, Telemetry, WeatherContext
from api.services.demo_diversify import diversify_assets

_PHASES = [
    ScenarioClock.Phase.APPROACH,
    ScenarioClock.Phase.PEAK,
    ScenarioClock.Phase.LANDFALL,
    ScenarioClock.Phase.AFTERMATH,
]
_TICKS_PER_PHASE = 8


def clock_payload(clock: ScenarioClock | None = None) -> dict[str, Any]:
    c = clock or ScenarioClock.get_solo()
    return {
        "sim_phase": c.sim_phase,
        "sim_tick": int(c.sim_tick),
        "sim_time_label": c.time_label(),
        "sim_paused": bool(c.paused),
    }


@transaction.atomic
def set_paused(paused: bool) -> dict[str, Any]:
    c = ScenarioClock.get_solo()
    c.paused = bool(paused)
    c.save(update_fields=["paused", "updated_at"])
    return clock_payload(c)


@transaction.atomic
def tick_scenario(*, force: bool = False, seed: int | None = None) -> dict[str, Any]:
    """Advance sim tick; nudge a subset of sites; maybe reflag 0–2 attention sites."""
    c = ScenarioClock.get_solo()
    if c.paused and not force:
        return {**clock_payload(c), "advanced": False, "detail": "paused"}

    rng = random.Random(seed if seed is not None else (c.sim_tick + 17))
    c.sim_tick = int(c.sim_tick) + 1
    phase_idx = (c.sim_tick // _TICKS_PER_PHASE) % len(_PHASES)
    c.sim_phase = _PHASES[phase_idx]
    c.save(update_fields=["sim_tick", "sim_phase", "updated_at"])

    assets = list(Asset.objects.all())
    if not assets:
        return {**clock_payload(c), "advanced": True, "nudged": 0, "reflagged": []}

    sample_n = max(3, min(12, len(assets) // 3))
    subset = rng.sample(assets, k=min(sample_n, len(assets)))
    nudged = 0
    for asset in subset:
        wx = WeatherContext.objects.filter(asset=asset).order_by("-timestamp").first()
        tel = Telemetry.objects.filter(asset=asset).order_by("-timestamp").first()
        if wx:
            wx.wind_speed = max(
                10.0, min(140.0, float(wx.wind_speed) + rng.uniform(-8.0, 10.0))
            )
            wx.flood_surge_level = max(
                0.1,
                min(20.0, float(wx.flood_surge_level) + rng.uniform(-0.6, 0.8)),
            )
            wx.save(update_fields=["wind_speed", "flood_surge_level"])
            nudged += 1
        if tel and asset.operational_state == Asset.OperationalState.NORMAL:
            tel.oil_temp = max(
                40.0, min(110.0, float(tel.oil_temp) + rng.uniform(-3.0, 4.0))
            )
            tel.load = max(0.05, min(0.98, float(tel.load) + rng.uniform(-0.05, 0.05)))
            tel.save(update_fields=["oil_temp", "load"])

    # Reflag up to 2 sites where physics looks dangerous and not already deenergized
    candidates = [
        a
        for a in assets
        if a.operational_state != Asset.OperationalState.DEENERGIZED
        and not a.conflict_flag
    ]
    rng.shuffle(candidates)
    reflagged: list[str] = []
    for asset in candidates:
        if len(reflagged) >= 2:
            break
        wx = WeatherContext.objects.filter(asset=asset).order_by("-timestamp").first()
        if not wx:
            continue
        wind = float(wx.wind_speed)
        surge = float(wx.flood_surge_level)
        elev = float(asset.elevation)
        if wind > 100 or surge > elev:
            asset.conflict_flag = True
            if float(asset.risk_score) > 0.45:
                asset.risk_score = round(rng.uniform(0.15, 0.38), 3)
            asset.save(update_fields=["conflict_flag", "risk_score"])
            reflagged.append(asset.external_id)

    return {
        **clock_payload(c),
        "advanced": True,
        "nudged": nudged,
        "reflagged": reflagged,
    }


@transaction.atomic
def reset_scenario(*, seed: int = 42) -> dict[str, Any]:
    """Diversify map + reset clock to peak / tick 0."""
    hist = diversify_assets(seed=seed)
    c = ScenarioClock.get_solo()
    c.sim_phase = ScenarioClock.Phase.PEAK
    c.sim_tick = 0
    c.paused = False
    c.save(update_fields=["sim_phase", "sim_tick", "paused", "updated_at"])
    conflicts = Asset.objects.filter(conflict_flag=True).count()
    return {
        **clock_payload(c),
        "diversify": hist,
        "conflict_count": conflicts,
    }
