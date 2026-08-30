"""AEGIS grid domain models (Sprint 2–3 — SQLite)."""

from __future__ import annotations

from django.db import models


class Asset(models.Model):
    class AssetType(models.TextChoices):
        TRANSFORMER = "Transformer", "Transformer"
        BATTERY = "Battery", "Battery"
        SWITCHGEAR = "Switchgear", "Switchgear"
        PUMP = "Pump", "Pump"
        HOSPITAL = "Hospital", "Hospital"
        WATER_PLANT = "WaterPlant", "WaterPlant"

    class OperationalState(models.TextChoices):
        NORMAL = "normal", "Normal"
        LOAD_REDUCED = "load_reduced", "Load reduced"
        DEENERGIZED = "deenergized", "Deenergized"

    external_id = models.CharField(max_length=64, unique=True)
    name = models.CharField(max_length=128)
    asset_type = models.CharField(max_length=32, choices=AssetType.choices)
    lat = models.FloatField()
    lon = models.FloatField()
    elevation = models.FloatField(default=0.0)
    scada_link_id = models.CharField(max_length=64, unique=True)
    replacement_cost = models.FloatField(default=0.0)
    flood_zone = models.CharField(max_length=32, blank=True, default="")
    age = models.IntegerField(default=20)
    risk_score = models.FloatField(default=0.0)
    confidence = models.FloatField(default=1.0)
    conflict_flag = models.BooleanField(default=False)
    drivers_json = models.JSONField(default=list, blank=True)
    operational_state = models.CharField(
        max_length=32,
        choices=OperationalState.choices,
        default=OperationalState.NORMAL,
    )
    baseline_load = models.FloatField(null=True, blank=True)

    class Meta:
        ordering = ["external_id"]

    def __str__(self) -> str:
        return f"{self.external_id} ({self.asset_type})"


class Telemetry(models.Model):
    asset = models.ForeignKey(Asset, on_delete=models.CASCADE, related_name="telemetry")
    timestamp = models.DateTimeField(auto_now_add=True)
    load = models.FloatField()
    oil_temp = models.FloatField()
    voltage = models.FloatField(default=120.0)
    battery_voltage = models.FloatField(default=125.0)
    is_anomaly = models.BooleanField(default=False)

    class Meta:
        ordering = ["-timestamp"]
        verbose_name_plural = "telemetry"


class WeatherContext(models.Model):
    asset = models.ForeignKey(
        Asset, on_delete=models.CASCADE, related_name="weather", null=True, blank=True
    )
    timestamp = models.DateTimeField(auto_now_add=True)
    wind_speed = models.FloatField()
    flood_surge_level = models.FloatField()
    storm_category = models.CharField(max_length=32, blank=True, default="demo")
    ambient_temp = models.FloatField(default=28.0)

    class Meta:
        ordering = ["-timestamp"]


class Dependency(models.Model):
    parent = models.ForeignKey(
        Asset, on_delete=models.CASCADE, related_name="downstream_links"
    )
    child = models.ForeignKey(
        Asset, on_delete=models.CASCADE, related_name="upstream_links"
    )

    class Meta:
        unique_together = ("parent", "child")
        verbose_name_plural = "dependencies"

    def __str__(self) -> str:
        return f"{self.parent.external_id} → {self.child.external_id}"


class AuditLog(models.Model):
    """HITL control decisions (Sprint 3)."""

    user_id = models.CharField(max_length=64, default="demo-ic")
    asset = models.ForeignKey(Asset, on_delete=models.CASCADE, related_name="audit_logs")
    action = models.CharField(max_length=64)
    reason_text = models.TextField()
    authorization_level = models.CharField(max_length=32)
    ai_recommendation = models.CharField(max_length=64, blank=True, default="")
    human_override = models.BooleanField(default=False)
    timestamp = models.DateTimeField(auto_now_add=True)
    outcome = models.CharField(max_length=128, blank=True, default="")

    class Meta:
        ordering = ["-timestamp"]

    def __str__(self) -> str:
        return f"{self.action} on {self.asset.external_id} by {self.user_id}"


class ShadowLog(models.Model):
    """AI suggested action vs human actual (eval / retrain signal)."""

    asset = models.ForeignKey(Asset, on_delete=models.CASCADE, related_name="shadow_logs")
    ai_predicted_action = models.CharField(max_length=64)
    human_actual_action = models.CharField(max_length=64)
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-timestamp"]

    def __str__(self) -> str:
        return (
            f"{self.asset.external_id}: AI={self.ai_predicted_action} "
            f"human={self.human_actual_action}"
        )


class ScenarioClock(models.Model):
    """Singleton-ish living-demo clock (one row id=1)."""

    class Phase(models.TextChoices):
        APPROACH = "approach", "Approach"
        PEAK = "peak", "Peak"
        LANDFALL = "landfall", "Landfall"
        AFTERMATH = "aftermath", "Aftermath"

    sim_phase = models.CharField(
        max_length=32, choices=Phase.choices, default=Phase.PEAK
    )
    sim_tick = models.PositiveIntegerField(default=0)
    paused = models.BooleanField(default=False)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "scenario clock"
        verbose_name_plural = "scenario clocks"

    def __str__(self) -> str:
        return f"{self.sim_phase} tick={self.sim_tick} paused={self.paused}"

    @classmethod
    def get_solo(cls) -> "ScenarioClock":
        obj, _ = cls.objects.get_or_create(
            pk=1,
            defaults={"sim_phase": cls.Phase.PEAK, "sim_tick": 0, "paused": False},
        )
        return obj

    def time_label(self) -> str:
        minutes = int(self.sim_tick) * 1
        return f"T+{minutes // 60:02d}:{minutes % 60:02d}"
