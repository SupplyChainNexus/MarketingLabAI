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

    def _save_execution(self, positioning_id="positioning-one", version=1) -> None:
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
        self.assertEqual(request.metadata["approved_positioning_id"], "positioning-one")

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


if __name__ == "__main__":
    unittest.main()
