"""Tests for the provider-neutral AI orchestrator."""

from __future__ import annotations

import unittest

from app.ai.models import IntelligenceRequest
from app.ai.orchestrator import AIOrchestrator
from app.ai.providers.mock import MockIntelligenceProvider
from app.ai.registry import IntelligenceProviderRegistry


class NamedMockProvider(MockIntelligenceProvider):
    def __init__(
        self,
        provider_name: str,
        response_content: str,
    ) -> None:
        super().__init__(
            response_content=response_content,
            model=f"{provider_name}-model",
        )
        self._provider_name = provider_name

    @property
    def provider_name(self) -> str:
        return self._provider_name


class AIOrchestratorTests(unittest.TestCase):
    def setUp(self) -> None:
        self.registry = IntelligenceProviderRegistry()
        self.provider = NamedMockProvider(
            "primary",
            "Generated campaign",
        )
        self.registry.register(self.provider)
        self.orchestrator = AIOrchestrator(self.registry)

    def test_generate_uses_active_provider(self) -> None:
        response = self.orchestrator.generate(
            tenant_id="tenant-one",
            brand_id="brand-one",
            task="Create a campaign",
        )

        self.assertEqual(
            response.content,
            "Generated campaign",
        )
        self.assertEqual(response.provider, "primary")
        self.assertEqual(len(self.provider.requests), 1)

    def test_generate_builds_prompt_with_instructions(
        self,
    ) -> None:
        self.orchestrator.generate(
            tenant_id="tenant-one",
            brand_id="brand-one",
            task="Create a campaign",
            instructions="Focus on trust and reliability.",
        )

        request = self.provider.requests[0]

        self.assertEqual(
            request.prompt,
            (
                "Task:\nCreate a campaign\n\n"
                "Instructions:\n"
                "Focus on trust and reliability."
            ),
        )

    def test_generate_passes_provider_options(self) -> None:
        self.orchestrator.generate(
            tenant_id="tenant-one",
            brand_id="brand-one",
            task="Create a campaign",
            system_instruction="Follow brand rules.",
            model="model-one",
            temperature=0.4,
            max_output_tokens=700,
        )

        request = self.provider.requests[0]

        self.assertEqual(
            request.system_instruction,
            "Follow brand rules.",
        )
        self.assertEqual(request.model, "model-one")
        self.assertEqual(request.temperature, 0.4)
        self.assertEqual(
            request.max_output_tokens,
            700,
        )

    def test_generate_adds_application_metadata(
        self,
    ) -> None:
        self.orchestrator.generate(
            tenant_id="tenant-one",
            brand_id="brand-one",
            task="Create a campaign",
            metadata={"request_id": "request-one"},
        )

        request = self.provider.requests[0]

        self.assertEqual(
            request.metadata,
            {
                "request_id": "request-one",
                "tenant_id": "tenant-one",
                "brand_id": "brand-one",
                "task": "Create a campaign",
                "company_brain_included": False,
            },
        )

    def test_generate_can_override_provider(self) -> None:
        secondary = NamedMockProvider(
            "secondary",
            "Secondary response",
        )
        self.registry.register(secondary)

        response = self.orchestrator.generate(
            tenant_id="tenant-one",
            brand_id="brand-one",
            task="Create a campaign",
            provider_name="secondary",
        )

        self.assertEqual(
            response.content,
            "Secondary response",
        )
        self.assertEqual(len(self.provider.requests), 0)
        self.assertEqual(len(secondary.requests), 1)

    def test_generate_rejects_blank_tenant(self) -> None:
        with self.assertRaisesRegex(
            ValueError,
            "tenant_id",
        ):
            self.orchestrator.generate(
                tenant_id=" ",
                brand_id="brand-one",
                task="Create a campaign",
            )

    def test_generate_rejects_blank_brand(self) -> None:
        with self.assertRaisesRegex(
            ValueError,
            "brand_id",
        ):
            self.orchestrator.generate(
                tenant_id="tenant-one",
                brand_id=" ",
                task="Create a campaign",
            )

    def test_generate_rejects_blank_task(self) -> None:
        with self.assertRaisesRegex(
            ValueError,
            "task",
        ):
            self.orchestrator.generate(
                tenant_id="tenant-one",
                brand_id="brand-one",
                task=" ",
            )

    def test_orchestrator_rejects_invalid_registry(
        self,
    ) -> None:
        with self.assertRaisesRegex(
            TypeError,
            "IntelligenceProviderRegistry",
        ):
            AIOrchestrator(object())  # type: ignore[arg-type]

    def test_provider_receives_intelligence_request(
        self,
    ) -> None:
        self.orchestrator.generate(
            tenant_id="tenant-one",
            brand_id="brand-one",
            task="Create a campaign",
        )

        self.assertIsInstance(
            self.provider.requests[0],
            IntelligenceRequest,
        )


if __name__ == "__main__":
    unittest.main()
