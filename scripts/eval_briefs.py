"""
Evaluate AEGIS action briefs: Pydantic grounding + LLM-as-judge.

Default FAKE_LLM path is CI-safe. Pass --live to force NIM (sets FAKE_LLM=0 for process).

Usage (repo root):
  python scripts/eval_briefs.py
  python scripts/eval_briefs.py --asset SUB-001
  python scripts/eval_briefs.py --live
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
sys.path.insert(0, str(BACKEND))

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")


def _bootstrap_django() -> None:
    import django

    django.setup()


def _inline_fixtures() -> list[dict]:
    return [
        {
            "asset_id": "SUB-001",
            "name": "Fort Myers Beach Tap",
            "risk": 0.18,
            "confidence": 0.45,
            "conflict_flag": True,
            "drivers": ["surge_level", "wind_speed", "oil_temp"],
            "downstream_ids": ["SUB-002", "SUB-012"],
            "replacement_cost": 2_880_000,
            "elevation": 5.0,
            "sensors": {"load": 0.64, "oil_temp": 72.0, "voltage": 120.0},
            "weather": {"wind_speed": 115.0, "flood_surge_level": 12.0},
        },
        {
            "asset_id": "SUB-010",
            "name": "Quiet Feeder",
            "risk": 0.12,
            "confidence": 0.7,
            "conflict_flag": False,
            "drivers": ["load"],
            "downstream_ids": [],
            "replacement_cost": 500_000,
            "elevation": 12.0,
            "sensors": {"load": 0.4, "oil_temp": 65.0, "voltage": 121.0},
            "weather": {"wind_speed": 40.0, "flood_surge_level": 1.2},
        },
    ]


def _facts_from_orm(asset_ids: list[str] | None) -> list[dict]:
    from api.models import Asset
    from api.services.briefing import build_asset_facts

    qs = Asset.objects.all().order_by("external_id")
    if asset_ids:
        qs = qs.filter(external_id__in=asset_ids)
    else:
        # Prefer SUB-001 + one non-conflict if present
        preferred = list(
            Asset.objects.filter(external_id="SUB-001")
        ) + list(Asset.objects.exclude(conflict_flag=True).order_by("external_id")[:1])
        if preferred:
            seen = set()
            out = []
            for a in preferred:
                if a.external_id in seen:
                    continue
                seen.add(a.external_id)
                out.append(build_asset_facts(a))
            if out:
                return out
        qs = qs[:2]
    return [build_asset_facts(a) for a in qs]


def main() -> int:
    parser = argparse.ArgumentParser(description="Eval AEGIS structured briefs")
    parser.add_argument("--asset", action="append", help="Limit to asset_id (repeatable)")
    parser.add_argument(
        "--live",
        action="store_true",
        help="Force live NIM (FAKE_LLM=0 for this process)",
    )
    parser.add_argument(
        "--fixtures-only",
        action="store_true",
        help="Skip ORM; use inline fixtures only",
    )
    args = parser.parse_args()

    if args.live:
        os.environ["FAKE_LLM"] = "0"

    cases: list[dict]
    if args.fixtures_only:
        cases = _inline_fixtures()
        if args.asset:
            cases = [c for c in cases if c["asset_id"] in set(args.asset)]
    else:
        try:
            _bootstrap_django()
            cases = _facts_from_orm(args.asset)
            if not cases:
                print("No ORM assets; falling back to inline fixtures")
                cases = _inline_fixtures()
        except Exception as exc:  # noqa: BLE001
            print(f"ORM unavailable ({exc}); using inline fixtures")
            cases = _inline_fixtures()
            if args.asset:
                cases = [c for c in cases if c["asset_id"] in set(args.asset)]

    from api.services.llm import generate_action_brief_structured, judge_brief

    print("AEGIS brief eval (Pydantic grounding + judge)")
    print(f"FAKE_LLM={os.getenv('FAKE_LLM', '1')}  cases={len(cases)}")
    print()
    print(
        f"{'asset':<12} {'provider':<8} {'ground':<6} {'judge':>5}  issues"
    )
    print("-" * 72)

    any_fail = False
    for facts in cases:
        brief, provider, issues = generate_action_brief_structured(facts)
        # Re-check in case FAKE replaced after NIM issues
        from api.services.brief_schema import deterministic_validate

        ground = deterministic_validate(brief, facts)
        verdict = judge_brief(facts, brief)
        ground_ok = len(ground) == 0
        if not ground_ok or not verdict.faithful:
            any_fail = True
        issue_str = "; ".join(ground[:2] or verdict.issues[:2]) or "-"
        print(
            f"{facts.get('asset_id', '?'):<12} {provider:<8} "
            f"{'PASS' if ground_ok else 'FAIL':<6} {verdict.score:5.2f}  {issue_str}"
        )

    print()
    if any_fail:
        print("RESULT: FAIL (grounding and/or judge)")
        return 1
    print("RESULT: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
