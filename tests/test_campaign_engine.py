"""Tests for provider-neutral Campaign Engine generation."""

from __future__ import annotations

import unittest
from typing import cast

from app.ai.capabilities import ProviderCapabilities
from app.ai.orchestrator import AIOrchestrator
from app.ai.providers.mock import MockIntelligenceProvider
from app.ai.registry import IntelligenceProviderRegistry
from app.campaigns.campaign_engine import CampaignEngine
from app.models import (
    BrandProfile,
    CampaignBrief,
    VoiceProfile,
)


class CampaignEngineTests(unittest.TestCase):
    def setUp(self) -> None:
        self.provider = MockIntelligenceProvider(
            response_content="Generated campaign content.",
            model="campaign-test-model",
            capabilities=ProviderCapabilities(
                available_models=[
                    "campaign-test-model",
                ]
            ),
        )

        registry = IntelligenceProviderRegistry()
        registry.register(self.provider)

        self.orchestrator = AIOrchestrator(registry)

        self.engine = CampaignEngine(
            self.orchestrator,
            tenant_id="tenant-one",
        )

        self.brand = BrandProfile(
            brand_id="brand-1",
            name="Example Brand",
            industry="Retail",
            description="An example retailer.",
            target_audience="Local customers",
            products_or_services=[
                "Replacement parts",
            ],
            values=[
                "service",
            ],
        )

        self.voice = VoiceProfile(
            voice_id="voice-1",
            brand_id="brand-1",
            summary="Clear and helpful.",
            tone_traits=[
                "clear",
                "helpful",
            ],
            preferred_words=[
                "reliable",
            ],
            avoided_words=[
                "guaranteed",
            ],
            authenticity_rules=[
                "Never claim results that were not supplied.",
            ],
        )

        self.brief = CampaignBrief(
            campaign_id="campaign-1",
            brand_id="brand-1",
            objective="Generate enquiries",
            audience="Local customers",
            offer="Product availability",
            platform="Facebook",
            content_type="Social post",
            key_message=("Contact us for replacement parts"),
            call_to_action="Send us a message",
        )

    def test_campaign_prompt_contains_verified_context(
        self,
    ) -> None:
        prompt = self.engine.build_campaign_prompt(
            self.brand,
            self.voice,
            self.brief,
        )

        self.assertIn(
            "Do not fabricate",
            prompt,
        )
        self.assertIn(
            "Example Brand",
            prompt,
        )
        self.assertIn(
            "Replacement parts",
            prompt,
        )
        self.assertIn(
            "Send us a message",
            prompt,
        )
        self.assertIn(
            "Never claim results",
            prompt,
        )

    def test_rejects_mismatched_voice(
        self,
    ) -> None:
        incorrect_voice = VoiceProfile(
            voice_id="voice-2",
            brand_id="another-brand",
            summary="Different voice.",
            tone_traits=[
                "formal",
            ],
        )

        with self.assertRaisesRegex(
            ValueError,
            "voice profile",
        ):
            self.engine.build_campaign_prompt(
                self.brand,
                incorrect_voice,
                self.brief,
            )

    def test_rejects_mismatched_brief(
        self,
    ) -> None:
        incorrect_brief = CampaignBrief(
            campaign_id="campaign-2",
            brand_id="another-brand",
            objective="Generate enquiries",
            audience="Local customers",
            offer="Product availability",
            platform="Facebook",
            content_type="Social post",
            key_message="Contact us",
            call_to_action="Send us a message",
        )

        with self.assertRaisesRegex(
            ValueError,
            "campaign brief",
        ):
            self.engine.build_campaign_prompt(
                self.brand,
                self.voice,
                incorrect_brief,
            )

    def test_generate_uses_ai_orchestrator(
        self,
    ) -> None:
        generated = self.engine.generate_campaign_content(
            brand=self.brand,
            voice=self.voice,
            brief=self.brief,
        )

        self.assertEqual(
            generated.content,
            "Generated campaign content.",
        )
        self.assertEqual(
            generated.model,
            "campaign-test-model",
        )
        self.assertEqual(
            len(self.provider.requests),
            1,
        )

    def test_generate_passes_campaign_metadata(
        self,
    ) -> None:
        self.engine.generate_campaign_content(
            brand=self.brand,
            voice=self.voice,
            brief=self.brief,
        )

        request = self.provider.requests[0]

        self.assertEqual(
            request.metadata["tenant_id"],
            "tenant-one",
        )
        self.assertEqual(
            request.metadata["brand_id"],
            "brand-1",
        )
        self.assertEqual(
            request.metadata["campaign_id"],
            "campaign-1",
        )
        self.assertEqual(
            request.metadata["voice_id"],
            "voice-1",
        )
        self.assertEqual(
            request.metadata["workflow"],
            "campaign_generation",
        )

    def test_generate_includes_campaign_instructions(
        self,
    ) -> None:
        self.engine.generate_campaign_content(
            brand=self.brand,
            voice=self.voice,
            brief=self.brief,
        )

        request = self.provider.requests[0]

        self.assertIn(
            "Generate one Social post for Facebook.",
            request.prompt,
        )
        self.assertIn(
            "Example Brand",
            request.prompt,
        )
        self.assertIn(
            "Send us a message",
            request.prompt,
        )
        self.assertIn(
            "MarketingLabAI Campaign Engine",
            request.system_instruction,
        )

    def test_generate_can_override_provider(
        self,
    ) -> None:
        secondary = MockIntelligenceProvider(
            response_content="Secondary response",
            model="secondary-model",
            capabilities=ProviderCapabilities(
                available_models=[
                    "secondary-model",
                ]
            ),
        )

        class SecondaryProvider(MockIntelligenceProvider):
            @property
            def provider_name(self) -> str:
                return "secondary"

        secondary_provider = SecondaryProvider(
            response_content=secondary.response_content,
            model=secondary.model,
            capabilities=secondary.capabilities,
        )

        registry = IntelligenceProviderRegistry()
        registry.register(self.provider)
        registry.register(secondary_provider)

        engine = CampaignEngine(
            AIOrchestrator(registry),
            tenant_id="tenant-one",
            provider_name="secondary",
        )

        generated = engine.generate_campaign_content(
            brand=self.brand,
            voice=self.voice,
            brief=self.brief,
        )

        self.assertEqual(
            generated.content,
            "Secondary response",
        )
        self.assertEqual(
            len(self.provider.requests),
            0,
        )
        self.assertEqual(
            len(secondary_provider.requests),
            1,
        )

    def test_rejects_invalid_orchestrator(
        self,
    ) -> None:
        invalid_orchestrator = cast(
            AIOrchestrator,
            object(),
        )

        with self.assertRaisesRegex(
            TypeError,
            "AIOrchestrator",
        ):
            CampaignEngine(invalid_orchestrator)

    def test_rejects_blank_tenant(
        self,
    ) -> None:
        with self.assertRaisesRegex(
            ValueError,
            "tenant_id",
        ):
            CampaignEngine(
                self.orchestrator,
                tenant_id=" ",
            )

    def test_rejects_blank_provider_override(
        self,
    ) -> None:
        with self.assertRaisesRegex(
            ValueError,
            "provider_name",
        ):
            CampaignEngine(
                self.orchestrator,
                provider_name=" ",
            )


if __name__ == "__main__":
    unittest.main()
