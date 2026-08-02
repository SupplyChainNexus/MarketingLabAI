"""Provider-neutral campaign content generation engine."""

from __future__ import annotations

from app.ai.bootstrap import gemini_provider_bootstrap
from app.ai.orchestrator import AIOrchestrator
from app.models import (
    BrandProfile,
    CampaignBrief,
    GeneratedContent,
    VoiceProfile,
)


class CampaignEngine:
    """Generate content using verified brand and voice information."""

    def __init__(
        self,
        orchestrator: AIOrchestrator | None = None,
        *,
        tenant_id: str = "default",
        provider_name: str | None = None,
    ) -> None:
        if orchestrator is not None and not isinstance(
            orchestrator,
            AIOrchestrator,
        ):
            raise TypeError("orchestrator must be an AIOrchestrator.")

        if not isinstance(tenant_id, str):
            raise TypeError("tenant_id must be a string.")

        cleaned_tenant_id = tenant_id.strip()

        if not cleaned_tenant_id:
            raise ValueError("tenant_id is required.")

        if provider_name is not None:
            if not isinstance(provider_name, str):
                raise TypeError("provider_name must be a string or None.")

            provider_name = provider_name.strip()

            if not provider_name:
                raise ValueError("provider_name cannot be blank.")

        self.orchestrator = (
            orchestrator
            if orchestrator is not None
            else gemini_provider_bootstrap().build_orchestrator()
        )
        self.tenant_id = cleaned_tenant_id
        self.provider_name = provider_name

    def build_campaign_prompt(
        self,
        brand: BrandProfile,
        voice: VoiceProfile,
        brief: CampaignBrief,
    ) -> str:
        """Build campaign instructions from verified inputs."""

        if not isinstance(brand, BrandProfile):
            raise TypeError("brand must be a BrandProfile.")

        if not isinstance(voice, VoiceProfile):
            raise TypeError("voice must be a VoiceProfile.")

        if not isinstance(brief, CampaignBrief):
            raise TypeError("brief must be a CampaignBrief.")

        if brand.brand_id != voice.brand_id:
            raise ValueError("The voice profile does not belong " "to this brand.")

        if brand.brand_id != brief.brand_id:
            raise ValueError("The campaign brief does not belong " "to this brand.")

        preferred_words = ", ".join(voice.preferred_words) or "None specified"
        avoided_words = ", ".join(voice.avoided_words) or "None specified"
        authenticity_rules = "\n".join(f"- {rule}" for rule in voice.authenticity_rules)

        return f"""
Create one finished marketing asset using only the verified brand information,
campaign brief, and voice profile below.

NON-NEGOTIABLE AUTHENTICITY RULES

- Do not fabricate customer stories, statistics, awards, credentials,
  partnerships, guarantees, outcomes, prices, or personal experience.
- Do not introduce facts that were not supplied.
- When information is insufficient, use neutral wording instead of guessing.
{authenticity_rules or "- Preserve factual accuracy."}

BRAND

Name: {brand.name}
Industry: {brand.industry}
Description: {brand.description}
Audience: {brand.target_audience}
Products or services: {", ".join(brand.products_or_services)}
Values: {", ".join(brand.values)}
Website: {brand.website or "Not supplied"}

VOICE PROFILE

Summary: {voice.summary}
Tone traits: {", ".join(voice.tone_traits)}
Preferred wording: {preferred_words}
Avoided wording: {avoided_words}
Sentence style: {voice.sentence_style}
Call-to-action style: {voice.call_to_action_style}

CAMPAIGN BRIEF

Objective: {brief.objective}
Audience: {brief.audience}
Offer: {brief.offer}
Platform: {brief.platform}
Content type: {brief.content_type}
Key message: {brief.key_message}
Call to action: {brief.call_to_action}
Additional context: {brief.additional_context or "None"}

Return only the finished marketing content.
Do not provide analysis, process notes, or explanations.
""".strip()

    def generate_campaign_content(
        self,
        brand: BrandProfile,
        voice: VoiceProfile,
        brief: CampaignBrief,
    ) -> GeneratedContent:
        """Generate campaign content through the AI platform."""

        instructions = self.build_campaign_prompt(
            brand=brand,
            voice=voice,
            brief=brief,
        )

        response = self.orchestrator.generate(
            tenant_id=self.tenant_id,
            brand_id=brand.brand_id,
            task=(f"Generate one {brief.content_type} " f"for {brief.platform}."),
            instructions=instructions,
            system_instruction=(
                "You are the MarketingLabAI Campaign Engine. "
                "Produce accurate, brand-aligned marketing "
                "content using only supplied facts."
            ),
            provider_name=self.provider_name,
            metadata={
                "campaign_id": brief.campaign_id,
                "voice_id": voice.voice_id,
                "platform": brief.platform,
                "content_type": brief.content_type,
                "workflow": "campaign_generation",
            },
        )

        content = response.content.strip()

        if not content:
            raise RuntimeError("The Campaign Engine returned empty content.")

        return GeneratedContent(
            campaign_id=brief.campaign_id,
            platform=brief.platform,
            content_type=brief.content_type,
            content=content,
            provider=response.provider,
            model=response.model,
            input_tokens=response.input_tokens,
            output_tokens=response.output_tokens,
            finish_reason=response.finish_reason,
            metadata=dict(response.metadata),
        )
