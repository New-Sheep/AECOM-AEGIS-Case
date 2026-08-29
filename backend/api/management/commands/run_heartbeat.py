"""AEGIS Heartbeat: anomaly → XGBoost → validation → persist."""

from __future__ import annotations

import pandas as pd
from django.core.management.base import BaseCommand
from django.db import transaction

from api.models import Asset, Telemetry, WeatherContext
from api.services.anomaly import (
    IFOREST_PATH,
    load_isolation_forest,
    predict_anomaly,
    train_isolation_forest,
)
from api.services.data_loader import FEATURE_COLS, load_joined_frame
from api.services.graph import clear_graph_cache
from api.services.inference import score_dataframe, top_drivers
from api.services.predict import MODEL_PATH, load_model
from api.services.preprocess import transform_feature_dict
from api.services.validation import evaluate_physics

# After scoring, clamp this asset to "Safe" so Old Guard raises ConflictFlag
# when physics says Failure (Sprint 2 demo).
DEMO_CONFLICT_ID = "SUB-001"
DEMO_SAFE_SCORE = 0.18


class Command(BaseCommand):
    help = "Run AEGIS heartbeat: IsolationForest + XGBoost + ValidationService"

    def add_arguments(self, parser):
        parser.add_argument(
            "--retrain-iforest",
            action="store_true",
            help="Refit Isolation Forest from current CSV features",
        )
        parser.add_argument(
            "--no-demo-conflict",
            action="store_true",
            help="Do not clamp SUB-001 score for ConflictFlag demo",
        )

    @transaction.atomic
    def handle(self, *args, **options):
        if not MODEL_PATH.exists():
            raise SystemExit(f"Missing {MODEL_PATH}. Run: python scripts/train_xgb.py")

        if options["retrain_iforest"] or not IFOREST_PATH.exists():
            frame = load_joined_frame()
            train_isolation_forest(frame)
            self.stdout.write(f"Trained Isolation Forest → {IFOREST_PATH}")

        xgb = load_model()
        iforest = load_isolation_forest()

        assets = list(Asset.objects.all())
        if not assets:
            raise SystemExit("No assets. Run: python manage.py seed_aegis --flush")

        rows = []
        meta = []
        for asset in assets:
            telem = asset.telemetry.order_by("-timestamp").first()
            weather = asset.weather.order_by("-timestamp").first()
            if not telem or not weather:
                continue
            feat = {
                "load": float(telem.load),
                "oil_temp": float(telem.oil_temp),
                "wind_speed": float(weather.wind_speed),
                "surge_level": float(weather.flood_surge_level),
            }
            is_anom = predict_anomaly(iforest, feat)
            if is_anom != telem.is_anomaly:
                telem.is_anomaly = is_anom
                telem.save(update_fields=["is_anomaly"])

            cleaned = transform_feature_dict(feat)
            # Anomaly policy: keep features but lower confidence later
            row = {**cleaned, "elevation": float(asset.elevation)}
            rows.append(row)
            meta.append((asset, telem, weather, cleaned, is_anom))

        frame = pd.DataFrame(rows)
        risks = score_dataframe(frame[FEATURE_COLS], xgb)

        conflicts = 0
        for i, (asset, telem, weather, feat, is_anom) in enumerate(meta):
            risk = float(risks[i])
            if (
                not options["no_demo_conflict"]
                and asset.external_id == DEMO_CONFLICT_ID
            ):
                # Ensure ConflictFlag demo: physics critical + model "safe"
                risk = DEMO_SAFE_SCORE

            drivers = top_drivers(xgb, pd.Series(feat))
            result = evaluate_physics(
                elevation=float(asset.elevation),
                surge_level=float(weather.flood_surge_level),
                wind_speed=float(weather.wind_speed),
                oil_temp=float(telem.oil_temp),
                risk_score=risk,
                is_anomaly=is_anom,
            )
            asset.risk_score = risk
            asset.conflict_flag = result.conflict_flag
            asset.confidence = result.confidence
            asset.drivers_json = drivers
            asset.save(
                update_fields=[
                    "risk_score",
                    "conflict_flag",
                    "confidence",
                    "drivers_json",
                ]
            )
            if result.conflict_flag:
                conflicts += 1
                self.stdout.write(
                    f"ConflictFlag {asset.external_id}: {'; '.join(result.reasons)}"
                )

        clear_graph_cache()
        self.stdout.write(
            self.style.SUCCESS(
                f"Heartbeat complete: scored={len(meta)} conflicts={conflicts}"
            )
        )
