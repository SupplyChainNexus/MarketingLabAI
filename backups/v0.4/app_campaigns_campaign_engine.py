"""Campaign content generation engine."""

from app.ai.gemini_client import GeminiClient, get_gemini_client
from app.models import (
    BrandProfile,
    CampaignBrief,
    GeneratedContent,
    VoiceProfile,
)


class CampaignEngine:
    """Generate marketing content using brand and voice profiles."""

    def __init__(
        self,
        gemini_client: GeminiClient | None = None,
    ):
        self.gemini_client = gemini_client or get_gemini_client()

    def build_campaign_prompt(
        self,
        brand: BrandProfile,
        voice: VoiceProfile,
        brief: CampaignBrief,
    ) -> str:
        if brand.brand_id != voice.brand_id:
            raise ValueError(
                "The voice profile does not belong to this brand."
            )

        if brand.brand_id != brief.brand_id:
            raise ValueError(
                "The campaign brief does not belong to this brand."
            )

        preferred_words = ", ".join(voice.preferred_words) or "None specified"
        avoided_words = ", ".join(voice.avoided_words) or "None specified"
        authenticity_rules = "\n".join(
            f"- {rule}" for rule in voice.authenticity_rules
        )

        return f"""
You are the MarketingLabAI Campaign Engine.

Create one finished marketing asset using the verified brand information,
campaign brief, and voice profile below.

NON-NEGOTIABLE AUTHENTICITY RULES

- Do not fabricate customer stories, statistics, awards, credentials,
  partnerships, guarantees, outcomes, or personal experience.
- Do not introduce facts that are not supplied.
- When information is insufficient, use neutral wording rather than guessing.
{authenticity_rules}

BRAND

Name: {brand.name}
Industry: {brand.industry}
Description: {brand.description}
Audience: {brand.target_audience}
Products or services: {", ".join(brand.products_or_services)}
Values: {", ".join(brand.values)}

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
Do not provide an explanation or analysis.
""".strip()

    def generate_campaign_content(
        self,
        brand: BrandProfile,
        voice: VoiceProfile,
        brief: CampaignBrief,
    ) -> GeneratedContent:
        prompt = self.build_campaign_prompt(
            brand=brand,
            voice=voice,
            brief=brief,
        )

        content = self.gemini_client.generate_text(prompt)

        return GeneratedContent(
            campaign_id=brief.campaign_id,
            platform=brief.platform,
            content_type=brief.content_type,
            content=content,
            model=self.gemini_client.settings.gemini_model,
        )
