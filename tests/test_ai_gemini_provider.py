"""Tests for the Gemini intelligence provider adapter."""

from __future__ import annotations

import unittest
from dataclasses import dataclass
from typing import cast

from app.ai.models import IntelligenceRequest
from app.ai.providers.gemini import (
    GeminiIntelligenceProvider,
    GeminiTextClient,
)


@dataclass
class FakeGeminiSettings:
    """Configuration used by the fake Gemini client."""

    gemini_model: str = "gemini-test-model"


class FakeGeminiClient:
    """Deterministic low-level Gemini client replacement."""

    def __init__(
        self,
        response: str = "Generated response",
        *,
        model: str = "gemini-test-model",
    ) -> None:
        self.settings = FakeGeminiSettings(gemini_model=model)
        self.response = response
        self.prompts: list[str] = []

    def generate_text(
        self,
        prompt: str,
    ) -> str:
        self.prompts.append(prompt)
        return self.response


class GeminiIntelligenceProviderTests(unittest.TestCase):
    def setUp(self) -> None:
        self.client = FakeGeminiClient()
        self.provider = GeminiIntelligenceProvider(self.client)

    def test_provider_name_is_stable(self) -> None:
        self.assertEqual(
            self.provider.provider_name,
            "gemini",
        )

    def test_provider_declares_configured_model(
        self,
    ) -> None:
        self.assertTrue(self.provider.capabilities.supports_model("gemini-test-model"))

    def test_capabilities_are_conservative(
        self,
    ) -> None:
        capabilities = self.provider.capabilities

        self.assertFalse(capabilities.supports_streaming)
        self.assertFalse(capabilities.supports_tools)
        self.assertFalse(capabilities.supports_structured_output)
        self.assertFalse(capabilities.supports_images)
        self.assertFalse(capabilities.supports_documents)
        self.assertIsNone(capabilities.maximum_context_tokens)

    def test_generate_returns_normalized_response(
        self,
    ) -> None:
        response = self.provider.generate(
            IntelligenceRequest(
                prompt="Create a campaign",
            )
        )

        self.assertEqual(
            response.content,
            "Generated response",
        )
        self.assertEqual(
            response.provider,
            "gemini",
        )
        self.assertEqual(
            response.model,
            "gemini-test-model",
        )
        self.assertEqual(
            response.finish_reason,
            "stop",
        )

    def test_generate_passes_plain_prompt(
        self,
    ) -> None:
        self.provider.generate(
            IntelligenceRequest(
                prompt="Create a campaign",
            )
        )

        self.assertEqual(
            self.client.prompts,
            [
                "Create a campaign",
            ],
        )

    def test_generate_includes_system_instruction(
        self,
    ) -> None:
        self.provider.generate(
            IntelligenceRequest(
                prompt="Create a campaign",
                system_instruction=("Follow the brand voice."),
            )
        )

        prompt = self.client.prompts[0]

        self.assertIn(
            "Follow the brand voice.",
            prompt,
        )
        self.assertIn(
            "Create a campaign",
            prompt,
        )
        self.assertIn(
            "System Instruction",
            prompt,
        )
        self.assertIn(
            "User Request",
            prompt,
        )

    def test_generate_accepts_configured_model(
        self,
    ) -> None:
        response = self.provider.generate(
            IntelligenceRequest(
                prompt="Create a campaign",
                model="gemini-test-model",
            )
        )

        self.assertEqual(
            response.model,
            "gemini-test-model",
        )

    def test_generate_rejects_unconfigured_model(
        self,
    ) -> None:
        with self.assertRaisesRegex(
            ValueError,
            "not configured",
        ):
            self.provider.generate(
                IntelligenceRequest(
                    prompt="Create a campaign",
                    model="different-model",
                )
            )

    def test_generate_preserves_request_metadata(
        self,
    ) -> None:
        metadata = {
            "tenant_id": "tenant-one",
            "brand_id": "brand-one",
        }

        response = self.provider.generate(
            IntelligenceRequest(
                prompt="Create a campaign",
                metadata=metadata,
            )
        )

        self.assertEqual(
            response.metadata["request_metadata"],
            metadata,
        )
        self.assertIsNot(
            response.metadata["request_metadata"],
            metadata,
        )

    def test_generate_rejects_invalid_request(
        self,
    ) -> None:
        with self.assertRaisesRegex(
            TypeError,
            "IntelligenceRequest",
        ):
            self.provider.generate("invalid")  # type: ignore[arg-type]

    def test_generate_rejects_empty_content(
        self,
    ) -> None:
        provider = GeminiIntelligenceProvider(FakeGeminiClient(response=" "))

        with self.assertRaisesRegex(
            RuntimeError,
            "empty content",
        ):
            provider.generate(IntelligenceRequest(prompt="Create a campaign"))

    def test_rejects_invalid_client(self) -> None:
        invalid_client = cast(
            GeminiTextClient,
            object(),
        )

        with self.assertRaisesRegex(
            TypeError,
            "GeminiTextClient",
        ):
            GeminiIntelligenceProvider(invalid_client)

    def test_rejects_blank_configured_model(
        self,
    ) -> None:
        with self.assertRaisesRegex(
            ValueError,
            "model is required",
        ):
            GeminiIntelligenceProvider(FakeGeminiClient(model=" "))

    def test_rejects_non_string_configured_model(
        self,
    ) -> None:
        client = FakeGeminiClient()
        client.settings.gemini_model = 123  # type: ignore[assignment]

        with self.assertRaisesRegex(
            TypeError,
            "model must be a string",
        ):
            GeminiIntelligenceProvider(client)


if __name__ == "__main__":
    unittest.main()
