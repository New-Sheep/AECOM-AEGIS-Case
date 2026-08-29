"""Load CSV fixtures into SQLite ORM."""

from __future__ import annotations

import csv
from pathlib import Path

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from api.models import Asset, Dependency, Telemetry, WeatherContext
from api.services.data_loader import DATA_DIR
from api.services.graph import clear_graph_cache


class Command(BaseCommand):
    help = "Seed AEGIS assets, telemetry, weather, and dependencies from data/*.csv"

    def add_arguments(self, parser):
        parser.add_argument(
            "--flush",
            action="store_true",
            help="Delete existing grid rows before seeding",
        )

    @transaction.atomic
    def handle(self, *args, **options):
        if options["flush"]:
            Dependency.objects.all().delete()
            Telemetry.objects.all().delete()
            WeatherContext.objects.all().delete()
            Asset.objects.all().delete()
            self.stdout.write("Flushed existing grid data.")

        assets_path = DATA_DIR / "assets.csv"
        telem_path = DATA_DIR / "telemetry.csv"
        deps_path = DATA_DIR / "dependencies.csv"

        by_ext: dict[str, Asset] = {}
        with assets_path.open(newline="", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                asset, _ = Asset.objects.update_or_create(
                    external_id=row["id"],
                    defaults={
                        "name": row["name"],
                        "asset_type": row["type"],
                        "lat": float(row["lat"]),
                        "lon": float(row["lon"]),
                        "elevation": float(row["elevation"]),
                        "scada_link_id": row["scada_link_id"],
                        "replacement_cost": float(row["replacement_cost"]),
                    },
                )
                by_ext[asset.external_id] = asset

        telem_by_scada: dict[str, dict] = {}
        with telem_path.open(newline="", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                telem_by_scada[row["scada_link_id"]] = row

        now = timezone.now()
        for asset in by_ext.values():
            row = telem_by_scada.get(asset.scada_link_id)
            if not row:
                continue
            Telemetry.objects.create(
                asset=asset,
                timestamp=now,
                load=float(row["load"]),
                oil_temp=float(row["oil_temp"]),
                voltage=float(row["voltage"]),
                battery_voltage=float(row["battery_voltage"]),
                is_anomaly=False,
            )
            WeatherContext.objects.create(
                asset=asset,
                timestamp=now,
                wind_speed=float(row["wind_speed"]),
                flood_surge_level=float(row["surge_level"]),
                storm_category="Sprint2-Demo",
            )

        # Guarantee physics-critical demo asset SUB-001 for ConflictFlag after heartbeat clamp
        demo = by_ext.get("SUB-001")
        if demo:
            Telemetry.objects.filter(asset=demo).delete()
            WeatherContext.objects.filter(asset=demo).delete()
            Telemetry.objects.create(
                asset=demo,
                load=0.55,
                oil_temp=72.0,
                voltage=120.0,
                battery_voltage=125.0,
                is_anomaly=False,
            )
            WeatherContext.objects.create(
                asset=demo,
                wind_speed=115.0,
                flood_surge_level=12.0,
                storm_category="ConflictDemo",
            )
            # elevation on SUB-001 from CSV may be 8; ensure surge > elev
            if demo.elevation >= 12.0:
                demo.elevation = 6.0
                demo.save(update_fields=["elevation"])

        deps_created = 0
        if deps_path.exists():
            with deps_path.open(newline="", encoding="utf-8") as f:
                for row in csv.DictReader(f):
                    parent = by_ext.get(row["parent_id"])
                    child = by_ext.get(row["child_id"])
                    if not parent or not child:
                        continue
                    _, created = Dependency.objects.get_or_create(parent=parent, child=child)
                    if created:
                        deps_created += 1

        clear_graph_cache()
        self.stdout.write(
            self.style.SUCCESS(
                f"Seeded assets={Asset.objects.count()} "
                f"telemetry={Telemetry.objects.count()} "
                f"deps={Dependency.objects.count()} (+{deps_created} new)"
            )
        )
