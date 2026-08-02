"""Tests for provider-neutral AI infrastructure."""

from __future__ import annotations

import unittest
from typing import cast

from app.ai.capabilities import ProviderCapabilities
from app.ai.models import (
    IntelligenceRequest,
    IntelligenceResponse,
)
from app.ai.provider import IntelligenceProvider
from app.ai.providers.mock import MockIntelligenceProvider


class IntelligenceRequestTests(unittest.TestCase):
    def test_request_cleans_values(self) -> None:
        request = IntelligenceRequest(
            prompt=" Create a campaign ",
            system_instruction=" Follow the brand voice ",
            model=" gemini-test ",
        )

        self.assertEqual(
            request.prompt,
            "Create a campaign",
        )
        self.assertEqual(
            request.system_instruction,
            "Follow the brand voice",
        )
        self.assertEqual(
            request.model,
            "gemini-test",
        )

    def test_request_rejects_blank_prompt(self) -> None:
        with self.assertRaisesRegex(
            ValueError,
            "prompt",
        ):
            IntelligenceRequest(prompt=" ")

    def test_request_rejects_invalid_temperature(
        self,
    ) -> None:
        with self.assertRaisesRegex(
            ValueError,
            "temperature",
        ):
            IntelligenceRequest(
                prompt="Create campaign",
                temperature=2.1,
            )

    def test_request_rejects_invalid_token_limit(
        self,
    ) -> None:
        with self.assertRaisesRegex(
            ValueError,
            "max_output_tokens",
        ):
            IntelligenceRequest(
                prompt="Create campaign",
                max_output_tokens=0,
            )

    def test_request_round_trip(self) -> None:
        request = IntelligenceRequest(
            prompt="Create campaign",
            system_instruction="Use brand voice",
            model="model-one",
            temperature=0.5,
            max_output_tokens=500,
            metadata={
                "brand_id": "brand-one",
            },
        )

        restored = IntelligenceRequest.from_dict(request.to_dict())

        self.assertEqual(
            restored,
            request,
        )


class IntelligenceResponseTests(unittest.TestCase):
    def test_response_round_trip(self) -> None:
        response = IntelligenceResponse(
            content="Generated copy",
            provider="mock",
            model="mock-model",
            input_tokens=10,
            output_tokens=20,
            finish_reason="stop",
            metadata={
                "request_id": "request-one",
            },
        )

        restored = IntelligenceResponse.from_dict(response.to_dict())

        self.assertEqual(
            restored,
            response,
        )

    def test_response_rejects_negative_tokens(
        self,
    ) -> None:
        with self.assertRaisesRegex(
            ValueError,
            "input_tokens",
        ):
            IntelligenceResponse(
                content="Generated copy",
                provider="mock",
                model="mock-model",
                input_tokens=-1,
            )


class IntelligenceProviderTests(unittest.TestCase):
    def test_provider_interface_is_abstract(
        self,
    ) -> None:
        with self.assertRaises(TypeError):
            IntelligenceProvider()

    def test_mock_provider_exposes_default_capabilities(
        self,
    ) -> None:
        provider = MockIntelligenceProvider(model="mock-model")

        self.assertIsInstance(
            provider.capabilities,
            ProviderCapabilities,
        )
        self.assertTrue(provider.capabilities.supports_model("mock-model"))
        self.assertFalse(provider.capabilities.supports_streaming)
        self.assertFalse(provider.capabilities.supports_tools)

    def test_mock_provider_accepts_custom_capabilities(
        self,
    ) -> None:
        capabilities = ProviderCapabilities(
            supports_structured_output=True,
            supports_streaming=True,
            supports_tools=True,
            maximum_context_tokens=32_000,
            available_models=[
                "mock-model",
                "mock-tools-model",
            ],
        )

        provider = MockIntelligenceProvider(capabilities=capabilities)

        self.assertIs(
            provider.capabilities,
            capabilities,
        )
        self.assertTrue(provider.capabilities.supports_streaming)
        self.assertTrue(provider.capabilities.supports_tools)
        self.assertEqual(
            provider.capabilities.maximum_context_tokens,
            32_000,
        )

    def test_mock_provider_rejects_invalid_capabilities(
        self,
    ) -> None:
        invalid_capabilities = cast(
            ProviderCapabilities,
            object(),
        )

        with self.assertRaisesRegex(
            TypeError,
            "ProviderCapabilities",
        ):
            MockIntelligenceProvider(capabilities=invalid_capabilities)

    def test_mock_provider_records_requests(
        self,
    ) -> None:
        provider = MockIntelligenceProvider(response_content="Generated copy")
        request = IntelligenceRequest(
            prompt="Create campaign",
            model="requested-model",
        )

        response = provider.generate(request)

        self.assertEqual(
            provider.requests,
            [request],
        )
        self.assertEqual(
            response.content,
            "Generated copy",
        )
        self.assertEqual(
            response.provider,
            "mock",
        )
        self.assertEqual(
            response.model,
            "requested-model",
        )

    def test_mock_provider_uses_response_factory(
        self,
    ) -> None:
        def factory(
            request: IntelligenceRequest,
        ) -> IntelligenceResponse:
            return IntelligenceResponse(
                content=f"Echo: {request.prompt}",
                provider="custom-mock",
                model="factory-model",
            )

        provider = MockIntelligenceProvider(response_factory=factory)

        response = provider.generate(
            IntelligenceRequest(
                prompt="Create campaign",
            )
        )

        self.assertEqual(
            response.content,
            "Echo: Create campaign",
        )
        self.assertEqual(
            response.provider,
            "custom-mock",
        )

    def test_mock_provider_rejects_invalid_request(
        self,
    ) -> None:
        provider = MockIntelligenceProvider()

        with self.assertRaisesRegex(
            TypeError,
            "IntelligenceRequest",
        ):
            provider.generate("invalid")  # type: ignore[arg-type]


if __name__ == "__main__":
    unittest.main()
