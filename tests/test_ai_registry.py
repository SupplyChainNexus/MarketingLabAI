"""Tests for the AI provider registry."""

from __future__ import annotations

import unittest
from typing import cast

from app.ai.capabilities import ProviderCapabilities
from app.ai.models import IntelligenceRequest
from app.ai.providers.mock import MockIntelligenceProvider
from app.ai.registry import IntelligenceProviderRegistry
from app.ai.requirements import ProviderRequirements
from app.ai.selection import ProviderSelectionStrategy


class NamedMockProvider(MockIntelligenceProvider):
    """Mock provider with configurable identity and capabilities."""

    def __init__(
        self,
        provider_name: str,
        response_content: str,
        *,
        capabilities: ProviderCapabilities | None = None,
    ) -> None:
        super().__init__(
            response_content=response_content,
            model=f"{provider_name}-model",
            capabilities=capabilities,
        )
        self._provider_name = provider_name

    @property
    def provider_name(self) -> str:
        return self._provider_name


class IntelligenceProviderRegistryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.registry = IntelligenceProviderRegistry()

        self.first = NamedMockProvider(
            "first",
            "First response",
            capabilities=ProviderCapabilities(
                maximum_context_tokens=8_000,
                available_models=[
                    "first-model",
                ],
            ),
        )

        self.second = NamedMockProvider(
            "second",
            "Second response",
            capabilities=ProviderCapabilities(
                supports_streaming=True,
                supports_tools=True,
                supports_structured_output=True,
                maximum_context_tokens=128_000,
                available_models=[
                    "second-model",
                ],
            ),
        )

    def test_registry_uses_default_selection_strategy(
        self,
    ) -> None:
        self.assertIsInstance(
            self.registry.selection_strategy,
            ProviderSelectionStrategy,
        )

    def test_registry_accepts_custom_selection_strategy(
        self,
    ) -> None:
        strategy = ProviderSelectionStrategy()

        registry = IntelligenceProviderRegistry(strategy)

        self.assertIs(
            registry.selection_strategy,
            strategy,
        )

    def test_registry_rejects_invalid_selection_strategy(
        self,
    ) -> None:
        invalid_strategy = cast(
            ProviderSelectionStrategy,
            object(),
        )

        with self.assertRaisesRegex(
            TypeError,
            "ProviderSelectionStrategy",
        ):
            IntelligenceProviderRegistry(invalid_strategy)

    def test_first_provider_becomes_active(
        self,
    ) -> None:
        self.registry.register(self.first)

        self.assertEqual(
            self.registry.active_provider_name,
            "first",
        )
        self.assertIs(
            self.registry.active_provider(),
            self.first,
        )

    def test_register_can_make_provider_active(
        self,
    ) -> None:
        self.registry.register(self.first)
        self.registry.register(
            self.second,
            make_active=True,
        )

        self.assertEqual(
            self.registry.active_provider_name,
            "second",
        )

    def test_duplicate_provider_is_rejected(
        self,
    ) -> None:
        self.registry.register(self.first)

        with self.assertRaisesRegex(
            ValueError,
            "already registered",
        ):
            self.registry.register(self.first)

    def test_provider_can_be_replaced(
        self,
    ) -> None:
        self.registry.register(self.first)

        replacement = NamedMockProvider(
            "first",
            "Replacement response",
        )

        self.registry.register(
            replacement,
            replace=True,
        )

        self.assertIs(
            self.registry.get("first"),
            replacement,
        )

    def test_set_active_selects_registered_provider(
        self,
    ) -> None:
        self.registry.register(self.first)
        self.registry.register(self.second)

        self.registry.set_active("second")

        self.assertIs(
            self.registry.active_provider(),
            self.second,
        )

    def test_unknown_provider_cannot_be_selected(
        self,
    ) -> None:
        with self.assertRaisesRegex(
            KeyError,
            "not registered",
        ):
            self.registry.set_active("missing")

    def test_empty_registry_has_no_active_provider(
        self,
    ) -> None:
        with self.assertRaisesRegex(
            RuntimeError,
            "No active",
        ):
            self.registry.active_provider()

    def test_unregister_returns_provider(
        self,
    ) -> None:
        self.registry.register(self.first)

        removed = self.registry.unregister("first")

        self.assertIs(
            removed,
            self.first,
        )
        self.assertFalse(self.registry.contains("first"))
        self.assertIsNone(self.registry.active_provider_name)

    def test_unregister_active_provider_selects_next(
        self,
    ) -> None:
        self.registry.register(self.first)
        self.registry.register(self.second)

        self.registry.unregister("first")

        self.assertEqual(
            self.registry.active_provider_name,
            "second",
        )

    def test_list_names_is_sorted(self) -> None:
        self.registry.register(self.second)
        self.registry.register(self.first)

        self.assertEqual(
            self.registry.list_names(),
            [
                "first",
                "second",
            ],
        )
        self.assertEqual(
            self.registry.count(),
            2,
        )

    def test_select_uses_provider_requirements(
        self,
    ) -> None:
        self.registry.register(self.first)
        self.registry.register(self.second)

        selected = self.registry.select(ProviderRequirements(requires_tools=True))

        self.assertIs(
            selected,
            self.second,
        )

    def test_select_raises_when_no_provider_matches(
        self,
    ) -> None:
        self.registry.register(self.first)

        with self.assertRaisesRegex(
            LookupError,
            "No compatible",
        ):
            self.registry.select(ProviderRequirements(requires_tools=True))

    def test_select_rejects_invalid_requirements(
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
            self.registry.select(invalid_requirements)

    def test_compatible_providers_returns_matches(
        self,
    ) -> None:
        third = NamedMockProvider(
            "third",
            "Third response",
            capabilities=ProviderCapabilities(
                supports_tools=True,
                available_models=[
                    "third-model",
                ],
            ),
        )

        self.registry.register(self.first)
        self.registry.register(self.second)
        self.registry.register(third)

        compatible = self.registry.compatible_providers(
            ProviderRequirements(requires_tools=True)
        )

        self.assertEqual(
            compatible,
            [
                self.second,
                third,
            ],
        )

    def test_generate_uses_active_provider(
        self,
    ) -> None:
        self.registry.register(self.first)

        response = self.registry.generate(IntelligenceRequest(prompt="Generate"))

        self.assertEqual(
            response.content,
            "First response",
        )
        self.assertEqual(
            len(self.first.requests),
            1,
        )

    def test_generate_can_override_active_provider(
        self,
    ) -> None:
        self.registry.register(self.first)
        self.registry.register(self.second)

        response = self.registry.generate(
            IntelligenceRequest(prompt="Generate"),
            provider_name="second",
        )

        self.assertEqual(
            response.content,
            "Second response",
        )
        self.assertEqual(
            len(self.first.requests),
            0,
        )
        self.assertEqual(
            len(self.second.requests),
            1,
        )

    def test_generate_can_select_by_requirements(
        self,
    ) -> None:
        self.registry.register(self.first)
        self.registry.register(self.second)

        response = self.registry.generate(
            IntelligenceRequest(prompt="Generate"),
            requirements=ProviderRequirements(requires_streaming=True),
        )

        self.assertEqual(
            response.content,
            "Second response",
        )
        self.assertEqual(
            len(self.first.requests),
            0,
        )
        self.assertEqual(
            len(self.second.requests),
            1,
        )

    def test_explicit_provider_takes_precedence_over_requirements(
        self,
    ) -> None:
        self.registry.register(self.first)
        self.registry.register(self.second)

        response = self.registry.generate(
            IntelligenceRequest(prompt="Generate"),
            provider_name="first",
            requirements=ProviderRequirements(requires_tools=True),
        )

        self.assertEqual(
            response.content,
            "First response",
        )
        self.assertEqual(
            len(self.first.requests),
            1,
        )
        self.assertEqual(
            len(self.second.requests),
            0,
        )

    def test_generate_rejects_invalid_request(
        self,
    ) -> None:
        self.registry.register(self.first)

        with self.assertRaisesRegex(
            TypeError,
            "IntelligenceRequest",
        ):
            self.registry.generate("invalid")  # type: ignore[arg-type]

    def test_generate_rejects_invalid_requirements(
        self,
    ) -> None:
        self.registry.register(self.first)

        invalid_requirements = cast(
            ProviderRequirements,
            object(),
        )

        with self.assertRaisesRegex(
            TypeError,
            "ProviderRequirements",
        ):
            self.registry.generate(
                IntelligenceRequest(prompt="Generate"),
                requirements=invalid_requirements,
            )

    def test_register_rejects_invalid_object(
        self,
    ) -> None:
        with self.assertRaisesRegex(
            TypeError,
            "IntelligenceProvider",
        ):
            self.registry.register(object())  # type: ignore[arg-type]


if __name__ == "__main__":
    unittest.main()
