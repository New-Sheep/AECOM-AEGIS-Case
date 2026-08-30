"""Doc 17 — customer attribution, finance explain APIs, grounded strategist."""

from __future__ import annotations

from django.test import TestCase
from rest_framework.test import APIClient

from api.models import Asset, Dependency, ScenarioClock, Telemetry, WeatherContext
from api.services import impact_economy as eco
from api.services.assistant import _CONV_SNAPSHOTS, answer_assistant


class ImpactEconomyTests(TestCase):
    def setUp(self):
        eco.clear_customer_cache()
        self.assets = []
        types = [
            ("SUB-001", "Transformer"),
            ("SUB-002", "Switchgear"),
            ("SUB-003", "Hospital"),
            ("SUB-004", "WaterPlant"),
            ("SUB-005", "Pump"),
        ]
        for eid, atype in types:
            self.assets.append(
                Asset.objects.create(
                    external_id=eid,
                    name=f"Site {eid}",
                    asset_type=atype,
                    lat=30.0,
                    lon=-90.0,
                    elevation=5.0,
                    scada_link_id=f"SCADA-{eid}",
                    replacement_cost=1_000_000,
                    risk_score=0.8 if eid == "SUB-001" else 0.2,
                    conflict_flag=eid == "SUB-001",
                )
            )
        WeatherContext.objects.create(
            asset=self.assets[0],
            wind_speed=90.0,
            flood_surge_level=4.0,
            storm_category="Active severe weather",
        )
        ScenarioClock.get_solo()

    def tearDown(self):
        eco.clear_customer_cache()
        _CONV_SNAPSHOTS.clear()

    def test_territory_customers_sum_to_8m(self):
        total = sum(eco.customers_map().values())
        self.assertEqual(total, eco.TERRITORY_CUSTOMERS)
        self.assertAlmostEqual(total / 8_000_000, 1.0, delta=0.01)

    def test_finance_formula_matches_constants(self):
        clock = ScenarioClock.get_solo()
        clock.sim_phase = "peak"
        clock.save(update_fields=["sim_phase"])
        fin = eco.finance_breakdown()
        flagged = [
            a
            for a in Asset.objects.all()
            if a.risk_score > 0.7 or a.conflict_flag
        ]
        expected_cust = sum(eco.customers_for_asset(a) for a in flagged)
        hrs = eco.hours_at_risk("peak")
        expected_outage = round(
            expected_cust * hrs * eco.VOLL_PER_CUSTOMER_HOUR_USD, 2
        )
        self.assertEqual(fin["customers_at_risk"], expected_cust)
        self.assertEqual(fin["hours_at_risk"], hrs)
        self.assertEqual(fin["illustrative_outage_cost_usd"], expected_outage)
        self.assertTrue(fin["methodology"])
        self.assertIn("Illustrative", fin["methodology"])
        self.assertIn("CapEx_at_risk", fin["methodology"])
        self.assertEqual(
            fin["constants"]["voll_per_customer_hour_usd"],
            eco.VOLL_PER_CUSTOMER_HOUR_USD,
        )

    def test_site_explain_includes_customers(self):
        site = eco.site_explain(self.assets[0])
        self.assertIn("customers_served", site)
        self.assertGreater(site["customers_served"], 0)
        self.assertFalse(site["critical_lifeline"])
        hosp = eco.site_explain(self.assets[2])
        self.assertTrue(hosp["critical_lifeline"])


class ExplainApiTests(TestCase):
    def setUp(self):
        eco.clear_customer_cache()
        self.client = APIClient()
        self.asset = Asset.objects.create(
            external_id="SUB-001",
            name="Coastal Transformer 1",
            asset_type="Transformer",
            lat=30.0,
            lon=-90.0,
            elevation=5.0,
            scada_link_id="SCADA-001",
            replacement_cost=2_000_000,
            risk_score=0.85,
            confidence=0.55,
            conflict_flag=True,
            drivers_json=["surge_level"],
        )
        hosp = Asset.objects.create(
            external_id="SUB-049",
            name="Regional Hospital",
            asset_type="Hospital",
            lat=30.1,
            lon=-90.1,
            elevation=10.0,
            scada_link_id="SCADA-049",
            replacement_cost=500_000,
            risk_score=0.2,
        )
        Dependency.objects.create(parent=self.asset, child=hosp)
        Telemetry.objects.create(
            asset=self.asset, load=0.85, oil_temp=78.0, voltage=120.0
        )
        WeatherContext.objects.create(
            asset=self.asset,
            wind_speed=115.0,
            flood_surge_level=12.0,
            storm_category="Cat3",
        )

    def tearDown(self):
        eco.clear_customer_cache()
        _CONV_SNAPSHOTS.clear()

    def test_explain_site(self):
        resp = self.client.get("/api/v1/explain/site/SUB-001/")
        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        self.assertEqual(body["asset_id"], "SUB-001")
        self.assertGreater(body["customers_served"], 0)
        self.assertIn("sensors", body)
        self.assertIn("weather", body)

    def test_explain_region_customers_near_8m(self):
        resp = self.client.get("/api/v1/explain/region/")
        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        self.assertEqual(body["territory_customers"], 8_000_000)
        self.assertAlmostEqual(
            body["customers_total"] / 8_000_000, 1.0, delta=0.01
        )

    def test_explain_finance_methodology(self):
        resp = self.client.get("/api/v1/explain/finance/")
        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        self.assertTrue(body["methodology"])
        self.assertIn("voll_per_customer_hour_usd", body["constants"])

    def test_explain_customers_and_deps(self):
        resp = self.client.get("/api/v1/explain/customers/?asset_id=SUB-001")
        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        self.assertIsNotNone(body.get("site"))
        self.assertGreater(body["site"]["customers_served"], 0)
        resp2 = self.client.get("/api/v1/explain/dependencies/SUB-001/")
        self.assertEqual(resp2.status_code, 200)
        dep = resp2.json()
        self.assertGreaterEqual(dep["downstream_count"], 1)

    def test_header_exposes_outage_fields(self):
        resp = self.client.get("/api/v1/dashboard/header/")
        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        self.assertIn("illustrative_outage_cost_usd", body)
        self.assertIn("customers_at_risk", body)
        self.assertIn("finance_methodology", body)


class StrategistGroundingTests(TestCase):
    def setUp(self):
        eco.clear_customer_cache()
        _CONV_SNAPSHOTS.clear()
        self.client = APIClient()
        self.asset = Asset.objects.create(
            external_id="SUB-001",
            name="Coastal Transformer 1",
            asset_type="Transformer",
            lat=30.0,
            lon=-90.0,
            elevation=5.0,
            scada_link_id="SCADA-001",
            replacement_cost=2_000_000,
            risk_score=0.85,
            conflict_flag=True,
        )
        Asset.objects.create(
            external_id="SUB-010",
            name="Inland Pump",
            asset_type="Pump",
            lat=30.2,
            lon=-90.2,
            elevation=12.0,
            scada_link_id="SCADA-010",
            replacement_cost=100_000,
            risk_score=0.1,
        )
        WeatherContext.objects.create(
            asset=self.asset,
            wind_speed=100.0,
            flood_surge_level=8.0,
            storm_category="Cat3",
        )

    def tearDown(self):
        eco.clear_customer_cache()
        _CONV_SNAPSHOTS.clear()

    def test_who_is_affected_uses_customer_tool(self):
        cust = eco.customers_for_asset(self.asset)
        resp = self.client.post(
            "/api/v1/assistant/chat/",
            {
                "asset_id": "SUB-001",
                "message": "Who is affected?",
                "mode": "fake",
                "conversation_id": "conv-cust-1",
            },
            format="json",
        )
        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        calls = body.get("tool_calls") or []
        self.assertTrue(any(c.get("name") == "get_customer_impact" for c in calls))
        self.assertIn(f"{cust:,}", body["reply"])
        self.assertIn("8,000,000", body["reply"])

    def test_how_is_dollar_calculated(self):
        fin = eco.finance_breakdown()
        resp = self.client.post(
            "/api/v1/assistant/chat/",
            {
                "asset_id": "SUB-001",
                "message": "How is $ calculated?",
                "mode": "fake",
                "conversation_id": "conv-fin-1",
            },
            format="json",
        )
        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        calls = body.get("tool_calls") or []
        self.assertTrue(any(c.get("name") == "get_finance_breakdown" for c in calls))
        reply = body["reply"]
        self.assertIn(f"{fin['capex_at_risk_usd']:,.0f}", reply)
        self.assertIn("Equipment at risk", reply)
        self.assertIn("Customer outage estimate", reply)
        self.assertIn("How money is calculated", reply)

    def test_follow_up_after_finance_stays_grounded(self):
        cid = "conv-follow-1"
        first = answer_assistant(
            asset_id="SUB-001",
            message="How is $ calculated?",
            mode="fake",
            conversation_id=cid,
        )
        self.assertTrue(
            any(c.get("name") == "get_finance_breakdown" for c in first["tool_calls"])
        )
        follow = answer_assistant(
            asset_id="SUB-001",
            message="why that $?",
            mode="fake",
            conversation_id=cid,
            history=[
                {"role": "user", "content": "How is $ calculated?"},
                {"role": "assistant", "content": first["reply"]},
            ],
        )
        self.assertIn("How money is calculated", follow["reply"])
        self.assertIn("Equipment at risk", follow["reply"])
        # Should reuse finance numbers, not invent new ones
        fin = eco.finance_breakdown()
        self.assertIn(
            f"{int(fin['customers_at_risk']):,}", follow["reply"]
        )

    def test_unknown_topic_say_unknown(self):
        resp = self.client.post(
            "/api/v1/assistant/chat/",
            {
                "asset_id": "SUB-001",
                "message": "What is the capital of France?",
                "mode": "fake",
                "conversation_id": "conv-unk-1",
            },
            format="json",
        )
        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        calls = body.get("tool_calls") or []
        self.assertTrue(any(c.get("name") == "say_unknown" for c in calls))
        self.assertIn("don't know", body["reply"].lower())

    def test_region_outlook_tool(self):
        resp = self.client.post(
            "/api/v1/assistant/chat/",
            {
                "asset_id": "SUB-001",
                "message": "Region outlook",
                "mode": "fake",
            },
            format="json",
        )
        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        self.assertTrue(
            any(c.get("name") == "get_region_situation" for c in body["tool_calls"])
        )
        self.assertIn("8,000,000", body["reply"])

    def test_list_priority_sites_orders_bands_excludes_low(self):
        from api.services.assistant import run_tool

        # SUB-001 already Needs attention (conflict). Add High / Watch / Low.
        Asset.objects.create(
            external_id="SUB-HIGH",
            name="High Risk Yard",
            asset_type="Transformer",
            lat=30.1,
            lon=-90.1,
            elevation=6.0,
            scada_link_id="SCADA-HIGH",
            replacement_cost=500_000,
            risk_score=0.9,
            conflict_flag=False,
        )
        Asset.objects.create(
            external_id="SUB-HIGH2",
            name="High Risk B",
            asset_type="Switchgear",
            lat=30.15,
            lon=-90.15,
            elevation=7.0,
            scada_link_id="SCADA-HIGH2",
            replacement_cost=400_000,
            risk_score=0.75,
            conflict_flag=False,
        )
        Asset.objects.create(
            external_id="SUB-WATCH",
            name="Watch Site",
            asset_type="Pump",
            lat=30.18,
            lon=-90.18,
            elevation=8.0,
            scada_link_id="SCADA-WATCH",
            replacement_cost=50_000,
            risk_score=0.5,
            conflict_flag=False,
        )
        # SUB-010 remains Low (0.1) from setUp — must be excluded

        data = run_tool("list_priority_sites", {}, {"asset_id": "SUB-001"})
        bands = [s["band"] for s in data["sites"]]
        ids = [s["asset_id"] for s in data["sites"]]

        self.assertNotIn("Low", bands)
        self.assertNotIn("SUB-010", ids)
        # High first (by severity), then Needs attention, then Watch
        self.assertEqual(bands[0], "High")
        self.assertEqual(ids[0], "SUB-HIGH")
        self.assertEqual(ids[1], "SUB-HIGH2")
        self.assertEqual(bands[2], "Needs attention")
        self.assertEqual(ids[2], "SUB-001")
        self.assertEqual(bands[3], "Watch")
        self.assertEqual(ids[3], "SUB-WATCH")

        resp = self.client.post(
            "/api/v1/assistant/chat/",
            {
                "asset_id": "SUB-001",
                "message": "Site priority list: red and orange sites from most critical to least",
                "mode": "fake",
            },
            format="json",
        )
        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        self.assertTrue(
            any(c.get("name") == "list_priority_sites" for c in body["tool_calls"])
        )
        self.assertIn("decision needed", body["reply"].lower())
        self.assertIn("handle in this order", body["reply"].lower())
        self.assertNotIn("model severity", body["reply"].lower())

    def test_list_priority_sites_live_mode_uses_tool_prose(self):
        """Live mode must not LLM-refuse red/orange — use deterministic bands."""
        Asset.objects.create(
            external_id="SUB-HIGH",
            name="High Risk Yard",
            asset_type="Transformer",
            lat=30.1,
            lon=-90.1,
            elevation=6.0,
            scada_link_id="SCADA-HIGH",
            replacement_cost=500_000,
            risk_score=0.9,
            conflict_flag=False,
        )
        resp = self.client.post(
            "/api/v1/assistant/chat/",
            {
                "asset_id": "SUB-001",
                "message": "Site priority list: red and orange sites from most critical to least",
                "mode": "live",
            },
            format="json",
        )
        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        self.assertTrue(
            any(c.get("name") == "list_priority_sites" for c in body["tool_calls"])
        )
        reply = body["reply"].lower()
        self.assertIn("decision needed", reply)
        self.assertNotIn("don't know the red and orange", reply)
        self.assertEqual(body.get("provider"), "tools")
