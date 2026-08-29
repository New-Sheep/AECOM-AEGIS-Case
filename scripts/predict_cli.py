"""CLI: score one feature row with the trained joblib model."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from api.services.predict import load_model, score_row  # noqa: E402


def main() -> None:
    p = argparse.ArgumentParser(description="Score one asset feature vector")
    p.add_argument("--load", type=float, default=0.8)
    p.add_argument("--oil-temp", type=float, default=90.0)
    p.add_argument("--wind-speed", type=float, default=100.0)
    p.add_argument("--surge-level", type=float, default=10.0)
    args = p.parse_args()

    model = load_model()
    risk = score_row(
        model,
        load=args.load,
        oil_temp=args.oil_temp,
        wind_speed=args.wind_speed,
        surge_level=args.surge_level,
    )
    print(f"risk_score={risk:.4f}")


if __name__ == "__main__":
    main()
