"""Tests for the campaign compliance-review pipeline."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from uuid import uuid4

from app.ai.prompt import PromptSection
from app.campaigns.campaign_service import CampaignService
from app.campaigns.review_pipeline import CampaignReviewPipeline
from app.compliance.models import (
    ComplianceReport,
    ComplianceStatus,
    ReviewSubjectType,
)
from app.compliance.rule_packs import RulePackLoader
from app.config import Settings
from app.models import (
    BrandProfile,
    CampaignBrief,
    GeneratedContent,
    VoiceProfile,
)


class FakeCampaignEngine:
    """Deterministic campaign engine used by pipeline tests."""

    def __init__(self) -> None:
        self.additional_sections: list[PromptSection] = []

    def generate_campaign_content(
        self,
        *,
        brand: BrandProfile,
        voice: VoiceProfile,
        brief: CampaignBrief,
        additional_sections: tuple[PromptSection, ...] | list[PromptSection] = (),
    ) -> GeneratedContent:
        self.additional_sections = list(additional_sections)
        return GeneratedContent(
            campaign_id=brief.campaign_id,
            platform=brief.platform,
            content_type=brief.content_type,
            content="Generated campaign content.",
            model="fake-model",
        )


class FakeComplianceEngine:
    """Compliance engine replacement that records evaluation inputs."""

    def __init__(self) -> None:
        self.last_evaluation: dict[str, object] | None = None

    def evaluate(
        self,
        *,
        brand_id: str,
        subject_id: str,
        subject_type: ReviewSubjectType,
        content: str,
    ) -> ComplianceReport:
        self.last_evaluation = {
            "brand_id": brand_id,
            "subject_id": subject_id,
            "subject_type": subject_type,
            "content": content,
        }

        return ComplianceReport(
            report_id=str(uuid4()),
            brand_id=brand_id,
            subject_id=subject_id,
            subject_type=subject_type,
            status=ComplianceStatus.COMPLIANT,
            summary="Campaign passed compliance review.",
            ruleset_version="test-rule:v1",
            completed_at="2026-07-30T12:00:00+00:00",
        )


class CampaignReviewPipelineTests(unittest.TestCase):
    def setUp(self) -> None:
        self.brand = BrandProfile(
            brand_id="brand-1",
            name="Example Brand",
            industry="Retail",
            description="An example retailer.",
            target_audience="Local customers",
            products_or_services=["Replacement parts"],
            values=["service"],
        )

        self.voice = VoiceProfile(
            voice_id="voice-1",
            brand_id="brand-1",
            summary="Clear and helpful.",
            tone_traits=["clear", "helpful"],
        )

        self.brief = CampaignBrief(
            campaign_id="campaign-1",
            brand_id="brand-1",
            objective="Generate enquiries",
            audience="Local customers",
            offer="Product availability",
            platform="Facebook",
            content_type="Social post",
            key_message="Contact us for replacement parts",
            call_to_action="Send us a message",
        )

    def create_settings(self, root: Path) -> Settings:
        return Settings(
            project_root=root,
            gemini_api_key="test-key",
            gemini_model="test-model",
            database_folder=root / "database",
            output_folder=root / "outputs",
            assets_folder=root / "assets",
            prompts_folder=root / "prompts",
        )

    def test_pipeline_generates_reviews_and_saves_campaign(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            compliance_engine = FakeComplianceEngine()

            pipeline = CampaignReviewPipeline(
                campaign_engine=FakeCampaignEngine(),
                campaign_service=CampaignService(self.create_settings(root)),
                compliance_engine=compliance_engine,
            )

            result = pipeline.generate_review_and_save(
                brand=self.brand,
                voice=self.voice,
                brief=self.brief,
            )

            self.assertTrue(result.content_path.exists())
            self.assertTrue(result.compliance_report_path.exists())
            self.assertEqual(
                result.compliance_report.status,
                ComplianceStatus.COMPLIANT,
            )

            self.assertEqual(
                compliance_engine.last_evaluation,
                {
                    "brand_id": "brand-1",
                    "subject_id": "campaign-1",
                    "subject_type": ReviewSubjectType.TEXT,
                    "content": "Generated campaign content.",
                },
            )

    def test_saved_report_contains_serialised_compliance_data(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)

            pipeline = CampaignReviewPipeline(
                campaign_engine=FakeCampaignEngine(),
                campaign_service=CampaignService(self.create_settings(root)),
                compliance_engine=FakeComplianceEngine(),
            )

            result = pipeline.generate_review_and_save(
                brand=self.brand,
                voice=self.voice,
                brief=self.brief,
            )

            saved_report = json.loads(
                result.compliance_report_path.read_text(encoding="utf-8")
            )

            self.assertEqual(saved_report["brand_id"], "brand-1")
            self.assertEqual(saved_report["subject_id"], "campaign-1")
            self.assertEqual(saved_report["status"], "compliant")
            self.assertEqual(
                saved_report["ruleset_version"],
                "test-rule:v1",
            )

    def test_campaign_service_saves_report_metadata(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            service = CampaignService(self.create_settings(root))

            report = FakeComplianceEngine().evaluate(
                brand_id="brand-1",
                subject_id="campaign-1",
                subject_type=ReviewSubjectType.TEXT,
                content="Generated campaign content.",
            )

            report_path = service.save_compliance_report(report)

            self.assertTrue(report_path.exists())

            records = service.list_campaign_records()

            self.assertTrue(any("compliance" in record for record in records))

    def test_pipeline_builds_pre_generation_compliance_section(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            campaign_engine = FakeCampaignEngine()

            rule_pack = RulePackLoader().load_dict(
                {
                    "pack_id": "campaign-rules",
                    "name": "Campaign rules",
                    "description": ("Rules for campaign generation."),
                    "version": 1,
                    "rules": [
                        {
                            "rule": {
                                "rule_id": ("required-disclaimer"),
                                "name": ("Required disclaimer"),
                                "description": ("Require approved wording."),
                                "severity": "error",
                                "evaluation_method": ("deterministic"),
                                "subject_types": ["text"],
                                "category": "disclosure",
                            },
                            "evaluator_type": ("required_phrase"),
                            "evaluator_config": {
                                "required_phrase": ("Terms apply."),
                            },
                        },
                    ],
                },
                brand_id=self.brand.brand_id,
            )

            pipeline = CampaignReviewPipeline(
                campaign_engine=campaign_engine,
                campaign_service=CampaignService(self.create_settings(root)),
                compliance_engine=FakeComplianceEngine(),
            )

            pipeline.generate_review_and_save(
                brand=self.brand,
                voice=self.voice,
                brief=self.brief,
                rule_pack=rule_pack,
            )

            self.assertEqual(
                len(campaign_engine.additional_sections),
                1,
            )

            section = campaign_engine.additional_sections[0]

            self.assertEqual(
                section.title,
                "Compliance Requirements",
            )
            self.assertIn(
                "Terms apply.",
                section.content,
            )
            self.assertNotIn(
                "required-disclaimer",
                section.content,
            )

    def test_pipeline_uses_no_additional_sections_without_pack(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            campaign_engine = FakeCampaignEngine()

            pipeline = CampaignReviewPipeline(
                campaign_engine=campaign_engine,
                campaign_service=CampaignService(self.create_settings(root)),
                compliance_engine=FakeComplianceEngine(),
            )

            pipeline.generate_review_and_save(
                brand=self.brand,
                voice=self.voice,
                brief=self.brief,
            )

            self.assertEqual(
                campaign_engine.additional_sections,
                [],
            )

    def test_pipeline_rejects_invalid_rule_pack(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)

            pipeline = CampaignReviewPipeline(
                campaign_engine=FakeCampaignEngine(),
                campaign_service=CampaignService(self.create_settings(root)),
                compliance_engine=FakeComplianceEngine(),
            )

            with self.assertRaisesRegex(
                TypeError,
                "RulePack",
            ):
                pipeline.generate_review_and_save(
                    brand=self.brand,
                    voice=self.voice,
                    brief=self.brief,
                    rule_pack=object(),  # type: ignore[arg-type]
                )


if __name__ == "__main__":
    unittest.main()
