"""Tests for Campaign Engine prompt construction."""

import unittest

from app.campaigns.campaign_engine import CampaignEngine
from app.models import BrandProfile, CampaignBrief, VoiceProfile


class FakeGeminiClient:
    """Gemini replacement used by local unit tests."""

    settings = None

    def generate_text(self, prompt: str) -> str:
        return "Generated content"


class CampaignEngineTests(unittest.TestCase):

    def setUp(self):
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
            authenticity_rules=["Never claim results that were not supplied."],
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

    def test_campaign_prompt_contains_authenticity_rules(self):
        engine = CampaignEngine(gemini_client=FakeGeminiClient())

        prompt = engine.build_campaign_prompt(
            self.brand,
            self.voice,
            self.brief,
        )

        self.assertIn("Do not fabricate", prompt)
        self.assertIn("Example Brand", prompt)
        self.assertIn("Send us a message", prompt)

    def test_rejects_mismatched_voice(self):
        incorrect_voice = VoiceProfile(
            voice_id="voice-2",
            brand_id="another-brand",
            summary="Different voice.",
            tone_traits=["formal"],
        )

        engine = CampaignEngine(gemini_client=FakeGeminiClient())

        with self.assertRaises(ValueError):
            engine.build_campaign_prompt(
                self.brand,
                incorrect_voice,
                self.brief,
            )


if __name__ == "__main__":
    unittest.main()
