"""Client-facing Strategy workspace and Design Partner readiness tests."""

import unittest
from pathlib import Path

from app.design_partner import DesignPartnerReadinessEvaluator
from tests import test_pilot_api


class StrategyWorkspaceReadinessTests(unittest.TestCase):
    def setUp(self) -> None:
        self.fixture = test_pilot_api.PilotApiTests()
        self.fixture.setUp()

    def tearDown(self) -> None:
        self.fixture.tearDown()

    def test_workflow_review_exposes_transport_safe_strategy(self) -> None:
        status, payload = self.fixture.request(
            "/v1/pilot/workflow-review",
            {
                "brand_id": "brand-one",
                "campaign_id": "campaign-one",
                "brief_id": "brief-one",
            },
        )
        self.assertEqual(status, 200)
        strategy = payload["data"]["strategy"]
        self.assertTrue(strategy["ready"])
        self.assertEqual(strategy["strategy_id"], "strategy-one")
        self.assertNotIn("tenant_id", strategy)
        self.assertNotIn("evidence", strategy)
        self.assertTrue(payload["data"]["generation_ready"])

    def test_readiness_never_activates_real_data(self) -> None:
        evidence = {
            name: True for name in DesignPartnerReadinessEvaluator.REQUIRED_GATES
        }
        status, payload = self.fixture.request(
            "/v1/pilot/design-partner/readiness",
            {"partner_name": "Strand Auto Parts", "evidence": evidence},
        )
        self.assertEqual(status, 200)
        data = payload["data"]
        self.assertTrue(data["ready_for_activation_decision"])
        self.assertFalse(data["real_data_activation_authorized"])
        self.assertTrue(data["synthetic_rehearsal_authorized"])
        self.assertEqual(data["pilot_status"], "real_data_activation_frozen")
        self.assertFalse(data["account_entitlement"]["billing_enabled"])
        self.assertTrue(data["account_entitlement"]["full_feature_access"])
        self.assertFalse(data["market_validation_claimed"])

    def test_missing_readiness_evidence_remains_a_blocker(self) -> None:
        report = DesignPartnerReadinessEvaluator().evaluate(
            partner_name="Strand Auto Parts", evidence={}
        )
        self.assertEqual(
            report["blockers"],
            list(DesignPartnerReadinessEvaluator.REQUIRED_GATES),
        )
        self.assertFalse(report["ready_for_activation_decision"])

    def test_unapproved_partner_cannot_claim_founder_entitlement(self) -> None:
        with self.assertRaisesRegex(ValueError, "candidate is not approved"):
            DesignPartnerReadinessEvaluator().evaluate(
                partner_name="Another Business", evidence={}
            )

    def test_workspace_contains_strategy_and_readiness_surface(self) -> None:
        html = Path("app/pilot_workspace/assets/index.html").read_text(encoding="utf-8")
        script = Path("app/pilot_workspace/assets/workspace.js").read_text(
            encoding="utf-8"
        )
        self.assertIn("Strategy review", html)
        self.assertIn("Founder Design Partner readiness", html)
        self.assertIn("Strand Auto Parts", html)
        self.assertIn("design-partner/readiness", script)
        self.assertIn("real customer data automatically", html)


if __name__ == "__main__":
    unittest.main()
