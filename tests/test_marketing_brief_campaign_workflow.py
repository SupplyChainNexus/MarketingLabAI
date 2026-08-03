"""Tests for approved Marketing Brief campaign workflow."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from app.ai.prompt import PromptSection
from app.campaigns.review_pipeline import (
    CampaignReviewPipeline,
)
from app.compliance.models import (
    ComplianceReport,
    ComplianceStatus,
    ReviewSubjectType,
)
from app.database.connection import SQLiteDatabase
from app.database.repositories import BrandRepository
from app.marketing_brief import (
    BriefStatus,
    MarketingBrief,
    MarketingBriefCampaignResult,
    MarketingBriefCampaignWorkflow,
    MarketingBriefPromptPackService,
)
from app.models import (
    BrandProfile,
    GeneratedContent,
    VoiceProfile,
)
from app.prompts.models import PromptPack
from app.prompts.repository import PromptPackRepository
from app.prompts.selector import PromptPackSelector


class RecordingCampaignEngine:
    """Record campaign inputs and return deterministic content."""

    def __init__(self) -> None:
        self.additional_sections: tuple[PromptSection, ...] = ()
        self.brief = None

    def generate_campaign_content(
        self,
        brand,
        voice,
        brief,
        *,
        additional_sections=(),
    ) -> GeneratedContent:
        self.brief = brief
        self.additional_sections = tuple(additional_sections)

        return GeneratedContent(
            campaign_id=brief.campaign_id,
            platform=brief.platform,
            content_type=brief.content_type,
            content="Generated campaign content.",
            model="test-model",
        )


class RecordingCampaignService:
    """Record persisted campaign and compliance artifacts."""

    def __init__(self, folder: Path) -> None:
        self.folder = folder
        self.generated_content = None
        self.compliance_report = None

    def save_generated_content(self, generated):
        self.generated_content = generated
        return self.folder / "campaign.json"

    def save_compliance_report(self, report):
        self.compliance_report = report
        return self.folder / "compliance.json"


class RecordingComplianceEngine:
    """Record evaluated campaign content."""

    def __init__(self) -> None:
        self.arguments = None

    def evaluate(
        self,
        *,
        brand_id,
        subject_id,
        subject_type,
        content,
    ) -> ComplianceReport:
        self.arguments = {
            "brand_id": brand_id,
            "subject_id": subject_id,
            "subject_type": subject_type,
            "content": content,
        }

        return ComplianceReport(
            report_id="report-one",
            brand_id=brand_id,
            subject_id=subject_id,
            subject_type=subject_type,
            status=ComplianceStatus.COMPLIANT,
            summary="Campaign passed compliance review.",
            completed_at="2026-08-03T12:00:00+00:00",
        )


class MarketingBriefCampaignWorkflowTests(unittest.TestCase):
    """Validate approved-brief campaign orchestration."""

    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.folder = Path(self.temporary_directory.name)

        self.database = SQLiteDatabase(self.folder / "marketinglabai.db")
        self.database.initialise()

        self.brands = BrandRepository(self.database)
        self.brands.save(
            {
                "brand_id": "brand-one",
                "tenant_id": "default",
                "name": "Brand One",
            }
        )

        self.prompt_repository = PromptPackRepository(self.database)
        self.prompt_repository.save(
            PromptPack(
                prompt_pack_id="campaign-pack",
                tenant_id="default",
                brand_id="brand-one",
                name="Campaign Prompt",
                task_type="campaign_content",
                channel="facebook",
                template=("Objective: {objective}\n" "Audience: {audience}"),
                variables=["objective", "audience"],
                system_instruction=("Use only verified Marketing Brief facts."),
            )
        )

        self.campaign_engine = RecordingCampaignEngine()
        self.campaign_service = RecordingCampaignService(self.folder)
        self.compliance_engine = RecordingComplianceEngine()

        self.review_pipeline = CampaignReviewPipeline(
            campaign_engine=self.campaign_engine,
            campaign_service=self.campaign_service,
            compliance_engine=self.compliance_engine,
        )

        prompt_pack_service = MarketingBriefPromptPackService(
            PromptPackSelector(self.prompt_repository)
        )

        self.workflow = MarketingBriefCampaignWorkflow(
            review_pipeline=self.review_pipeline,
            prompt_pack_service=prompt_pack_service,
        )

        self.brand = BrandProfile(
            brand_id="brand-one",
            name="Brand One",
            industry="Automotive",
            description="Parts supplier.",
            target_audience="Repair workshops",
            products_or_services=["Replacement parts"],
            values=["service"],
        )
        self.voice = VoiceProfile(
            voice_id="voice-one",
            brand_id="brand-one",
            summary="Clear and helpful.",
            tone_traits=["clear"],
        )

    def tearDown(self) -> None:
        self.temporary_directory.cleanup()

    @staticmethod
    def make_brief(
        **overrides: object,
    ) -> MarketingBrief:
        values: dict[str, object] = {
            "brief_id": "brief-one",
            "tenant_id": "default",
            "brand_id": "brand-one",
            "name": "Workshop Acquisition",
            "objective": "Increase qualified enquiries",
            "audience": "Independent repair workshops",
            "offer": "Priority parts sourcing",
            "key_message": "Dependable access to parts",
            "call_to_action": "Request a quote",
            "channels": ["facebook"],
            "deliverables": ["Lead advert"],
            "constraints": ["No unsupported guarantees"],
            "success_metrics": ["Qualified enquiries"],
            "notes": "Use direct language.",
            "status": BriefStatus.APPROVED,
        }
        values.update(overrides)

        return MarketingBrief(**values)

    def test_workflow_rejects_non_approved_brief(self) -> None:
        brief = self.make_brief(status=BriefStatus.DRAFT)

        with self.assertRaisesRegex(
            ValueError,
            "approved",
        ):
            self.workflow.generate_review_and_save(
                brand=self.brand,
                voice=self.voice,
                brief=brief,
                content_type="social post",
            )

    def test_workflow_rejects_mismatched_brand(self) -> None:
        brief = self.make_brief(brand_id="other-brand")

        with self.assertRaisesRegex(
            ValueError,
            "does not belong",
        ):
            self.workflow.generate_review_and_save(
                brand=self.brand,
                voice=self.voice,
                brief=brief,
                content_type="social post",
            )

    def test_workflow_uses_first_brief_channel_by_default(
        self,
    ) -> None:
        result = self.workflow.generate_review_and_save(
            brand=self.brand,
            voice=self.voice,
            brief=self.make_brief(),
            content_type="social post",
        )

        self.assertEqual(
            result.campaign_review.generated_content.platform,
            "facebook",
        )

    def test_workflow_rejects_channel_outside_brief(
        self,
    ) -> None:
        with self.assertRaisesRegex(
            ValueError,
            "not included",
        ):
            self.workflow.generate_review_and_save(
                brand=self.brand,
                voice=self.voice,
                brief=self.make_brief(),
                content_type="social post",
                channel="email",
            )

    def test_workflow_injects_selected_prompt_pack_sections(
        self,
    ) -> None:
        result = self.workflow.generate_review_and_save(
            brand=self.brand,
            voice=self.voice,
            brief=self.make_brief(),
            content_type="social post",
        )

        section_map = {
            section.title: section.render()
            for section in self.campaign_engine.additional_sections
        }

        self.assertIn(
            "Selected Prompt Pack",
            section_map,
        )
        self.assertIn(
            "Objective: Increase qualified enquiries",
            section_map["Selected Prompt Pack"],
        )
        self.assertIn(
            "Prompt Pack System Requirements",
            section_map,
        )
        self.assertIsInstance(
            result,
            MarketingBriefCampaignResult,
        )

    def test_workflow_preserves_prompt_and_brief_audit_data(
        self,
    ) -> None:
        result = self.workflow.generate_review_and_save(
            brand=self.brand,
            voice=self.voice,
            brief=self.make_brief(version=2),
            content_type="social post",
        )

        self.assertEqual(
            result.rendered_prompt.brief_id,
            "brief-one",
        )
        self.assertEqual(
            result.rendered_prompt.brief_version,
            2,
        )
        self.assertEqual(
            result.rendered_prompt.prompt.prompt_pack_id,
            "campaign-pack",
        )

    def test_workflow_runs_post_generation_compliance(
        self,
    ) -> None:
        result = self.workflow.generate_review_and_save(
            brand=self.brand,
            voice=self.voice,
            brief=self.make_brief(),
            content_type="social post",
        )

        self.assertEqual(
            self.compliance_engine.arguments,
            {
                "brand_id": "brand-one",
                "subject_id": "brief-one",
                "subject_type": ReviewSubjectType.TEXT,
                "content": "Generated campaign content.",
            },
        )
        self.assertEqual(
            result.campaign_review.compliance_report.status,
            ComplianceStatus.COMPLIANT,
        )

    def test_workflow_maps_brief_to_legacy_campaign_brief(
        self,
    ) -> None:
        self.workflow.generate_review_and_save(
            brand=self.brand,
            voice=self.voice,
            brief=self.make_brief(),
            content_type="social post",
        )

        campaign_brief = self.campaign_engine.brief

        self.assertEqual(
            campaign_brief.campaign_id,
            "brief-one",
        )
        self.assertEqual(
            campaign_brief.objective,
            "Increase qualified enquiries",
        )
        self.assertIn(
            "No unsupported guarantees",
            campaign_brief.additional_context,
        )
        self.assertIn(
            "Qualified enquiries",
            campaign_brief.additional_context,
        )

    def test_existing_pipeline_callers_need_no_new_argument(
        self,
    ) -> None:
        legacy_brief = self.campaign_engine.brief

        if legacy_brief is None:
            self.workflow.generate_review_and_save(
                brand=self.brand,
                voice=self.voice,
                brief=self.make_brief(),
                content_type="social post",
            )
            legacy_brief = self.campaign_engine.brief

        self.campaign_engine.additional_sections = (
            PromptSection(
                title="Stale",
                content="Stale",
            ),
        )

        self.review_pipeline.generate_review_and_save(
            brand=self.brand,
            voice=self.voice,
            brief=legacy_brief,
        )

        self.assertEqual(
            self.campaign_engine.additional_sections,
            (),
        )

    def test_pipeline_rejects_invalid_additional_section(
        self,
    ) -> None:
        self.workflow.generate_review_and_save(
            brand=self.brand,
            voice=self.voice,
            brief=self.make_brief(),
            content_type="social post",
        )
        legacy_brief = self.campaign_engine.brief

        with self.assertRaisesRegex(
            TypeError,
            "PromptSection",
        ):
            self.review_pipeline.generate_review_and_save(
                brand=self.brand,
                voice=self.voice,
                brief=legacy_brief,
                additional_sections=[object()],  # type: ignore[list-item]
            )


if __name__ == "__main__":
    unittest.main()
