"""Tests for preprocess + fingerprint retrain gate."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
from django.test import SimpleTestCase, override_settings

from api.services.data_loader import ARTIFACTS_DIR, FEATURE_COLS
from api.services.preprocess import (
    FINGERPRINT_PATH,
    PREPROCESS_PATH,
    SCALER_PATH,
    fingerprint,
    fit_preprocess,
    should_retrain,
    transform_feature_dict,
    transform_preprocess,
    write_fingerprint,
)


class PreprocessTests(SimpleTestCase):
    def test_impute_and_clip(self):
        df = pd.DataFrame(
            [
                {"load": 0.5, "oil_temp": 70.0, "wind_speed": 40.0, "surge_level": 2.0},
                {"load": None, "oil_temp": 200.0, "wind_speed": 40.0, "surge_level": 2.0},
            ]
        )
        X, bundle, report = fit_preprocess(df)
        self.assertEqual(report.n_out, 2)
        self.assertGreaterEqual(report.n_imputed, 1)
        self.assertGreaterEqual(report.n_clipped, 1)
        self.assertLessEqual(float(X.loc[1, "oil_temp"]), 150.0)
        X2, _ = transform_preprocess(df, bundle)
        self.assertEqual(len(X2), 2)

    def test_fingerprint_changes_with_data(self):
        a = pd.DataFrame(
            [{"load": 0.5, "oil_temp": 70.0, "wind_speed": 40.0, "surge_level": 2.0}]
        )
        b = pd.DataFrame(
            [{"load": 0.9, "oil_temp": 70.0, "wind_speed": 40.0, "surge_level": 2.0}]
        )
        Xa, _, _ = fit_preprocess(a)
        Xb, _, _ = fit_preprocess(b)
        self.assertEqual(fingerprint(Xa), fingerprint(Xa))
        self.assertNotEqual(fingerprint(Xa), fingerprint(Xb))

    def test_should_retrain_false_when_stamp_matches(self):
        df = pd.DataFrame(
            [{"load": 0.4, "oil_temp": 65.0, "wind_speed": 30.0, "surge_level": 1.0}]
        )
        X, _, _ = fit_preprocess(df)
        fp = fingerprint(X)
        # Point stamp + fake required files via writing fingerprint and touching paths
        ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)
        write_fingerprint(fp)
        # Create empty placeholders if missing so required_model_files_exist can pass
        from api.services.data_loader import MODEL_PATH
        from api.services.anomaly import IFOREST_PATH
        import joblib
        from sklearn.preprocessing import StandardScaler

        if not MODEL_PATH.exists():
            joblib.dump({"stub": True}, MODEL_PATH)
        if not IFOREST_PATH.exists():
            joblib.dump({"stub": True}, IFOREST_PATH)
        if not PREPROCESS_PATH.exists():
            joblib.dump({"version": "1", "medians": {}, "ranges": {}, "feature_cols": FEATURE_COLS}, PREPROCESS_PATH)
        if not SCALER_PATH.exists():
            joblib.dump(StandardScaler(), SCALER_PATH)

        self.assertFalse(should_retrain(X, force=False))
        self.assertTrue(should_retrain(X, force=True))

    def test_transform_feature_dict_clips(self):
        out = transform_feature_dict(
            {
                "load": 0.5,
                "oil_temp": 999.0,
                "wind_speed": 10.0,
                "surge_level": 1.0,
            }
        )
        self.assertLessEqual(out["oil_temp"], 150.0)
