"""Illustrative customer attribution + finance breakdown (doc 17)."""

from __future__ import annotations

from functools import lru_cache
from typing import Any

from api.models import Asset, ScenarioClock, Telemetry, WeatherContext
from api.services.graph import cached_graph, downstream_impact
from api.services.scenario import clock_payload

TERRITORY_CUSTOMERS = 8_000_000
VOLL_PER_CUSTOMER_HOUR_USD = 3.50

METHODOLOGY = (
    "Illustrative. CapEx_at_risk = sum(replacement_cost) for flagged high-risk/conflict sites. "
    "Illustrative_outage_cost = customers_at_risk * hours_at_risk * voll_per_customer_hour_usd. "
    "Not an ICE Calculator run; not regulatory VoLL."
)

_TYPE_WEIGHTS = {
    "Transformer": 12.0,
    "Switchgear": 10.0,
    "Pump": 5.0,
    "Battery": 3.0,
    "Hospital": 4.0,
    "WaterPlant": 4.0,
}

_HOURS_BY_PHASE = {
    "approach": 6.0,
    "peak": 12.0,
    "landfall": 18.0,
    "aftermath": 8.0,
}

CRITICAL_TYPES = {"Hospital", "WaterPlant"}


def is_critical(asset_type: str) -> bool:
    return asset_type in CRITICAL_TYPES


def _weight(asset_type: str) -> float:
    return float(_TYPE_WEIGHTS.get(asset_type, 5.0))


@lru_cache(maxsize=1)
def _customer_map_key(asset_sig: str) -> dict[str, int]:
    """Internal: asset_sig forces cache bust when asset set changes."""
    _ = asset_sig
    assets = list(Asset.objects.all().order_by("external_id"))
    if not assets:
        return {}
    weights = [_weight(a.asset_type) for a in assets]
    total_w = sum(weights) or 1.0
    raw = [TERRITORY_CUSTOMERS * w / total_w for w in weights]
    floors = [int(x) for x in raw]
    rem = TERRITORY_CUSTOMERS - sum(floors)
    # Give remainder to highest fractional parts
    fracs = sorted(
        ((raw[i] - floors[i], i) for i in range(len(assets))),
        reverse=True,
    )
    for k in range(rem):
        floors[fracs[k % len(fracs)][1]] += 1
    return {assets[i].external_id: floors[i] for i in range(len(assets))}


def clear_customer_cache() -> None:
    _customer_map_key.cache_clear()


def _asset_signature() -> str:
    rows = Asset.objects.order_by("external_id").values_list(
        "external_id", "asset_type"
    )
    return "|".join(f"{e}:{t}" for e, t in rows)


def customers_map() -> dict[str, int]:
    return dict(_customer_map_key(_asset_signature()))


def customers_for_asset(asset: Asset | str) -> int:
    eid = asset.external_id if isinstance(asset, Asset) else str(asset)
    return int(customers_map().get(eid, 0))


def hours_at_risk(phase: str | None = None) -> float:
    if not phase:
        phase = ScenarioClock.get_solo().sim_phase
    return float(_HOURS_BY_PHASE.get(str(phase), 12.0))


def _threat_rollups(assets: list[Asset], wx: WeatherContext | None) -> dict[str, Any]:
    conflict_count = sum(1 for a in assets if a.conflict_flag)
    high_risk_count = sum(1 for a in assets if a.risk_score > 0.7)
    wind = float(wx.wind_speed) if wx else 0.0
    surge = float(wx.flood_surge_level) if wx else 0.0
    if conflict_count > 0 or high_risk_count >= 5:
        threat = "CRITICAL"
    elif wind > 100 or high_risk_count >= 2 or wind > 70:
        threat = "ELEVATED"
    elif high_risk_count >= 1:
        threat = "WATCH"
    else:
        threat = "NORMAL"
    return {
        "threat_level": threat,
        "conflict_count": conflict_count,
        "high_risk_count": high_risk_count,
        "wind_speed": wind,
        "surge_level": surge,
    }


def risk_band(risk: float, conflict: bool) -> str:
    if conflict:
        return "Needs attention"
    if risk < 0.3:
        return "Low"
    if risk <= 0.7:
        return "Watch"
    return "High"


def finance_breakdown() -> dict[str, Any]:
    assets = list(Asset.objects.all())
    cmap = customers_map()
    wx = WeatherContext.objects.order_by("-timestamp").first()
    clock = clock_payload()
    roll = _threat_rollups(assets, wx)
    flagged = [a for a in assets if a.risk_score > 0.7 or a.conflict_flag]
    capex = sum(float(a.replacement_cost) for a in flagged)
    customers_at_risk = sum(cmap.get(a.external_id, 0) for a in flagged)
    hrs = hours_at_risk(clock.get("sim_phase"))
    outage = round(customers_at_risk * hrs * VOLL_PER_CUSTOMER_HOUR_USD, 2)
    return {
        "capex_at_risk_usd": round(capex, 2),
        "illustrative_outage_cost_usd": outage,
        "customers_at_risk": customers_at_risk,
        "hours_at_risk": hrs,
        "constants": {
            "territory_customers": TERRITORY_CUSTOMERS,
            "voll_per_customer_hour_usd": VOLL_PER_CUSTOMER_HOUR_USD,
            "hours_at_risk_heuristic": hrs,
        },
        "methodology": METHODOLOGY,
        "flagged_asset_ids": [a.external_id for a in flagged],
        "threat_level": roll["threat_level"],
        **{k: clock[k] for k in ("sim_phase", "sim_tick", "sim_time_label", "sim_paused")},
    }


def region_situation() -> dict[str, Any]:
    assets = list(Asset.objects.all())
    cmap = customers_map()
    wx = WeatherContext.objects.order_by("-timestamp").first()
    clock = clock_payload()
    roll = _threat_rollups(assets, wx)
    hist = {"Low": 0, "Watch": 0, "High": 0, "Needs attention": 0}
    critical_customers = 0
    residential_customers = 0
    for a in assets:
        hist[risk_band(float(a.risk_score), bool(a.conflict_flag))] += 1
        c = cmap.get(a.external_id, 0)
        if is_critical(a.asset_type):
            critical_customers += c
        else:
            residential_customers += c
    conflicts = [
        {
            "asset_id": a.external_id,
            "name": a.name,
            "customers_served": cmap.get(a.external_id, 0),
        }
        for a in assets
        if a.conflict_flag
    ]
    return {
        **roll,
        **clock,
        "risk_histogram": hist,
        "territory_customers": TERRITORY_CUSTOMERS,
        "customers_total": sum(cmap.values()),
        "customers_critical": critical_customers,
        "customers_residential": residential_customers,
        "conflict_sites": conflicts,
        "asset_count": len(assets),
    }


def site_explain(asset: Asset) -> dict[str, Any]:
    from api.services.briefing import build_asset_facts

    facts = build_asset_facts(asset)
    graph = cached_graph()
    _, down_ids = downstream_impact(asset.external_id, graph)
    down_names = []
    for eid in down_ids[:12]:
        row = Asset.objects.filter(external_id=eid).only("name").first()
        down_names.append(row.name if row else eid)
    cust = customers_for_asset(asset)
    return {
        "asset_id": asset.external_id,
        "name": asset.name,
        "type": asset.asset_type,
        "critical_lifeline": is_critical(asset.asset_type),
        "risk": facts.get("risk"),
        "confidence": facts.get("confidence"),
        "conflict_flag": bool(facts.get("conflict_flag")),
        "drivers": facts.get("drivers") or [],
        "operational_state": facts.get("operational_state"),
        "elevation": facts.get("elevation"),
        "replacement_cost": facts.get("replacement_cost"),
        "customers_served": cust,
        "sensors": facts.get("sensors") or {},
        "weather": facts.get("weather") or {},
        "downstream_ids": down_ids,
        "downstream_names": down_names,
    }


def customer_impact(*, asset_id: str | None = None) -> dict[str, Any]:
    region = region_situation()
    out: dict[str, Any] = {
        "region": {
            "territory_customers": region["territory_customers"],
            "customers_total": region["customers_total"],
            "customers_critical": region["customers_critical"],
            "customers_residential": region["customers_residential"],
            "customers_at_risk": finance_breakdown()["customers_at_risk"],
        },
        "methodology": (
            "Illustrative allocation of SGW's 8,000,000 service population "
            "across demo assets by type weights. Critical = Hospital/WaterPlant."
        ),
    }
    if asset_id:
        try:
            asset = Asset.objects.get(external_id=asset_id)
        except Asset.DoesNotExist:
            out["site"] = None
            out["detail"] = f"Asset {asset_id} not found"
            return out
        cmap = customers_map()
        graph = cached_graph()
        _, down_ids = downstream_impact(asset.external_id, graph)
        down_cust = sum(cmap.get(d, 0) for d in down_ids)
        out["site"] = {
            "asset_id": asset.external_id,
            "name": asset.name,
            "customers_served": customers_for_asset(asset),
            "critical_lifeline": is_critical(asset.asset_type),
            "downstream_customers": down_cust,
            "downstream_count": len(down_ids),
        }
    return out


def dependency_impact(asset: Asset) -> dict[str, Any]:
    cmap = customers_map()
    graph = cached_graph()
    count, down_ids = downstream_impact(asset.external_id, graph)
    cascade = []
    for eid in down_ids:
        row = Asset.objects.filter(external_id=eid).first()
        cascade.append(
            {
                "asset_id": eid,
                "name": row.name if row else eid,
                "type": row.asset_type if row else "",
                "customers_served": cmap.get(eid, 0),
                "critical_lifeline": is_critical(row.asset_type) if row else False,
            }
        )
    return {
        "asset_id": asset.external_id,
        "name": asset.name,
        "customers_served": customers_for_asset(asset),
        "downstream_count": count,
        "downstream_customers_sum": sum(c["customers_served"] for c in cascade),
        "cascade": cascade,
    }
