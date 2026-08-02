"""Tests for core MarketingLabAI data models."""

from __future__ import annotations

import unittest

from app.models import (
    BrandProfile,
    CampaignBrief,
    GeneratedContent,
    VoiceProfile,
)


class ModelTests(unittest.TestCase):
    def test_brand_profile_to_dict(
        self,
    ) -> None:
        brand = BrandProfile(
            brand_id="test-brand",
            name="Test Brand",
            industry="Testing",
            description="A test brand.",
            target_audience="Developers",
        )

        data = brand.to_dict()

        self.assertEqual(
            data["brand_id"],
            "test-brand",
        )
        self.assertEqual(
            data["name"],
            "Test Brand",
        )

    def test_voice_profile_to_dict(
        self,
    ) -> None:
        voice = VoiceProfile(
            voice_id="voice-1",
            brand_id="test-brand",
            summary="Clear and direct.",
            tone_traits=[
                "clear",
                "direct",
            ],
        )

        self.assertEqual(
            voice.to_dict()["tone_traits"],
            [
                "clear",
                "direct",
            ],
        )

    def test_campaign_brief_to_dict(
        self,
    ) -> None:
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

    def test_generated_content_supports_legacy_construction(
        self,
    ) -> None:
        generated = GeneratedContent(
            campaign_id="campaign-1",
            platform="LinkedIn",
            content_type="Post",
            content="Generated content",
            model="test-model",
        )

        self.assertEqual(
            generated.provider,
            "",
        )
        self.assertIsNone(
            generated.input_tokens,
        )
        self.assertIsNone(
            generated.output_tokens,
        )
        self.assertEqual(
            generated.metadata,
            {},
        )

    def test_generated_content_preserves_audit_metadata(
        self,
    ) -> None:
        metadata = {
            "request_id": "request-1",
        }

        generated = GeneratedContent(
            campaign_id="campaign-1",
            platform="LinkedIn",
            content_type="Post",
            content="Generated content",
            provider="mock",
            model="test-model",
            input_tokens=10,
            output_tokens=20,
            finish_reason="stop",
            metadata=metadata,
        )

        self.assertEqual(
            generated.provider,
            "mock",
        )
        self.assertEqual(
            generated.input_tokens,
            10,
        )
        self.assertEqual(
            generated.output_tokens,
            20,
        )
        self.assertEqual(
            generated.finish_reason,
            "stop",
        )
        self.assertEqual(
            generated.metadata,
            metadata,
        )
        self.assertIsNot(
            generated.metadata,
            metadata,
        )

    def test_generated_content_to_dict_copies_metadata(
        self,
    ) -> None:
        generated = GeneratedContent(
            campaign_id="campaign-1",
            platform="LinkedIn",
            content_type="Post",
            content="Generated content",
            provider="mock",
            model="test-model",
            metadata={
                "request_id": "request-1",
            },
        )

        data = generated.to_dict()

        self.assertEqual(
            data["provider"],
            "mock",
        )
        self.assertEqual(
            data["metadata"],
            {
                "request_id": "request-1",
            },
        )
        self.assertIsNot(
            data["metadata"],
            generated.metadata,
        )

    def test_generated_content_rejects_negative_tokens(
        self,
    ) -> None:
        with self.assertRaisesRegex(
            ValueError,
            "input_tokens",
        ):
            GeneratedContent(
                campaign_id="campaign-1",
                platform="LinkedIn",
                content_type="Post",
                content="Generated content",
                model="test-model",
                input_tokens=-1,
            )


if __name__ == "__main__":
    unittest.main()
