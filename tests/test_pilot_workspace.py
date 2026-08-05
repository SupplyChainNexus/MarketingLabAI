"""Synthetic end-to-end tests for the thin secure pilot workspace."""

from __future__ import annotations

import io
import json
import unittest
from pathlib import Path

from app.pilot_workspace import PilotWorkspaceApplication
from tests import test_pilot_api


class PilotWorkspaceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.fixture = test_pilot_api.PilotApiTests()
        self.fixture.setUp()
        self.workspace = PilotWorkspaceApplication(self.fixture.service)

    def tearDown(self) -> None:
        self.fixture.tearDown()

    def get(self, path: str) -> tuple[int, dict[str, str], bytes]:
        captured = {}

        def start_response(status, headers):
            captured["status"] = int(status.split()[0])
            captured["headers"] = dict(headers)

        body = b"".join(
            self.workspace({"REQUEST_METHOD": "GET", "PATH_INFO": path}, start_response)
        )
        return captured["status"], captured["headers"], body

    def test_workspace_serves_guided_synthetic_pilot_surface(self) -> None:
        status, headers, body = self.get("/pilot")
        text = body.decode()
        self.assertEqual(status, 200)
        self.assertIn("Synthetic pilot only", text)
        self.assertIn("Context readiness", text)
        self.assertIn("Campaign Plan review", text)
        self.assertIn("Marketing Brief review", text)
        self.assertIn("Independent compliance review", text)
        self.assertIn("Authorize safe export", text)
        self.assertNotIn("publish", text.lower().replace("never publishes", ""))
        self.assertIn("frame-ancestors 'none'", headers["Content-Security-Policy"])
        self.assertEqual(headers["Cache-Control"], "no-store")

    def test_workspace_assets_are_same_origin_and_framework_neutral(self) -> None:
        for path, content_type in (
            ("/pilot/workspace.css", "text/css"),
            ("/pilot/workspace.js", "application/javascript"),
        ):
            status, headers, body = self.get(path)
            self.assertEqual(status, 200)
            self.assertTrue(headers["Content-Type"].startswith(content_type))
            self.assertTrue(body)
        source = Path("app/pilot_workspace/wsgi.py").read_text(encoding="utf-8")
        for forbidden in (
            "CanonicalApplication",
            "app.database",
            "campaign_planner.repository",
            "marketing_brief.repository",
        ):
            self.assertNotIn(forbidden, source)

    def test_workflow_review_returns_safe_views_and_readiness(self) -> None:
        status, payload = self.fixture.request(
            "/v1/pilot/workflow-review",
            {
                "brand_id": "brand-one",
                "campaign_id": "campaign-one",
                "brief_id": "brief-one",
            },
        )
        self.assertEqual(status, 200)
        data = payload["data"]
        self.assertTrue(data["generation_ready"])
        self.assertEqual(data["campaign_plan"]["status"], "approved")
        self.assertEqual(data["marketing_brief"]["status"], "approved")
        self.assertNotIn("tenant_id", data["campaign_plan"])
        self.assertNotIn("tenant_id", data["marketing_brief"])
        self.assertNotIn("evidence", data["marketing_brief"])

    def test_guided_onboarding_persists_verified_synthetic_context(self) -> None:
        status, payload = self.fixture.request(
            "/v1/pilot/onboarding/context",
            {
                "brand_id": "brand-one",
                "business": {
                    "revenue_model": "Synthetic subscriptions",
                    "geographic_markets": ["Synthetic market"],
                    "business_goals": ["Validate the guided pilot"],
                },
                "customer": {
                    "segment_id": "segment-pilot",
                    "name": "Synthetic pilot segment",
                    "summary": "Verified synthetic customer context.",
                    "description": "Synthetic customers only.",
                    "evidence_source": "Synthetic customer interview",
                },
                "product": {
                    "product_id": "product-pilot",
                    "name": "Synthetic pilot service",
                    "product_type": "service",
                    "description": "Synthetic verified service.",
                    "evidence_source": "Synthetic approved catalogue",
                    "features": ["Guided workflow"],
                    "benefits": ["Consistent review"],
                    "limitations": ["Synthetic use only"],
                    "prohibited_claims": ["Guaranteed outcome"],
                },
            },
            idempotency_key="onboarding-one",
        )
        self.assertEqual(status, 200)
        self.assertEqual(
            payload["data"]["verified_sections"], ["company", "customer", "product"]
        )
        context_status, context = self.fixture.request(
            "/v1/pilot/context", {"brand_id": "brand-one"}
        )
        self.assertEqual(context_status, 200)
        self.assertFalse(context["data"]["missing"]["company"])
        self.assertFalse(context["data"]["missing"]["customer"])
        self.assertFalse(context["data"]["missing"]["product"])
        self.assertIn("Synthetic subscriptions", context["data"]["company_context"])

    def test_revision_creates_planned_version_and_locks_generation(self) -> None:
        status, payload = self.fixture.request(
            "/v1/pilot/campaign-plans/campaign-one/revise",
            {"expected_version": 1, "changes": {"notes": "Synthetic revision"}},
            idempotency_key="revision-one",
        )
        self.assertEqual(status, 200)
        self.assertEqual(payload["data"]["version"], 2)
        self.assertEqual(payload["data"]["status"], "planned")
        review_status, review = self.fixture.request(
            "/v1/pilot/workflow-review",
            {
                "brand_id": "brand-one",
                "campaign_id": "campaign-one",
                "brief_id": "brief-one",
            },
        )
        self.assertEqual(review_status, 200)
        self.assertFalse(review["data"]["generation_ready"])
        approval_status, approval = self.fixture.request(
            "/v1/pilot/campaign-plans/campaign-one/approve",
            {"expected_version": 2},
            idempotency_key="revised-plan-approval",
        )
        self.assertEqual(approval_status, 200)
        self.assertEqual(approval["data"]["version"], 3)
        final_status, final_review = self.fixture.request(
            "/v1/pilot/workflow-review",
            {
                "brand_id": "brand-one",
                "campaign_id": "campaign-one",
                "brief_id": "brief-one",
            },
        )
        self.assertEqual(final_status, 200)
        self.assertTrue(final_review["data"]["generation_ready"])

    def test_revision_rejects_protected_or_stale_changes(self) -> None:
        status, payload = self.fixture.request(
            "/v1/pilot/marketing-briefs/brief-one/revise",
            {"expected_version": 1, "changes": {"tenant_id": "tenant-two"}},
            idempotency_key="protected-revision",
        )
        self.assertEqual(status, 400)
        self.assertEqual(payload["error"]["code"], "invalid_request")
        self.fixture.request(
            "/v1/pilot/marketing-briefs/brief-one/revise",
            {"expected_version": 1, "changes": {"notes": "First revision"}},
            idempotency_key="brief-revision-one",
        )
        status, payload = self.fixture.request(
            "/v1/pilot/marketing-briefs/brief-one/revise",
            {"expected_version": 1, "changes": {"notes": "Stale revision"}},
            idempotency_key="brief-revision-stale",
        )
        self.assertEqual(status, 409)
        self.assertEqual(payload["error"]["code"], "lifecycle_conflict")

    def test_generation_exposes_independent_compliance_limitations_and_audit(self):
        status, payload = self.fixture.request(
            "/v1/pilot/generate",
            self.fixture.generation_body(),
            idempotency_key="workspace-generation",
        )
        self.assertEqual(status, 201)
        data = payload["data"]
        self.assertEqual(data["compliance"]["status"], "compliant")
        self.assertTrue(data["limitations"])
        self.assertEqual(data["audit"]["provider"], "mock")
        self.assertEqual(data["audit"]["campaign_id"], "campaign-one")
        self.assertEqual(data["audit"]["brief_id"], "brief-one")
        self.assertNotEqual(data["asset_id"], "campaign-one")

    def test_workspace_delegates_api_security_without_bypass(self) -> None:
        encoded = json.dumps(
            {
                "brand_id": "brand-two",
                "campaign_id": "campaign-one",
                "brief_id": "brief-one",
            }
        ).encode()
        captured = {}

        def start_response(status, headers):
            captured["status"] = int(status.split()[0])

        body = b"".join(
            self.workspace(
                {
                    "REQUEST_METHOD": "POST",
                    "PATH_INFO": "/v1/pilot/workflow-review",
                    "CONTENT_LENGTH": str(len(encoded)),
                    "HTTP_AUTHORIZATION": "Bearer valid-token",
                    "HTTP_X_TENANT_ID": "default",
                    "wsgi.input": io.BytesIO(encoded),
                },
                start_response,
            )
        )
        self.assertIn(captured["status"], {403, 409})
        self.assertIn("error", json.loads(body))


if __name__ == "__main__":
    unittest.main()
