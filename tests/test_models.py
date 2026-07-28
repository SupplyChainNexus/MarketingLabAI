"""Tests for core MarketingLabAI data models."""

import unittest

from app.models import BrandProfile, CampaignBrief, VoiceProfile


class ModelTests(unittest.TestCase):

    def test_brand_profile_to_dict(self):
        brand = BrandProfile(
            brand_id="test-brand",
            name="Test Brand",
            industry="Testing",
            description="A test brand.",
            target_audience="Developers",
        )

        data = brand.to_dict()

        self.assertEqual(data["brand_id"], "test-brand")
        self.assertEqual(data["name"], "Test Brand")

    def test_voice_profile_to_dict(self):
        voice = VoiceProfile(
            voice_id="voice-1",
            brand_id="test-brand",
            summary="Clear and direct.",
            tone_traits=["clear", "direct"],
        )

        self.assertEqual(
            voice.to_dict()["tone_traits"],
            ["clear", "direct"],
        )

    def test_campaign_brief_to_dict(self):
        brief = CampaignBrief(
            campaign_id="campaign-1",
            brand_id="test-brand",
            objective="Awareness",
            audience="Developers",
            offer="Free demonstration",
            platform="LinkedIn",
            content_type="Post",
            key_message="Save time",
            call_to_action="Book a demonstration",
        )

        self.assertEqual(
            brief.to_dict()["platform"],
            "LinkedIn",
        )


if __name__ == "__main__":
    unittest.main()
