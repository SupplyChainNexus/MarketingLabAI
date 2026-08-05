"""Tests for the provider-neutral AI orchestrator."""

from __future__ import annotations

import unittest

from app.ai.models import IntelligenceRequest
from app.ai.orchestrator import AIOrchestrator
from app.ai.prompt import PromptSection
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
                "customer_intelligence_included": False,
                "product_intelligence_included": False,
                "memory_included": False,
                "memory_count": 0,
                "positioning_intelligence_included": False,
                "positioning_id": "",
                "positioning_version": 0,
            },
        )

    def test_build_prompt_includes_customer_intelligence(self) -> None:
        from app.ai.assembler import AIContext

        prompt = self.orchestrator._build_prompt(
            context=AIContext(
                customer_context="- Pain points: Vehicle downtime",
            ),
            task="Create a campaign",
            instructions="Use verified context only.",
        )

        self.assertIn("Customer Context:", prompt)
        self.assertIn("- Pain points: Vehicle downtime", prompt)

    def test_build_prompt_keeps_verified_product_context_separate(self) -> None:
        from app.ai.assembler import AIContext

        prompt = self.orchestrator._build_prompt(
            context=AIContext(product_context="Price: Unknown"),
            task="Create a campaign",
            instructions="Use verified context only.",
        )

        self.assertIn("Verified Product and Offer Context:", prompt)
        self.assertIn("Price: Unknown", prompt)

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

    def test_generate_adds_additional_prompt_sections(
        self,
    ) -> None:
        self.orchestrator.generate(
            tenant_id="tenant-one",
            brand_id="brand-one",
            task="Create a campaign.",
            instructions="Return final content only.",
            additional_sections=[
                PromptSection(
                    title="Compliance Requirements",
                    content=(
                        "- Include the phrase Terms apply.\n"
                        "- Keep the content within 100 characters."
                    ),
                ),
            ],
        )

        request = self.provider.requests[0]

        self.assertIn(
            "Compliance Requirements:",
            request.prompt,
        )
        self.assertIn(
            "Include the phrase Terms apply.",
            request.prompt,
        )
        self.assertIn(
            "Keep the content within 100 characters.",
            request.prompt,
        )

    def test_additional_sections_have_deterministic_order(
        self,
    ) -> None:
        self.orchestrator.generate(
            tenant_id="tenant-one",
            brand_id="brand-one",
            task="Create a campaign.",
            instructions="Return final content only.",
            additional_sections=[
                PromptSection(
                    title="First Extension",
                    content="First content.",
                ),
                PromptSection(
                    title="Second Extension",
                    content="Second content.",
                ),
            ],
        )

        prompt = self.provider.requests[0].prompt

        self.assertLess(
            prompt.index("Task:"),
            prompt.index("First Extension:"),
        )
        self.assertLess(
            prompt.index("First Extension:"),
            prompt.index("Second Extension:"),
        )
        self.assertLess(
            prompt.index("Second Extension:"),
            prompt.index("Instructions:"),
        )

    def test_generate_omits_empty_additional_section(
        self,
    ) -> None:
        self.orchestrator.generate(
            tenant_id="tenant-one",
            brand_id="brand-one",
            task="Create a campaign.",
            additional_sections=[
                PromptSection(
                    title="Optional Context",
                    content=" ",
                ),
            ],
        )

        request = self.provider.requests[0]

        self.assertNotIn(
            "Optional Context:",
            request.prompt,
        )

    def test_generate_rejects_invalid_section_collection(
        self,
    ) -> None:
        with self.assertRaisesRegex(
            TypeError,
            "sequence",
        ):
            self.orchestrator.generate(
                tenant_id="tenant-one",
                brand_id="brand-one",
                task="Create a campaign.",
                additional_sections=("invalid"),  # type: ignore[arg-type]
            )

    def test_generate_rejects_invalid_section_entry(
        self,
    ) -> None:
        with self.assertRaisesRegex(
            TypeError,
            "PromptSection",
        ):
            self.orchestrator.generate(
                tenant_id="tenant-one",
                brand_id="brand-one",
                task="Create a campaign.",
                additional_sections=[
                    object(),  # type: ignore[list-item]
                ],
            )


if __name__ == "__main__":
    unittest.main()
