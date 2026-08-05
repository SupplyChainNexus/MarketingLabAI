"""Governed Positioning Intelligence workflow integration tests."""

from __future__ import annotations

import tempfile
import unittest
from datetime import date
from pathlib import Path

from app.ai.providers.mock import MockIntelligenceProvider
from app.ai.registry import IntelligenceProviderRegistry
from app.application import CanonicalApplication, LifecycleConflictError
from app.campaign_planner import (
    CampaignAudience,
    CampaignChannel,
    CampaignMetric,
    CampaignObjective,
    CampaignPlan,
    CampaignStatus,
    CampaignTimeline,
)
from app.database.connection import SQLiteDatabase
from app.identity import AuthenticatedPrincipal, TenantMembership, TenantRole
from app.marketing_brief import BriefStatus, MarketingBrief
from app.positioning_intelligence import (
    PositioningDecision,
    PositioningEvidence,
    PositioningStatus,
    TargetKind,
)
from app.strategy_intelligence import (
    StrategyDecision,
    StrategyEvidence,
    StrategyStatus,
)


class PositioningWorkflowIntegrationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.folder = tempfile.TemporaryDirectory()
        self.application = CanonicalApplication.build(
            SQLiteDatabase(Path(self.folder.name) / "db.sqlite")
        )
        self.application.brands.save(
            {"brand_id": "brand-one", "tenant_id": "default", "name": "One"}
        )
        principal = AuthenticatedPrincipal("subject-one", "synthetic-idp")
        self.application.identities.save_membership(
            TenantMembership(
                "subject-one", "synthetic-idp", "default", TenantRole.ADMIN
            )
        )
        self.session = self.application.authorize(principal, tenant_id="default")
        self.registry = IntelligenceProviderRegistry()
        self.provider = MockIntelligenceProvider("Synthetic result")
        self.registry.register(self.provider)
        self._save_positioning()
        self.application.strategy_intelligence.save(
            StrategyDecision(
                strategy_id="strategy-one",
                version=1,
                tenant_id="default",
                brand_id="brand-one",
                positioning_id="positioning-one",
                positioning_version=1,
                status=StrategyStatus.APPROVED,
                business_objectives=["Validate synthetic demand"],
                evidence=[
                    StrategyEvidence("Synthetic", "Reviewed objective", 0.9, True)
                ],
                approved_at="2026-08-06T00:00:00+00:00",
            )
        )

    def tearDown(self) -> None:
        self.folder.cleanup()

    def _save_positioning(
        self,
        *,
        positioning_id: str = "positioning-one",
        version: int = 1,
        status: PositioningStatus = PositioningStatus.APPROVED,
    ) -> None:
        self.application.positioning_intelligence.save(
            PositioningDecision(
                positioning_id=positioning_id,
                version=version,
                tenant_id="default",
                brand_id="brand-one",
                target_kind=TargetKind.SEGMENT,
                target_id="segment-one",
                product_id="product-one",
                value_proposition="A verified synthetic value proposition.",
                evidence=[PositioningEvidence("Synthetic", "Reviewed", 0.9, True)],
                status=status,
                approved_at=(
                    "2026-08-06T00:00:00+00:00" if status.value == "approved" else ""
                ),
            )
        )

    def _save_execution(
        self,
        positioning_id="positioning-one",
        version=1,
        strategy_id="strategy-one",
        strategy_version=1,
        brief_strategy_id=None,
        brief_strategy_version=None,
    ) -> None:
        self.application.campaign_plans.save(
            CampaignPlan(
                campaign_id="campaign-one",
                tenant_id="default",
                brand_id="brand-one",
                name="Campaign",
                objective=CampaignObjective("Validate"),
                audience=CampaignAudience("Audience", "Synthetic"),
                timeline=CampaignTimeline(date(2026, 8, 1), date(2026, 8, 2)),
                channels=(CampaignChannel("Email"),),
                success_metrics=(CampaignMetric("Reviews", "1"),),
                owner="Owner",
                status=CampaignStatus.APPROVED,
                positioning_id=positioning_id,
                positioning_version=version,
                strategy_id=strategy_id,
                strategy_version=strategy_version,
            )
        )
        self.application.marketing_briefs.save(
            MarketingBrief(
                brief_id="brief-one",
                tenant_id="default",
                brand_id="brand-one",
                name="Brief",
                objective="Validate",
                audience="Synthetic",
                key_message="Message",
                call_to_action="Review",
                channels=["Email"],
                deliverables=["Draft"],
                status=BriefStatus.APPROVED,
                positioning_id=positioning_id,
                positioning_version=version,
                strategy_id=(
                    strategy_id if brief_strategy_id is None else brief_strategy_id
                ),
                strategy_version=(
                    strategy_version
                    if brief_strategy_version is None
                    else brief_strategy_version
                ),
            )
        )

    def _generate(self):
        return self.session.generate_approved(
            self.registry,
            brand_id="brand-one",
            campaign_id="campaign-one",
            campaign_version=1,
            brief_id="brief-one",
            brief_version=1,
            task="Create synthetic content",
        )

    def test_canonical_composition_shares_positioning_repository(self) -> None:
        self.assertIs(
            self.application.positioning_intelligence.database,
            self.application.database,
        )

    def test_approved_positioning_is_rendered_for_generation(self) -> None:
        self._save_execution()
        response = self._generate()
        self.assertEqual(response.content, "Synthetic result")
        request = self.provider.requests[0]
        self.assertIn("Approved Positioning Context", request.prompt)
        self.assertIn("A verified synthetic value proposition.", request.prompt)
        self.assertIn("Approved Marketing Strategy Context", request.prompt)
        self.assertIn("Strategy reference: strategy-one v1", request.prompt)
        self.assertEqual(request.metadata["approved_positioning_id"], "positioning-one")
        self.assertEqual(request.metadata["approved_strategy_id"], "strategy-one")
        self.assertEqual(request.metadata["approved_strategy_version"], 1)

    def test_missing_strategy_reference_blocks_generation(self) -> None:
        self._save_execution(strategy_id="", strategy_version=0)
        with self.assertRaisesRegex(LifecycleConflictError, "same approved strategy"):
            self._generate()
        self.assertEqual(self.provider.requests, [])

    def test_mismatched_plan_and_brief_strategy_blocks_generation(self) -> None:
        self._save_execution(brief_strategy_id="strategy-two", brief_strategy_version=1)
        with self.assertRaisesRegex(LifecycleConflictError, "same approved strategy"):
            self._generate()
        self.assertEqual(self.provider.requests, [])

    def test_stale_strategy_reference_blocks_generation(self) -> None:
        self._save_execution()
        self.application.strategy_intelligence.save(
            StrategyDecision(
                strategy_id="strategy-one",
                version=2,
                tenant_id="default",
                brand_id="brand-one",
                positioning_id="positioning-one",
                positioning_version=1,
                status=StrategyStatus.APPROVED,
                business_objectives=["Revised synthetic objective"],
                evidence=[StrategyEvidence("Synthetic", "Reviewed", 0.9, True)],
                approved_at="2026-08-07T00:00:00+00:00",
            )
        )
        with self.assertRaisesRegex(LifecycleConflictError, "current approved version"):
            self._generate()
        self.assertEqual(self.provider.requests, [])

    def test_draft_strategy_context_is_rejected(self) -> None:
        self.application.strategy_intelligence.save(
            StrategyDecision(
                strategy_id="draft-strategy",
                version=1,
                tenant_id="default",
                brand_id="brand-one",
                positioning_id="positioning-one",
                positioning_version=1,
                status=StrategyStatus.DRAFT,
            )
        )
        with self.assertRaisesRegex(ValueError, "currently approved"):
            self.application.build_context_assembler().build(
                tenant_id="default",
                brand_id="brand-one",
                strategy_id="draft-strategy",
                strategy_version=1,
            )

    def test_cross_brand_strategy_context_is_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "requested brand differ"):
            self.application.build_context_assembler().build(
                tenant_id="default",
                brand_id="brand-two",
                strategy_id="strategy-one",
                strategy_version=1,
            )

    def test_strategy_positioning_mismatch_blocks_generation(self) -> None:
        self._save_positioning(positioning_id="positioning-two")
        self.application.strategy_intelligence.save(
            StrategyDecision(
                strategy_id="strategy-two",
                version=1,
                tenant_id="default",
                brand_id="brand-one",
                positioning_id="positioning-two",
                positioning_version=1,
                status=StrategyStatus.APPROVED,
                business_objectives=["Synthetic alternative objective"],
                evidence=[StrategyEvidence("Synthetic", "Reviewed", 0.9, True)],
                approved_at="2026-08-06T00:00:00+00:00",
            )
        )
        self._save_execution(strategy_id="strategy-two", strategy_version=1)
        with self.assertRaisesRegex(LifecycleConflictError, "do not match"):
            self._generate()
        self.assertEqual(self.provider.requests, [])

    def test_missing_positioning_reference_blocks_generation(self) -> None:
        self._save_execution("", 0)
        with self.assertRaisesRegex(LifecycleConflictError, "same approved"):
            self._generate()
        self.assertEqual(self.provider.requests, [])

    def test_mismatched_plan_and_brief_references_block_generation(self) -> None:
        self._save_execution()
        brief = self.application.marketing_briefs.get(
            "brief-one", tenant_id="default", version=1
        )
        brief.brief_id = "brief-two"
        brief.positioning_id = "positioning-two"
        self.application.marketing_briefs.save(brief)
        with self.assertRaisesRegex(LifecycleConflictError, "same approved"):
            self.session.generate_approved(
                self.registry,
                brand_id="brand-one",
                campaign_id="campaign-one",
                campaign_version=1,
                brief_id="brief-two",
                brief_version=1,
                task="Create synthetic content",
            )

    def test_stale_positioning_reference_blocks_generation(self) -> None:
        self._save_execution()
        self._save_positioning(version=2)
        with self.assertRaisesRegex(LifecycleConflictError, "current approved"):
            self._generate()

    def test_draft_positioning_context_is_rejected(self) -> None:
        self._save_positioning(
            positioning_id="draft-one", status=PositioningStatus.DRAFT
        )
        with self.assertRaisesRegex(ValueError, "currently approved"):
            self.application.build_context_assembler().build(
                tenant_id="default",
                brand_id="brand-one",
                positioning_id="draft-one",
                positioning_version=1,
            )

    def test_plan_and_brief_references_round_trip(self) -> None:
        self._save_execution()
        plan = self.application.campaign_plans.get("campaign-one", tenant_id="default")
        brief = self.application.marketing_briefs.get("brief-one", tenant_id="default")
        self.assertEqual(
            (plan.positioning_id, plan.positioning_version), ("positioning-one", 1)
        )
        self.assertEqual(
            (brief.positioning_id, brief.positioning_version), ("positioning-one", 1)
        )
        self.assertEqual((plan.strategy_id, plan.strategy_version), ("strategy-one", 1))
        self.assertEqual(
            (brief.strategy_id, brief.strategy_version), ("strategy-one", 1)
        )


if __name__ == "__main__":
    unittest.main()
