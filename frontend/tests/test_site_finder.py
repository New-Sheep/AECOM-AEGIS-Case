"""Tests for Find site filter/sort (no Streamlit UI)."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

# frontend/ is not a package — put it on sys.path like Streamlit does.
_FRONTEND = Path(__file__).resolve().parents[1]
if str(_FRONTEND) not in sys.path:
    sys.path.insert(0, str(_FRONTEND))

from site_finder import filter_sites  # noqa: E402


def _asset(eid: str, name: str, risk: float, conflict: bool = False) -> dict:
    return {
        "id": eid,
        "name": name,
        "current_risk": risk,
        "conflict_flag": conflict,
    }


class SiteFinderTests(unittest.TestCase):
    def setUp(self):
        self.assets = [
            _asset("SUB-LOW", "Quiet Substation", 0.1),
            _asset("SUB-WATCH", "Tampa Watch Yard", 0.55),
            _asset("SUB-HIGH", "Blue Heron Solar", 0.91),
            _asset("SUB-HIGH2", "City of Sarasota WWTP", 0.88),
            _asset("SUB-DEC", "Punta Gorda Solar", 0.42, conflict=True),
            _asset("SUB-OTHER", "Fort Myers Beach Tap", 0.2),
        ]

    def test_search_matches_name_substring(self):
        out = filter_sites(self.assets, query="blue her")
        ids = [a["id"] for a in out]
        self.assertEqual(ids, ["SUB-HIGH"])
        self.assertNotIn("SUB-OTHER", ids)

    def test_search_matches_id(self):
        out = filter_sites(self.assets, query="sub-high2")
        self.assertEqual([a["id"] for a in out], ["SUB-HIGH2"])

    def test_search_empty_means_no_fallback_to_all(self):
        out = filter_sites(self.assets, query="zzzz-not-a-site")
        self.assertEqual(out, [])

    def test_search_does_not_inject_keep_id(self):
        out = filter_sites(
            self.assets,
            query="blue",
            keep_id="SUB-OTHER",
            inject_keep_when_searching=False,
        )
        self.assertEqual([a["id"] for a in out], ["SUB-HIGH"])

    def test_filter_high_risk(self):
        out = filter_sites(self.assets, show_band="High risk")
        ids = [a["id"] for a in out]
        self.assertEqual(ids, ["SUB-HIGH", "SUB-HIGH2"])

    def test_filter_decision_needed(self):
        out = filter_sites(self.assets, show_band="Decision needed")
        self.assertEqual([a["id"] for a in out], ["SUB-DEC"])

    def test_priority_order(self):
        out = filter_sites(self.assets, order_mode="Priority")
        ids = [a["id"] for a in out]
        # High first, then Needs attention, then Watch, then Low
        self.assertEqual(ids[0], "SUB-HIGH")
        self.assertEqual(ids[1], "SUB-HIGH2")
        self.assertEqual(ids[2], "SUB-DEC")
        self.assertEqual(ids[3], "SUB-WATCH")

    def test_name_order(self):
        out = filter_sites(self.assets, order_mode="Name A–Z")
        names = [a["name"] for a in out]
        self.assertEqual(names, sorted(names, key=str.lower))

    def test_keep_id_when_not_searching(self):
        out = filter_sites(
            self.assets,
            query="",
            show_band="High risk",
            keep_id="SUB-OTHER",
        )
        self.assertEqual(out[0]["id"], "SUB-OTHER")
        self.assertIn("SUB-HIGH", [a["id"] for a in out])


if __name__ == "__main__":
    unittest.main()
