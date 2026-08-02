"""Tests for deterministic AI provider selection."""

from __future__ import annotations

import unittest
from typing import cast

from app.ai.capabilities import ProviderCapabilities
from app.ai.provider import IntelligenceProvider
from app.ai.providers.mock import MockIntelligenceProvider
from app.ai.requirements import ProviderRequirements
from app.ai.selection import ProviderSelectionStrategy


class NamedMockProvider(MockIntelligenceProvider):
    """Mock provider with a configurable stable name."""

    def __init__(
        self,
        provider_name: str,
        capabilities: ProviderCapabilities,
    ) -> None:
        super().__init__(capabilities=capabilities)
        self._provider_name = provider_name

    @property
    def provider_name(self) -> str:
        return self._provider_name


class ProviderSelectionStrategyTests(unittest.TestCase):
    def setUp(self) -> None:
        self.strategy = ProviderSelectionStrategy()

        self.basic = NamedMockProvider(
            "basic",
            ProviderCapabilities(
                maximum_context_tokens=8_000,
                available_models=[
                    "basic-model",
                ],
            ),
        )

        self.advanced = NamedMockProvider(
            "advanced",
            ProviderCapabilities(
                supports_structured_output=True,
                supports_streaming=True,
                supports_tools=True,
                supports_images=True,
                supports_documents=True,
                maximum_context_tokens=128_000,
                available_models=[
                    "advanced-model",
                    "shared-model",
                ],
            ),
        )

        self.alternative = NamedMockProvider(
            "alternative",
            ProviderCapabilities(
                supports_streaming=True,
                supports_tools=True,
                maximum_context_tokens=64_000,
                available_models=[
                    "alternative-model",
                    "shared-model",
                ],
            ),
        )

    def test_selects_first_provider_when_no_special_requirements(
        self,
    ) -> None:
        selected = self.strategy.select(
            [
                self.basic,
                self.advanced,
            ],
            ProviderRequirements(),
        )

        self.assertIs(
            selected,
            self.basic,
        )

    def test_selects_provider_supporting_requested_model(
        self,
    ) -> None:
        selected = self.strategy.select(
            [
                self.basic,
                self.advanced,
            ],
            ProviderRequirements(model="advanced-model"),
        )

        self.assertIs(
            selected,
            self.advanced,
        )

    def test_model_matching_is_case_insensitive(
        self,
    ) -> None:
        selected = self.strategy.select(
            [
                self.advanced,
            ],
            ProviderRequirements(model=" ADVANCED-MODEL "),
        )

        self.assertIs(
            selected,
            self.advanced,
        )

    def test_selects_provider_supporting_all_flags(
        self,
    ) -> None:
        selected = self.strategy.select(
            [
                self.basic,
                self.advanced,
            ],
            ProviderRequirements(
                requires_streaming=True,
                requires_tools=True,
                requires_structured_output=True,
                requires_image_input=True,
                requires_document_input=True,
            ),
        )

        self.assertIs(
            selected,
            self.advanced,
        )

    def test_rejects_provider_missing_one_requirement(
        self,
    ) -> None:
        compatible = self.strategy.is_compatible(
            self.alternative,
            ProviderRequirements(
                requires_streaming=True,
                requires_tools=True,
                requires_structured_output=True,
            ),
        )

        self.assertFalse(compatible)

    def test_selects_provider_with_sufficient_context(
        self,
    ) -> None:
        selected = self.strategy.select(
            [
                self.basic,
                self.advanced,
            ],
            ProviderRequirements(minimum_context_tokens=32_000),
        )

        self.assertIs(
            selected,
            self.advanced,
        )

    def test_unknown_context_capacity_is_not_compatible(
        self,
    ) -> None:
        provider = NamedMockProvider(
            "unknown-context",
            ProviderCapabilities(),
        )

        compatible = self.strategy.is_compatible(
            provider,
            ProviderRequirements(minimum_context_tokens=1),
        )

        self.assertFalse(compatible)

    def test_returns_all_compatible_providers_in_input_order(
        self,
    ) -> None:
        compatible = self.strategy.compatible_providers(
            [
                self.basic,
                self.advanced,
                self.alternative,
            ],
            ProviderRequirements(requires_streaming=True),
        )

        self.assertEqual(
            compatible,
            [
                self.advanced,
                self.alternative,
            ],
        )

    def test_selection_is_deterministic(
        self,
    ) -> None:
        requirements = ProviderRequirements(
            model="shared-model",
            requires_streaming=True,
        )

        first_result = self.strategy.select(
            [
                self.advanced,
                self.alternative,
            ],
            requirements,
        )
        second_result = self.strategy.select(
            [
                self.advanced,
                self.alternative,
            ],
            requirements,
        )

        self.assertIs(
            first_result,
            self.advanced,
        )
        self.assertIs(
            second_result,
            self.advanced,
        )

    def test_missing_compatible_provider_raises(
        self,
    ) -> None:
        with self.assertRaisesRegex(
            LookupError,
            "No compatible",
        ):
            self.strategy.select(
                [
                    self.basic,
                ],
                ProviderRequirements(requires_tools=True),
            )

    def test_empty_provider_sequence_raises(
        self,
    ) -> None:
        with self.assertRaisesRegex(
            LookupError,
            "No compatible",
        ):
            self.strategy.select(
                [],
                ProviderRequirements(),
            )

    def test_rejects_invalid_provider_sequence(
        self,
    ) -> None:
        with self.assertRaisesRegex(
            TypeError,
            "sequence",
        ):
            self.strategy.select(
                "invalid",  # type: ignore[arg-type]
                ProviderRequirements(),
            )

    def test_rejects_invalid_provider_member(
        self,
    ) -> None:
        invalid_provider = cast(
            IntelligenceProvider,
            object(),
        )

        with self.assertRaisesRegex(
            TypeError,
            "IntelligenceProvider",
        ):
            self.strategy.select(
                [
                    self.basic,
                    invalid_provider,
                ],
                ProviderRequirements(requires_tools=True),
            )

    def test_rejects_invalid_requirements(
        self,
    ) -> None:
        invalid_requirements = cast(
            ProviderRequirements,
            object(),
        )

        with self.assertRaisesRegex(
            TypeError,
            "ProviderRequirements",
        ):
            self.strategy.select(
                [
                    self.basic,
                ],
                invalid_requirements,
            )

    def test_is_compatible_rejects_invalid_provider(
        self,
    ) -> None:
        invalid_provider = cast(
            IntelligenceProvider,
            object(),
        )

        with self.assertRaisesRegex(
            TypeError,
            "IntelligenceProvider",
        ):
            self.strategy.is_compatible(
                invalid_provider,
                ProviderRequirements(),
            )


if __name__ == "__main__":
    unittest.main()
