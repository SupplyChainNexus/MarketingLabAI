"""Tests for the canonical MarketingLabAI application composition root."""

from __future__ import annotations

import tempfile
import unittest
from datetime import date
from pathlib import Path

from app.ai.providers.mock import MockIntelligenceProvider
from app.ai.registry import IntelligenceProviderRegistry
from app.application import CanonicalApplication
from app.campaign_planner import (
    CampaignAudience,
    CampaignChannel,
    CampaignMetric,
    CampaignObjective,
    CampaignPlan,
    CampaignStatus,
    CampaignTimeline,
)
from app.compliance.models import (
    ComplianceReport,
    ComplianceStatus,
    ReviewSubjectType,
)
from app.customer_intelligence import (
    CustomerIntelligenceProfile,
    CustomerPersona,
    CustomerSegment,
)
from app.database.connection import SQLiteDatabase
from app.intelligence.models import BusinessIntelligenceProfile
from app.marketing_brief import BriefStatus, MarketingBrief
from app.models import BrandProfile, VoiceProfile
from app.prompts.models import PromptPack


class RecordingArtifactService:
    """Represent the explicit campaign-artifact persistence boundary."""

    def __init__(self, folder: Path) -> None:
        self.folder = folder
        self.generated_content = None
        self.compliance_report = None

    def save_generated_content(self, generated):
        self.generated_content = generated
        return self.folder / "generated.json"

    def save_compliance_report(self, report):
        self.compliance_report = report
        return self.folder / "compliance.json"


class SyntheticComplianceEngine:
    """Return a deterministic compliant report."""

    def evaluate(
        self,
        *,
        brand_id,
        subject_id,
        subject_type,
        content,
    ) -> ComplianceReport:
        return ComplianceReport(
            report_id="report-one",
            brand_id=brand_id,
            subject_id=subject_id,
            subject_type=ReviewSubjectType.TEXT,
            status=ComplianceStatus.COMPLIANT,
            summary="Synthetic pilot content passed.",
            completed_at="2026-08-05T12:00:00+00:00",
        )


class CanonicalApplicationTests(unittest.TestCase):
    """Verify canonical dependency composition and the pilot workflow."""

    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.folder = Path(self.temporary_directory.name)
        self.application = CanonicalApplication.build(
            database=SQLiteDatabase(self.folder / "marketinglabai.db"),
        )
        self.application.brands.save(
            {
                "brand_id": "brand-one",
                "tenant_id": "default",
                "name": "Brand One",
            }
        )

    def tearDown(self) -> None:
        self.temporary_directory.cleanup()

    def test_repositories_share_one_sqlite_database(self) -> None:
        repositories = (
            self.application.tenants,
            self.application.brands,
            self.application.business_intelligence,
            self.application.customer_intelligence,
            self.application.memory,
            self.application.campaign_plans,
            self.application.marketing_briefs,
            self.application.prompt_packs,
            self.application.compliance_rules,
        )

        for repository in repositories:
            self.assertIs(repository.database, self.application.database)

    def test_context_assembler_composes_company_and_customer_context(self) -> None:
        self.application.business_intelligence.save(
            BusinessIntelligenceProfile(
                brand_id="brand-one",
                revenue_model="Retail sales",
            )
        )
        self.application.customer_intelligence.save(
            CustomerIntelligenceProfile(
                brand_id="brand-one",
                summary="Workshops value dependable availability.",
                primary_segment_id="workshops",
                segments=[
                    CustomerSegment(
                        segment_id="workshops",
                        name="Independent Workshops",
                    )
                ],
                personas=[
                    CustomerPersona(
                        persona_id="owner",
                        name="Workshop Owner",
                        segment_id="workshops",
                        pain_points=["Vehicle downtime"],
                    )
                ],
            )
        )

        context = self.application.build_context_assembler().build(brand_id="brand-one")

        self.assertIn("- Revenue model: Retail sales", context.company_context)
        self.assertIn(
            "- Summary: Workshops value dependable availability.",
            context.customer_context,
        )
        self.assertIn("- Pain points: Vehicle downtime", context.customer_context)

    def test_approved_plan_runs_through_governed_generation(self) -> None:
        plan = CampaignPlan(
            campaign_id="campaign-one",
            tenant_id="default",
            brand_id="brand-one",
            name="Workshop Acquisition",
            objective=CampaignObjective(
                "Increase qualified enquiries",
                "Grow workshop revenue.",
            ),
            audience=CampaignAudience(
                "Independent workshops",
                "Repair businesses in the Western Cape.",
            ),
            timeline=CampaignTimeline(
                date(2026, 9, 1),
                date(2026, 9, 30),
            ),
            channels=(CampaignChannel("facebook"),),
            success_metrics=(
                CampaignMetric("Qualified enquiries", "25", "CRM source"),
            ),
            owner="Campaign Manager",
            status=CampaignStatus.APPROVED,
        )
        brief = MarketingBrief(
            brief_id="brief-one",
            tenant_id="default",
            brand_id="brand-one",
            name="Workshop Acquisition Brief",
            objective="Increase qualified enquiries",
            audience="Independent workshops",
            offer="Priority parts sourcing",
            key_message="Dependable access to parts",
            call_to_action="Request a quote",
            channels=["facebook"],
            deliverables=["Lead advert"],
            constraints=["No unsupported guarantees"],
            success_metrics=["Qualified enquiries"],
            status=BriefStatus.APPROVED,
        )
        self.application.campaign_plans.save(plan)
        self.application.marketing_briefs.save(brief)
        self.application.prompt_packs.save(
            PromptPack(
                prompt_pack_id="campaign-pack",
                tenant_id="default",
                brand_id="brand-one",
                name="Campaign Prompt",
                task_type="campaign_content",
                channel="facebook",
                template="Objective: {objective}\nAudience: {audience}",
                variables=["objective", "audience"],
                system_instruction="Use verified Marketing Brief facts.",
            )
        )

        artifacts = RecordingArtifactService(self.folder)
        provider = MockIntelligenceProvider(
            response_content="Verified workshop campaign content.",
        )
        registry = IntelligenceProviderRegistry()
        registry.register(provider)
        engine = self.application.build_campaign_engine(
            registry,
            tenant_id="default",
        )
        workflow = self.application.build_campaign_workflow(
            campaign_engine=engine,
            campaign_artifact_service=artifacts,
            compliance_engine=SyntheticComplianceEngine(),
        )
        result = workflow.generate_review_and_save(
            brand=BrandProfile(
                brand_id="brand-one",
                name="Brand One",
                industry="Automotive",
                description="Parts supplier.",
                target_audience="Repair workshops",
                products_or_services=["Replacement parts"],
                values=["service"],
            ),
            voice=VoiceProfile(
                voice_id="voice-one",
                brand_id="brand-one",
                summary="Clear and helpful.",
                tone_traits=["clear"],
            ),
            brief=self.application.marketing_briefs.get(
                "brief-one",
                tenant_id="default",
            ),
            campaign_plan=self.application.campaign_plans.get(
                "campaign-one",
                tenant_id="default",
            ),
            content_type="social post",
        )

        self.assertEqual(
            result.campaign_plan_audit.campaign_id,
            "campaign-one",
        )
        self.assertEqual(
            result.campaign_review.compliance_report.status,
            ComplianceStatus.COMPLIANT,
        )
        self.assertIsNotNone(artifacts.generated_content)
        self.assertIsNotNone(artifacts.compliance_report)
        self.assertEqual(len(provider.requests), 1)
        self.assertIn(
            "Selected Prompt Pack:",
            provider.requests[0].prompt,
        )


if __name__ == "__main__":
    unittest.main()
