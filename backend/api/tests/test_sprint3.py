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

    def test_suggest_monitor_when_stable(self):
        self.assertEqual(
            suggest_action_level(
                {
                    "risk": 0.1,
                    "conflict_flag": False,
                    "weather": {"wind_speed": 44.0, "flood_surge_level": 0.7},
                    "sensors": {"oil_temp": 47.5},
                    "elevation": 10.0,
                }
            ),
            "monitor",
        )

    def test_stable_brief_recommends_monitor(self):
        facts = {
            "asset_id": "SUB-048",
            "name": "Tampa General Hospital",
            "risk": 0.12,
            "conflict_flag": False,
            "drivers": ["oil_temp", "wind_speed", "load"],
            "downstream_ids": [],
            "replacement_cost": 13_792_000,
            "elevation": 10.0,
            "sensors": {"load": 0.52, "oil_temp": 47.5, "voltage": 120.0},
            "weather": {"wind_speed": 44.0, "flood_surge_level": 0.7},
        }
        brief = fake_action_brief(facts)
        self.assertEqual(brief.recommended_action, "monitor")
        self.assertIn("stable", (brief.summary or "").lower())
        from api.services.brief_schema import render_brief_markdown

        md = render_brief_markdown(brief)
        self.assertIn("Keep monitoring", md)
        self.assertNotIn("Confirm under Approve", md)

    def test_summary_without_conflict_avoids_needs_attention(self):
        facts = {
            "asset_id": "SUB-007",
            "name": "Inland Sub",
            "risk": 0.42,
            "conflict_flag": False,
            "drivers": [],
            "downstream_ids": [],
            "replacement_cost": 100,
            "elevation": 20.0,
            "sensors": {"load": 0.5, "oil_temp": 70.0},
            "weather": {"wind_speed": 115.0, "flood_surge_level": 3.0},
        }
        brief = fake_action_brief(facts)
        lower = (brief.summary or "").lower()
        self.assertNotIn("needs attention", lower)
        self.assertNotIn("needs a decision", lower)
        self.assertTrue(
            "under watch" in lower or "stable" in lower or "conditions" in lower
        )

    def test_summary_with_conflict_says_needs_decision(self):
        facts = {
            "asset_id": "SUB-001",
            "name": "Coastal Sub",
            "risk": 0.2,
            "conflict_flag": True,
            "drivers": ["surge_level"],
            "downstream_ids": [],
            "replacement_cost": 100,
            "elevation": 5.0,
            "sensors": {},
            "weather": {"wind_speed": 115.0, "flood_surge_level": 12.0},
        }
        brief = fake_action_brief(facts)
        self.assertIn("needs a decision", (brief.summary or "").lower())
        self.assertNotIn("needs attention", (brief.summary or "").lower())

    def test_engineer_markdown_has_no_h1(self):
        facts = {
            "asset_id": "SUB-007",
            "name": "X",
            "risk": 0.4,
            "conflict_flag": False,
            "drivers": [],
            "downstream_ids": [],
            "replacement_cost": 100,
            "sensors": {},
            "weather": {},
        }
        brief = fake_action_brief(facts)
        from api.services.brief_schema import render_brief_markdown

        md = render_brief_markdown(brief)
        self.assertFalse(md.lstrip().startswith("# "))
        self.assertNotIn("\n# ", md)
        self.assertNotIn("\n## ", md)


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
        self.assertEqual(body["threat_level"], "CRITICAL")
        self.assertIn("service territory", body.get("scenario", ""))

    def test_header_high_wind_alone_is_elevated_not_critical(self):
        Asset.objects.all().update(conflict_flag=False, risk_score=0.2)
        WeatherContext.objects.all().update(
            wind_speed=115.0, flood_surge_level=4.0, storm_category="Cat3"
        )
        resp = self.client.get("/api/v1/dashboard/header/")
        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        self.assertEqual(body["conflict_count"], 0)
        self.assertEqual(body["threat_level"], "ELEVATED")
        self.assertEqual(body["storm_category"], "Active severe weather")
        self.assertTrue(body.get("severe_weather"))

    def test_assistant_attention_empty_when_no_flags(self):
        Asset.objects.all().update(conflict_flag=False)
        resp = self.client.post(
            "/api/v1/assistant/chat/",
            {
                "asset_id": "SUB-001",
                "message": "Which sites need attention?",
                "mode": "fake",
            },
            format="json",
        )
        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        self.assertIn("no sites need a decision", body["reply"].lower())
        calls = body.get("tool_calls") or []
        self.assertTrue(any(c.get("name") == "list_attention_sites" for c in calls))

    def test_assistant_explain_warning_mentions_weather_without_flag(self):
        Asset.objects.filter(external_id="SUB-001").update(conflict_flag=False)
        resp = self.client.post(
            "/api/v1/assistant/chat/",
            {
                "asset_id": "SUB-001",
                "message": "Explain this warning",
                "mode": "fake",
            },
            format="json",
        )
        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        lower = body["reply"].lower()
        self.assertIn("no decision flag", lower)
        self.assertTrue("elevated" in lower or "wind" in lower)

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
        self.assertIn("tool_calls", body)

    def test_assistant_what_should_i_do_pending(self):
        resp = self.client.post(
            "/api/v1/assistant/chat/",
            {
                "asset_id": "SUB-001",
                "message": "What should I do?",
                "mode": "fake",
            },
            format="json",
        )
        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        self.assertIn("reply", body)
        self.assertTrue(body.get("tool_calls"))
        pending = body.get("pending_actions") or []
        self.assertTrue(pending)
        names = {p.get("name") for p in pending}
        self.assertTrue(names & {"reduce_load", "shutdown", "reroute"})
        for p in pending:
            self.assertTrue(p.get("requires_confirm"))

    def test_assistant_what_should_i_do_stable_no_pending(self):
        Asset.objects.filter(external_id="SUB-001").update(
            conflict_flag=False, risk_score=0.12
        )
        WeatherContext.objects.filter(asset=self.asset).update(
            wind_speed=44.0, flood_surge_level=0.7
        )
        Telemetry.objects.filter(asset=self.asset).update(oil_temp=47.5, load=0.52)
        resp = self.client.post(
            "/api/v1/assistant/chat/",
            {
                "asset_id": "SUB-001",
                "message": "What should I do?",
                "mode": "fake",
            },
            format="json",
        )
        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        self.assertIn("keep monitoring", body["reply"].lower())
        self.assertFalse(body.get("pending_actions"))
        self.assertIsNone(body.get("proposed_action"))

    def test_assistant_impact_tool(self):
        resp = self.client.post(
            "/api/v1/assistant/chat/",
            {
                "asset_id": "SUB-001",
                "message": "Who loses power if this site goes down?",
                "mode": "fake",
            },
            format="json",
        )
        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        calls = body.get("tool_calls") or []
        self.assertTrue(
            any(
                c.get("name") in {"list_impact", "get_dependency_impact"}
                for c in calls
            )
        )
        self.assertIn("power", body["reply"].lower())

    def test_assistant_attention_sites_tool(self):
        resp = self.client.post(
            "/api/v1/assistant/chat/",
            {
                "asset_id": "SUB-001",
                "message": "Which sites need attention?",
                "mode": "fake",
            },
            format="json",
        )
        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        calls = body.get("tool_calls") or []
        self.assertTrue(any(c.get("name") == "list_attention_sites" for c in calls))

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
        self.assertEqual(self.asset.operational_state, "deenergized")

    def test_duplicate_deenergize_returns_409(self):
        payload = {
            "asset_id": "SUB-001",
            "action_level": "deenergize",
            "authorization_token": "AEGIS-EXEC-DEMO",
            "reason_text": "first shutdown",
            "user_id": "demo-ic",
        }
        first = self.client.post("/api/v1/control/shutdown/", payload, format="json")
        self.assertEqual(first.status_code, 201)
        second = self.client.post(
            "/api/v1/control/shutdown/",
            {**payload, "reason_text": "cool"},
            format="json",
        )
        self.assertEqual(second.status_code, 409)
        self.assertEqual(AuditLog.objects.filter(action="deenergize").count(), 1)

    def test_duplicate_load_shed_returns_409(self):
        payload = {
            "asset_id": "SUB-001",
            "action_level": "load_shed",
            "authorization_token": "AEGIS-OPS",
            "reason_text": "first shed",
        }
        self.assertEqual(
            self.client.post("/api/v1/control/shutdown/", payload, format="json").status_code,
            201,
        )
        again = self.client.post(
            "/api/v1/control/shutdown/",
            {**payload, "reason_text": "again"},
            format="json",
        )
        self.assertEqual(again.status_code, 409)

    def test_restore_load_after_shed(self):
        before = float(
            Telemetry.objects.filter(asset=self.asset).latest("timestamp").load
        )
        shed = self.client.post(
            "/api/v1/control/shutdown/",
            {
                "asset_id": "SUB-001",
                "action_level": "load_shed",
                "authorization_token": "AEGIS-OPS",
                "reason_text": "shed",
            },
            format="json",
        )
        self.assertEqual(shed.status_code, 201)
        self.asset.refresh_from_db()
        self.assertEqual(self.asset.operational_state, "load_reduced")
        rest = self.client.post(
            "/api/v1/control/shutdown/",
            {
                "asset_id": "SUB-001",
                "action_level": "restore_load",
                "authorization_token": "AEGIS-OPS",
                "reason_text": "restore",
            },
            format="json",
        )
        self.assertEqual(rest.status_code, 201)
        self.asset.refresh_from_db()
        self.assertEqual(self.asset.operational_state, "normal")
        tel = Telemetry.objects.filter(asset=self.asset).latest("timestamp")
        self.assertAlmostEqual(float(tel.load), before, places=3)

    def test_reenergize_after_shutdown(self):
        self.client.post(
            "/api/v1/control/shutdown/",
            {
                "asset_id": "SUB-001",
                "action_level": "deenergize",
                "authorization_token": "AEGIS-EXEC-DEMO",
                "reason_text": "down",
            },
            format="json",
        )
        up = self.client.post(
            "/api/v1/control/shutdown/",
            {
                "asset_id": "SUB-001",
                "action_level": "reenergize",
                "authorization_token": "AEGIS-EXEC-DEMO",
                "reason_text": "back up",
            },
            format="json",
        )
        self.assertEqual(up.status_code, 201)
        self.asset.refresh_from_db()
        self.assertEqual(self.asset.operational_state, "normal")
        tel = Telemetry.objects.filter(asset=self.asset).latest("timestamp")
        self.assertGreater(float(tel.load), 0.0)

    def test_scenario_tick_increments(self):
        from api.models import ScenarioClock

        clock = ScenarioClock.get_solo()
        clock.sim_tick = 0
        clock.paused = False
        clock.save()
        before_wind = float(
            WeatherContext.objects.filter(asset=self.asset).latest("timestamp").wind_speed
        )
        resp = self.client.post("/api/v1/scenario/tick/", {"force": True}, format="json")
        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        self.assertTrue(body.get("advanced"))
        self.assertEqual(body["sim_tick"], 1)
        self.assertIn("sim_phase", body)
        # Nudge may or may not hit this asset; header still exposes clock
        header = self.client.get("/api/v1/dashboard/header/").json()
        self.assertEqual(header["sim_tick"], 1)
        self.assertIn("sim_time_label", header)
        _ = before_wind

    def test_scenario_reset_reseeds_conflicts(self):
        Asset.objects.all().update(conflict_flag=False, operational_state="deenergized")
        resp = self.client.post(
            "/api/v1/scenario/reset/", {"seed": 42}, format="json"
        )
        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        self.assertEqual(body["sim_tick"], 0)
        self.assertEqual(body["sim_phase"], "peak")
        self.assertGreaterEqual(body["conflict_count"], 1)
        self.assertFalse(
            Asset.objects.filter(operational_state="deenergized").exists()
        )

    def test_forecast_series(self):
        resp = self.client.get("/api/v1/assets/SUB-001/forecast/")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(resp.json()["series"]), 12)
