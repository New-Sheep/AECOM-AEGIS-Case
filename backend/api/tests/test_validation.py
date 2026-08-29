"""Unit tests for ValidationService ConflictFlag logic."""

from django.test import TestCase

from api.services.validation import evaluate_physics


class ValidationServiceTests(TestCase):
    def test_conflict_when_physics_fail_and_model_safe(self):
        result = evaluate_physics(
            elevation=6.0,
            surge_level=12.0,
            wind_speed=115.0,
            oil_temp=70.0,
            risk_score=0.18,
        )
        self.assertTrue(result.physics_failure)
        self.assertTrue(result.conflict_flag)

    def test_no_conflict_when_model_also_high(self):
        result = evaluate_physics(
            elevation=6.0,
            surge_level=12.0,
            wind_speed=115.0,
            oil_temp=70.0,
            risk_score=0.85,
        )
        self.assertTrue(result.physics_failure)
        self.assertFalse(result.conflict_flag)

    def test_thermal_conflict(self):
        result = evaluate_physics(
            elevation=20.0,
            surge_level=2.0,
            wind_speed=40.0,
            oil_temp=102.0,
            risk_score=0.1,
        )
        self.assertTrue(result.thermal_critical)
        self.assertTrue(result.conflict_flag)
