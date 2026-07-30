"""Campaign generation and compliance-review orchestration."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from app.campaigns.campaign_engine import CampaignEngine
from app.campaigns.campaign_service import CampaignService
from app.compliance.engine import ComplianceEngine
from app.compliance.models import ComplianceReport, ReviewSubjectType
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

    def generate_review_and_save(
        self,
        *,
        brand: BrandProfile,
        voice: VoiceProfile,
        brief: CampaignBrief,
    ) -> CampaignReviewResult:
        """Generate content, run compliance checks, and persist both."""

        generated = self.campaign_engine.generate_campaign_content(
            brand=brand,
            voice=voice,
            brief=brief,
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
