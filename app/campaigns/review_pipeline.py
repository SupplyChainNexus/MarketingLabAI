"""Campaign generation and compliance-review orchestration."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from app.campaigns.campaign_engine import CampaignEngine
from app.campaigns.campaign_service import CampaignService
from app.compliance.engine import ComplianceEngine
from app.compliance.models import ComplianceReport, ReviewSubjectType
from app.compliance.prompt_builder import CompliancePromptBuilder
from app.compliance.rule_packs import RulePack
from app.compliance.translator import ComplianceRequirementTranslator
from app.models import (
    BrandProfile,
    CampaignBrief,
    GeneratedContent,
    VoiceProfile,
)


@dataclass(slots=True)
class CampaignReviewResult:
    """Result of generating, reviewing, and saving a campaign."""

    generated_content: GeneratedContent
    compliance_report: ComplianceReport
    content_path: Path
    compliance_report_path: Path


class CampaignReviewPipeline:
    """Generate campaign content and immediately review compliance."""

    def __init__(
        self,
        *,
        campaign_engine: CampaignEngine,
        campaign_service: CampaignService,
        compliance_engine: ComplianceEngine,
    ) -> None:
        self.campaign_engine = campaign_engine
        self.campaign_service = campaign_service
        self.compliance_engine = compliance_engine
        self.requirement_translator = ComplianceRequirementTranslator()
        self.prompt_builder = CompliancePromptBuilder()

    def generate_review_and_save(
        self,
        *,
        brand: BrandProfile,
        voice: VoiceProfile,
        brief: CampaignBrief,
        rule_pack: RulePack | None = None,
    ) -> CampaignReviewResult:
        """Generate content, run compliance checks, and persist both."""

        additional_sections = []

        if rule_pack is not None:
            if not isinstance(rule_pack, RulePack):
                raise TypeError("rule_pack must be a RulePack or None.")

            requirements = self.requirement_translator.translate_many(rule_pack.rules)
            additional_sections = self.prompt_builder.build_sections(requirements)

        generated = self.campaign_engine.generate_campaign_content(
            brand=brand,
            voice=voice,
            brief=brief,
            additional_sections=additional_sections,
        )

        report = self.compliance_engine.evaluate(
            brand_id=brand.brand_id,
            subject_id=generated.campaign_id,
            subject_type=ReviewSubjectType.TEXT,
            content=generated.content,
        )

        content_path = self.campaign_service.save_generated_content(generated)
        compliance_report_path = self.campaign_service.save_compliance_report(report)

        return CampaignReviewResult(
            generated_content=generated,
            compliance_report=report,
            content_path=content_path,
            compliance_report_path=compliance_report_path,
        )
