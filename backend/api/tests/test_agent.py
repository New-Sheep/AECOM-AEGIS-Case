"""Sprint 4a — LangGraph agent + nervous-system API tests."""

from __future__ import annotations

import os

from django.test import TestCase
from rest_framework.test import APIClient

from api.agent.graph import resume_agent, run_agent
from api.models import Asset, Dependency, Telemetry, WeatherContext
from api.services.graph import clear_graph_cache


class AgentGraphFixtureMixin:
    def seed_assets(self):
        clear_graph_cache()
        self.asset = Asset.objects.create(
            external_id="SUB-010",
            name="Agent Demo Transformer",
            asset_type="Transformer",
            lat=30.0,
            lon=-90.0,
            elevation=12.0,
            scada_link_id="SCADA-010",
            replacement_cost=900_000,
            risk_score=0.4,
            confidence=1.0,
            conflict_flag=False,
            drivers_json=[],
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
            asset=self.asset, load=0.55, oil_temp=72.0, voltage=120.0
        )
        WeatherContext.objects.create(
            asset=self.asset,
            wind_speed=45.0,
            flood_surge_level=2.0,
            storm_category="Clear",
        )


class LangGraphUnitTests(AgentGraphFixtureMixin, TestCase):
    def setUp(self):
        os.environ["FAKE_LLM"] = "1"
        self.seed_assets()

    def test_clean_path_completes_with_brief(self):
        result = run_agent(self.asset.external_id, force_anomaly=False, force_normal=True)
        self.assertEqual(result["status"], "completed")
        self.assertFalse(result["is_anomaly"])
        self.assertIsInstance(result["risk_score"], float)
        self.assertIn("SUB-049", result["impact_nodes"])
        self.assertIn(self.asset.external_id, result["action_plan"])
        self.assertTrue(result["recommendation"])

    def test_anomaly_interrupts_then_resume_approved(self):
        result = run_agent(self.asset.external_id, force_anomaly=True)
        self.assertEqual(result["status"], "interrupted")
        self.assertTrue(result["is_anomaly"])
        self.assertIn("thread_id", result)

        done = resume_agent(
            result["thread_id"],
            decision="approved",
            reason_text="Operator OK to continue",
        )
        self.assertEqual(done["status"], "completed")
        self.assertTrue(done["action_plan"])
        self.assertIn("SUB-049", done["impact_nodes"])

    def test_anomaly_reject_halts(self):
        result = run_agent(self.asset.external_id, force_anomaly=True)
        done = resume_agent(
            result["thread_id"],
            decision="rejected",
            reason_text="Hold for field crew",
        )
        self.assertEqual(done["status"], "completed")
        self.assertEqual(done["approval_status"], "rejected")
        self.assertIn("Held for Manual Audit", done["action_plan"])


class NervousSystemApiTests(AgentGraphFixtureMixin, TestCase):
    def setUp(self):
        os.environ["FAKE_LLM"] = "1"
        self.seed_assets()
        self.client = APIClient()

    def test_predict_endpoint(self):
        resp = self.client.post(
            "/api/v1/predict/",
            {"asset_id": "SUB-010", "load": 0.6, "wind_speed": 50},
            format="json",
        )
        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        self.assertEqual(body["asset_id"], "SUB-010")
        self.assertIn("risk_score", body)
        self.assertIn("anomaly_score", body)

    def test_impact_endpoint(self):
        resp = self.client.get("/api/v1/impact/SUB-010/")
        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        self.assertIn("SUB-049", body["impacted_assets"])
        self.assertGreaterEqual(body["criticality_score"], 0.4)

    def test_brief_endpoint(self):
        resp = self.client.post(
            "/api/v1/brief/",
            {"asset_id": "SUB-010"},
            format="json",
        )
        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        self.assertIn("recommendation", body)
        self.assertTrue(body["context_str"] or body["action_plan"])

    def test_agent_run_resume_api(self):
        resp = self.client.post(
            "/api/v1/agent/run/",
            {"asset_id": "SUB-010", "force_anomaly": True},
            format="json",
        )
        self.assertEqual(resp.status_code, 202)
        body = resp.json()
        self.assertEqual(body["status"], "interrupted")

        resp2 = self.client.post(
            "/api/v1/agent/resume/",
            {
                "thread_id": body["thread_id"],
                "decision": "approved",
                "reason_text": "API test approve",
            },
            format="json",
        )
        self.assertEqual(resp2.status_code, 200)
        done = resp2.json()
        self.assertEqual(done["status"], "completed")
        self.assertTrue(done["action_plan"])
