"""Spread risk/conflict so the map shows Low / Watch / High / Needs attention."""

from __future__ import annotations

from django.core.management.base import BaseCommand, CommandError

from api.models import Asset
from api.services.demo_diversify import diversify_assets


class Command(BaseCommand):
    help = (
        "Diversify asset risk_score, conflict_flag, weather, and telemetry "
        "so Folium shows Low / Watch / High / Needs attention for demos."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--seed",
            type=int,
            default=42,
            help="RNG seed for reproducible demo mixes (default 42)",
        )

    def handle(self, *args, **options):
        seed = int(options["seed"])
        if not Asset.objects.exists():
            raise CommandError(
                "No assets found. Run: python backend/manage.py seed_aegis --flush"
            )
        result = diversify_assets(seed=seed)
        hist = result.get("histogram") or {}
        self.stdout.write(
            self.style.SUCCESS(
                f"Diversified {result.get('count', 0)} assets (seed={seed})."
            )
        )
        self.stdout.write("Map legend histogram:")
        for label in ("Low", "Watch", "High", "Needs attention"):
            self.stdout.write(f"  {label:16} {hist.get(label, 0):3d}")
