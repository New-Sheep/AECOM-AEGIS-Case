"""ValidationService — Old Guard physics vs XGBoost (Sprint 2)."""

from __future__ import annotations

from dataclasses import dataclass


SAFE_RISK_THRESHOLD = 0.3
WIND_CRITICAL_MPH = 100.0
OIL_TEMP_CRITICAL_C = 95.0


@dataclass
class ValidationResult:
    physics_failure: bool
    thermal_critical: bool
    conflict_flag: bool
    confidence: float
    reasons: list[str]


def evaluate_physics(
    *,
    elevation: float,
    surge_level: float,
    wind_speed: float,
    oil_temp: float,
    risk_score: float,
    is_anomaly: bool = False,
) -> ValidationResult:
    """Compare hard rules to model score.

    ConflictFlag = physics Failure AND model Safe (risk < 0.3).
    Goal: catch false negatives (minimize FN).
    """
    reasons: list[str] = []
    physics_failure = surge_level > elevation and wind_speed > WIND_CRITICAL_MPH
    if physics_failure:
        reasons.append(
            f"flood/wind rule: surge {surge_level:.1f} > elev {elevation:.1f} "
            f"and wind {wind_speed:.1f} > {WIND_CRITICAL_MPH}"
        )

    thermal_critical = oil_temp > OIL_TEMP_CRITICAL_C
    if thermal_critical:
        reasons.append(f"thermal rule: oil_temp {oil_temp:.1f} > {OIL_TEMP_CRITICAL_C}")

    model_safe = risk_score < SAFE_RISK_THRESHOLD
    # Conflict when physics says fail/thermal critical but model is "safe"
    conflict = (physics_failure or thermal_critical) and model_safe
    if conflict:
        reasons.append(
            f"ConflictFlag: physics critical but XGB risk={risk_score:.3f} < {SAFE_RISK_THRESHOLD}"
        )

    confidence = 0.45 if is_anomaly else 1.0
    if conflict:
        confidence = min(confidence, 0.6)

    return ValidationResult(
        physics_failure=physics_failure,
        thermal_critical=thermal_critical,
        conflict_flag=conflict,
        confidence=confidence,
        reasons=reasons,
    )
