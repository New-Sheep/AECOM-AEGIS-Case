"""Sprint 3 — FAKE LLM brief grounding + HITL shutdown / AuditLog."""

from __future__ import annotations

import os

from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from api.models import Asset, AuditLog, Dependency, ShadowLog, Telemetry, WeatherContext
from api.services.brief_schema import (
    ActionBrief,
    deterministic_validate,
    fake_action_brief,
)
from api.services.llm import (
    fake_brief_markdown,
    generate_action_brief,
    generate_action_brief_structured,
    suggest_action_level,
)


class FakeLlmTests(TestCase):
    def test_fake_brief_contains_risk_and_asset_id(self):
        facts = {
            "asset_id": "SUB-001",
            "name": "Demo Sub",
            "risk": 0.18,
            "confidence": 0.6,
            "conflict_flag": True,
            "drivers": ["surge_level", "wind_speed"],
            "downstream_ids": ["SUB-049"],
            "replacement_cost": 1_500_000,
            "elevation": 5.0,
            "sensors": {"load": 0.9, "oil_temp": 88.0, "voltage": 118.0},
            "weather": {"wind_speed": 120.0, "flood_surge_level": 12.0},
        }
        md = fake_brief_markdown(facts)
        self.assertIn("SUB-001", md)
        self.assertIn("WARNING", md)
        self.assertIn("Trade-off", md)
        self.assertIn("Oil temperature", md)

    def test_structured_fake_passes_grounding(self):
        os.environ["FAKE_LLM"] = "1"
        facts = {
            "asset_id": "SUB-001",
            "name": "Demo Sub",
            "risk": 0.18,
            "confidence": 0.6,
            "conflict_flag": True,
            "drivers": ["surge_level", "wind_speed"],
            "downstream_ids": ["SUB-049"],
            "replacement_cost": 1_500_000,
            "sensors": {"load": 0.9, "oil_temp": 88.0, "voltage": 118.0},
            "weather": {"wind_speed": 120.0, "flood_surge_level": 12.0},
        }
        brief, provider, issues = generate_action_brief_structured(facts)
        self.assertEqual(provider, "fake")
        self.assertIsInstance(brief, ActionBrief)
        self.assertEqual(brief.recommended_action, "deenergize")
        self.assertTrue(brief.conflict_warning)
        self.assertEqual(deterministic_validate(brief, facts), [])
        self.assertEqual(issues, [])

    def test_deterministic_rejects_invented_sensor(self):
        facts = {
            "asset_id": "SUB-007",
            "risk": 0.4,
            "conflict_flag": False,
            "sensors": {"load": 0.5, "oil_temp": 70.0},
            "weather": {"wind_speed": 30.0},
            "downstream_ids": [],
            "replacement_cost": 100,
        }
        brief = fake_action_brief(facts)
        bad = brief.model_copy(
            update={"cited_sensors": {**brief.cited_sensors, "made_up": 99.0}}
        )
        issues = deterministic_validate(bad, facts)
        self.assertTrue(any("invented sensor" in i for i in issues))

    def test_conflict_without_warning_fails_grounding(self):
        facts = {
            "asset_id": "SUB-001",
            "risk": 0.18,
            "conflict_flag": True,
            "sensors": {},
            "weather": {},
            "downstream_ids": [],
            "replacement_cost": 1,
        }
        brief = fake_action_brief(facts)
        stripped = brief.model_copy(update={"conflict_warning": None})
        issues = deterministic_validate(stripped, facts)
        self.assertTrue(any("conflict_warning" in i for i in issues))

    def test_generate_uses_fake_when_env_set(self):
        os.environ["FAKE_LLM"] = "1"
        facts = {
            "asset_id": "SUB-007",
            "name": "X",
            "risk": 0.42,
            "conflict_flag": False,
            "drivers": [],
            "downstream_ids": [],
            "replacement_cost": 100,
            "sensors": {},
            "weather": {},
        }
        md, provider = generate_action_brief(facts)
        self.assertEqual(provider, "fake")
        self.assertIn("SUB-007", md)
        self.assertIn("Watch", md)

    def test_suggest_deenergize_on_conflict(self):
        self.assertEqual(
            suggest_action_level({"risk": 0.1, "conflict_flag": True}),
            "deenergize",
        )


class ControlApiTests(TestCase):
    def setUp(self):
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
            risk_score=0.18,
            confidence=0.55,
            conflict_flag=True,
            drivers_json=["surge_level", "wind_speed"],
        )
        hospital = Asset.objects.create(
            external_id="SUB-049",
            name="Regional Hospital",
            asset_type="Hospital",
            lat=30.1,
            lon=-90.1,
            elevation=10.0,
            scada_link_id="SCADA-049",
            replacement_cost=0,
        )
        Dependency.objects.create(parent=self.asset, child=hospital)
        Telemetry.objects.create(
            asset=self.asset, load=0.85, oil_temp=78.0, voltage=120.0
        )
        WeatherContext.objects.create(
            asset=self.asset,
            wind_speed=115.0,
            flood_surge_level=12.0,
            storm_category="Cat3",
        )

    def test_action_brief_endpoint(self):
        os.environ["FAKE_LLM"] = "1"
        resp = self.client.get("/api/v1/assets/SUB-001/action_brief/")
        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        self.assertEqual(body["asset_id"], "SUB-001")
        self.assertEqual(body["provider"], "fake")
        self.assertIn("WARNING", body["markdown"])
        self.assertTrue(body["facts"]["conflict_flag"])

    def test_header_endpoint(self):
        resp = self.client.get("/api/v1/dashboard/header/")
        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        self.assertIn("threat_level", body)
        self.assertGreaterEqual(body["conflict_count"], 1)
        self.assertGreaterEqual(body["dollars_at_risk"], 0)

    def test_shutdown_requires_reason(self):
        resp = self.client.post(
            "/api/v1/control/shutdown/",
            {
                "asset_id": "SUB-001",
                "action_level": "load_shed",
                "authorization_token": "AEGIS-OPS",
                "reason_text": "",
            },
            format="json",
        )
        self.assertEqual(resp.status_code, 400)

    def test_l1_simulates_load_cut(self):
        before = Telemetry.objects.filter(asset=self.asset).latest("timestamp").load
        self.asset.conflict_flag = True
        self.asset.save(update_fields=["conflict_flag"])
        resp = self.client.post(
            "/api/v1/control/shutdown/",
            {
                "asset_id": "SUB-001",
                "action_level": "load_shed",
                "authorization_token": "AEGIS-OPS",
                "reason_text": "Demo load shed",
                "user_id": "demo-ic",
            },
            format="json",
        )
        self.assertEqual(resp.status_code, 201)
        body = resp.json()
        self.assertTrue(body["ok"])
        self.assertIn("human_summary", body)
        self.assertTrue(body.get("conflict_cleared"))
        self.assertAlmostEqual(float(body["load_before"]), float(before), places=3)
        self.assertAlmostEqual(
            float(body["load_after"]), max(0.05, float(before) * 0.8), places=3
        )
        after = Telemetry.objects.filter(asset=self.asset).latest("timestamp").load
        self.assertAlmostEqual(float(after), float(body["load_after"]), places=3)
        self.asset.refresh_from_db()
        self.assertFalse(self.asset.conflict_flag)

    def test_assistant_explains_surge(self):
        resp = self.client.post(
            "/api/v1/assistant/chat/",
            {
                "asset_id": "SUB-001",
                "message": "Why is surge a problem vs elevation?",
                "mode": "fake",
            },
            format="json",
        )
        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        self.assertIn("reply", body)
        self.assertTrue(
            "flood" in body["reply"].lower() or "surge" in body["reply"].lower()
        )

    def test_l4_requires_exec_token(self):
        resp = self.client.post(
            "/api/v1/control/shutdown/",
            {
                "asset_id": "SUB-001",
                "action_level": "deenergize",
                "authorization_token": "WRONG",
                "reason_text": "Storm surge risk",
            },
            format="json",
        )
        self.assertEqual(resp.status_code, 403)

    def test_l4_writes_audit_and_shadow(self):
        resp = self.client.post(
            "/api/v1/control/shutdown/",
            {
                "asset_id": "SUB-001",
                "action_level": "deenergize",
                "authorization_token": "AEGIS-EXEC-DEMO",
                "reason_text": "ConflictFlag + hospital downstream",
                "user_id": "demo-ic",
                "human_override": True,
            },
            format="json",
        )
        self.assertEqual(resp.status_code, 201)
        body = resp.json()
        self.assertTrue(body["ok"])
        self.assertEqual(AuditLog.objects.count(), 1)
        self.assertEqual(ShadowLog.objects.count(), 1)
        audit = AuditLog.objects.get()
        self.assertEqual(audit.action, "deenergize")
        self.assertEqual(audit.authorization_level, "L4")
        self.assertIn("hospital", audit.reason_text.lower())
        self.asset.refresh_from_db()
        self.assertFalse(self.asset.conflict_flag)
        tel = Telemetry.objects.filter(asset=self.asset).latest("timestamp")
        self.assertEqual(float(tel.load), 0.0)

    def test_forecast_series(self):
        resp = self.client.get("/api/v1/assets/SUB-001/forecast/")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(resp.json()["series"]), 12)
