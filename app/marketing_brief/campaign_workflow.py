"""Run approved Marketing Briefs through campaign review."""

from __future__ import annotations

from dataclasses import dataclass

from app.ai.prompt import PromptSection
from app.campaign_planner import (
    CampaignBriefReference,
    CampaignPlan,
    CampaignPlanAuditMetadata,
    CampaignStatus,
)
from app.campaigns.review_pipeline import (
    CampaignReviewPipeline,
    CampaignReviewResult,
)
from app.compliance.rule_packs import RulePack
from app.marketing_brief.models import (
    BriefStatus,
    MarketingBrief,
)
from app.marketing_brief.prompt_pack import (
    MarketingBriefPromptPackService,
    RenderedMarketingBriefPrompt,
)
from app.models import (
    BrandProfile,
    CampaignBrief,
    VoiceProfile,
)


@dataclass(slots=True, frozen=True)
class MarketingBriefCampaignResult:
    """Campaign result with Marketing Brief and Prompt Pack audit data."""

    campaign_review: CampaignReviewResult
    rendered_prompt: RenderedMarketingBriefPrompt
    campaign_plan_audit: CampaignPlanAuditMetadata | None = None

    def __post_init__(self) -> None:
        """Validate the workflow result."""

        if not isinstance(
            self.campaign_review,
            CampaignReviewResult,
        ):
            raise TypeError("campaign_review must be a " "CampaignReviewResult.")

        if not isinstance(
            self.rendered_prompt,
            RenderedMarketingBriefPrompt,
        ):
            raise TypeError(
                "rendered_prompt must be a " "RenderedMarketingBriefPrompt."
            )
        if self.campaign_plan_audit is not None and not isinstance(
            self.campaign_plan_audit,
            CampaignPlanAuditMetadata,
        ):
            raise TypeError(
                "campaign_plan_audit must be CampaignPlanAuditMetadata or None."
            )


class MarketingBriefCampaignWorkflow:
    """Generate, review, and save a campaign from an approved brief."""

    def __init__(
        self,
        *,
        review_pipeline: CampaignReviewPipeline,
        prompt_pack_service: MarketingBriefPromptPackService,
    ) -> None:
        """Create the Marketing Brief campaign workflow."""

        if not isinstance(
            review_pipeline,
            CampaignReviewPipeline,
        ):
            raise TypeError("review_pipeline must be a " "CampaignReviewPipeline.")

        if not isinstance(
            prompt_pack_service,
            MarketingBriefPromptPackService,
        ):
            raise TypeError(
                "prompt_pack_service must be a " "MarketingBriefPromptPackService."
            )

        self.review_pipeline = review_pipeline
        self.prompt_pack_service = prompt_pack_service

    def generate_review_and_save(
        self,
        *,
        brand: BrandProfile,
        voice: VoiceProfile,
        brief: MarketingBrief,
        content_type: str,
        channel: str = "",
        task_type: str = "campaign_content",
        prompt_pack_id: str | None = None,
        rule_pack: RulePack | None = None,
        campaign_plan: CampaignPlan | None = None,
    ) -> MarketingBriefCampaignResult:
        """Run an approved Marketing Brief through the campaign workflow."""

        if not isinstance(brand, BrandProfile):
            raise TypeError("brand must be a BrandProfile.")

        if not isinstance(voice, VoiceProfile):
            raise TypeError("voice must be a VoiceProfile.")

        if not isinstance(brief, MarketingBrief):
            raise TypeError("brief must be a MarketingBrief.")

        if brief.status is not BriefStatus.APPROVED:
            raise ValueError(
                "Only approved Marketing Briefs may generate " "campaign content."
            )

        if brand.brand_id != brief.brand_id:
            raise ValueError("The Marketing Brief does not belong to this brand.")

        effective_channel = self._resolve_channel(
            brief,
            channel,
        )
        campaign_plan_audit = self._campaign_plan_audit(
            campaign_plan,
            brief,
            effective_channel,
        )
        cleaned_content_type = self._required_text(
            "content_type",
            content_type,
        )
        cleaned_task_type = self._required_text(
            "task_type",
            task_type,
        )

        rendered_prompt = self.prompt_pack_service.render(
            brief,
            task_type=cleaned_task_type,
            channel=effective_channel,
            prompt_pack_id=prompt_pack_id,
        )

        campaign_brief = CampaignBrief(
            campaign_id=(
                campaign_plan.campaign_id
                if campaign_plan is not None
                else brief.brief_id
            ),
            brand_id=brief.brand_id,
            objective=brief.objective,
            audience=brief.audience,
            offer=brief.offer,
            platform=effective_channel,
            content_type=cleaned_content_type,
            key_message=brief.key_message,
            call_to_action=brief.call_to_action,
            additional_context=self._additional_context(brief),
        )

        campaign_review = self.review_pipeline.generate_review_and_save(
            brand=brand,
            voice=voice,
            brief=campaign_brief,
            rule_pack=rule_pack,
            additional_sections=self._prompt_sections(rendered_prompt),
        )

        return MarketingBriefCampaignResult(
            campaign_review=campaign_review,
            rendered_prompt=rendered_prompt,
            campaign_plan_audit=campaign_plan_audit,
        )

    @staticmethod
    def _campaign_plan_audit(
        campaign_plan: CampaignPlan | None,
        brief: MarketingBrief,
        channel: str,
    ) -> CampaignPlanAuditMetadata | None:
        if campaign_plan is None:
            return None
        if not isinstance(campaign_plan, CampaignPlan):
            raise TypeError("campaign_plan must be a CampaignPlan or None.")
        if campaign_plan.status not in {
            CampaignStatus.APPROVED,
            CampaignStatus.ACTIVE,
        }:
            raise ValueError(
                "Only approved or active Campaign Plans may govern generation."
            )
        if campaign_plan.tenant_id != brief.tenant_id:
            raise ValueError("The Marketing Brief and Campaign Plan tenants differ.")
        if campaign_plan.brand_id != brief.brand_id:
            raise ValueError("The Marketing Brief and Campaign Plan brands differ.")
        plan_channels = {item.name.casefold() for item in campaign_plan.channels}
        if channel.casefold() not in plan_channels:
            raise ValueError(
                "The selected channel is not included in the Campaign Plan."
            )
        reference = CampaignBriefReference(
            campaign_id=campaign_plan.campaign_id,
            brief_id=brief.brief_id,
            brief_version=brief.version,
            tenant_id=brief.tenant_id,
            brand_id=brief.brand_id,
        )
        return CampaignPlanAuditMetadata.from_plan_and_reference(
            campaign_plan,
            reference,
        )

    @classmethod
    def _resolve_channel(
        cls,
        brief: MarketingBrief,
        channel: str,
    ) -> str:
        if not isinstance(channel, str):
            raise TypeError("channel must be a string.")

        cleaned_channel = channel.strip()

        if not cleaned_channel:
            if not brief.channels:
                raise ValueError(
                    "An approved Marketing Brief must provide " "at least one channel."
                )

            return brief.channels[0]

        if brief.channels and cleaned_channel.casefold() not in {
            configured_channel.casefold() for configured_channel in brief.channels
        }:
            raise ValueError(
                "The selected channel is not included in the " "Marketing Brief."
            )

        return cleaned_channel

    @staticmethod
    def _additional_context(
        brief: MarketingBrief,
    ) -> str:
        parts: list[str] = []

        if brief.notes:
            parts.append(brief.notes)

        if brief.constraints:
            parts.append(
                "Constraints:\n"
                + "\n".join(f"- {constraint}" for constraint in brief.constraints)
            )

        if brief.success_metrics:
            parts.append(
                "Success metrics:\n"
                + "\n".join(f"- {metric}" for metric in brief.success_metrics)
            )

        return "\n\n".join(parts)

    @staticmethod
    def _prompt_sections(
        rendered_prompt: RenderedMarketingBriefPrompt,
    ) -> tuple[PromptSection, ...]:
        sections = [
            PromptSection(
                title="Selected Prompt Pack",
                content=rendered_prompt.prompt.content,
            ),
            PromptSection(
                title="Prompt Pack System Requirements",
                content=(rendered_prompt.prompt.system_instruction),
            ),
        ]

        return tuple(section for section in sections if section.render())

    @staticmethod
    def _required_text(
        field_name: str,
        value: str,
    ) -> str:
        if not isinstance(value, str):
            raise TypeError(f"{field_name} must be a string.")

        cleaned_value = value.strip()

        if not cleaned_value:
            raise ValueError(f"{field_name} is required.")

        return cleaned_value
