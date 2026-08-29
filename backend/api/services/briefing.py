"""Assemble grounded facts for action_brief / control."""

from __future__ import annotations

from typing import Any

from api.models import Asset, Telemetry, WeatherContext
from api.services.graph import cached_graph, downstream_impact
from api.services.llm import suggest_action_level


def build_asset_facts(asset: Asset) -> dict[str, Any]:
    tel = (
        Telemetry.objects.filter(asset=asset).order_by("-timestamp").first()
    )
    wx = (
        WeatherContext.objects.filter(asset=asset).order_by("-timestamp").first()
        or WeatherContext.objects.filter(asset__isnull=True).order_by("-timestamp").first()
    )
    graph = cached_graph()
    impact_count, downstream_ids = downstream_impact(asset.external_id, graph)

    sensors = {}
    if tel:
        sensors = {
            "load": float(tel.load),
            "oil_temp": float(tel.oil_temp),
            "voltage": float(tel.voltage),
            "battery_voltage": float(tel.battery_voltage),
            "is_anomaly": bool(tel.is_anomaly),
            "timestamp": tel.timestamp.isoformat() if tel.timestamp else None,
        }
    weather = {}
    if wx:
        weather = {
            "wind_speed": float(wx.wind_speed),
            "flood_surge_level": float(wx.flood_surge_level),
            "storm_category": wx.storm_category,
            "ambient_temp": float(wx.ambient_temp),
        }

    facts: dict[str, Any] = {
        "asset_id": asset.external_id,
        "name": asset.name,
        "type": asset.asset_type,
        "risk": round(float(asset.risk_score), 4),
        "confidence": round(float(asset.confidence), 3),
        "conflict_flag": bool(asset.conflict_flag),
        "drivers": asset.drivers_json or [],
        "elevation": float(asset.elevation),
        "replacement_cost": float(asset.replacement_cost),
        "impact_count": impact_count,
        "downstream_ids": downstream_ids,
        "sensors": sensors,
        "weather": weather,
        "suggested_action": suggest_action_level(
            {
                "risk": asset.risk_score,
                "conflict_flag": asset.conflict_flag,
            }
        ),
    }
    return facts
