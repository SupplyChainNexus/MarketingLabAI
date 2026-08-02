"""Tests for explicit AI provider bootstrap."""

from __future__ import annotations

import unittest
from dataclasses import dataclass
from typing import cast

from app.ai.bootstrap import (
    ProviderBootstrap,
    gemini_provider_bootstrap,
)
from app.ai.capabilities import ProviderCapabilities
from app.ai.orchestrator import AIOrchestrator
from app.ai.provider import IntelligenceProvider
from app.ai.providers.gemini import (
    GeminiIntelligenceProvider,
)
from app.ai.providers.mock import MockIntelligenceProvider
from app.ai.selection import ProviderSelectionStrategy


@dataclass
class FakeGeminiSettings:
    """Settings exposed by the fake Gemini client."""

    gemini_model: str = "gemini-test-model"


class FakeGeminiClient:
    """Low-level Gemini client used without live API access."""

    def __init__(self) -> None:
        self.settings = FakeGeminiSettings()
        self.prompts: list[str] = []

    def generate_text(
        self,
        prompt: str,
    ) -> str:
        self.prompts.append(prompt)
        return "Generated response"


class NamedMockProvider(MockIntelligenceProvider):
    """Mock provider with a configurable provider name."""

    def __init__(
        self,
        provider_name: str,
    ) -> None:
        super().__init__(
            model=f"{provider_name}-model",
            capabilities=ProviderCapabilities(
                available_models=[
                    f"{provider_name}-model",
                ]
            ),
        )
        self._provider_name = provider_name

    @property
    def provider_name(self) -> str:
        return self._provider_name


class ProviderBootstrapTests(unittest.TestCase):
    def test_build_registry_registers_factories_in_order(
        self,
    ) -> None:
        bootstrap = ProviderBootstrap(
            [
                lambda: NamedMockProvider("first"),
                lambda: NamedMockProvider("second"),
            ]
        )

        registry = bootstrap.build_registry()

        self.assertEqual(
            registry.list_names(),
            [
                "first",
                "second",
            ],
        )
        self.assertEqual(
            registry.active_provider_name,
            "first",
        )

    def test_configured_provider_becomes_active(
        self,
    ) -> None:
        bootstrap = ProviderBootstrap(
            [
                lambda: NamedMockProvider("first"),
                lambda: NamedMockProvider("second"),
            ],
            active_provider_name="second",
        )

        registry = bootstrap.build_registry()

        self.assertEqual(
            registry.active_provider_name,
            "second",
        )

    def test_build_registry_creates_new_instances(
        self,
    ) -> None:
        bootstrap = ProviderBootstrap(
            [
                lambda: NamedMockProvider("first"),
            ]
        )

        first_registry = bootstrap.build_registry()
        second_registry = bootstrap.build_registry()

        self.assertIsNot(
            first_registry,
            second_registry,
        )
        self.assertIsNot(
            first_registry.get("first"),
            second_registry.get("first"),
        )

    def test_factories_run_only_when_registry_is_built(
        self,
    ) -> None:
        calls: list[str] = []

        def factory() -> IntelligenceProvider:
            calls.append("called")
            return NamedMockProvider("first")

        bootstrap = ProviderBootstrap(
            [
                factory,
            ]
        )

        self.assertEqual(
            calls,
            [],
        )

        bootstrap.build_registry()

        self.assertEqual(
            calls,
            [
                "called",
            ],
        )

    def test_bootstrap_exposes_configuration(
        self,
    ) -> None:
        bootstrap = ProviderBootstrap(
            [
                lambda: NamedMockProvider("first"),
            ],
            active_provider_name="first",
        )

        self.assertEqual(
            bootstrap.provider_count,
            1,
        )
        self.assertEqual(
            bootstrap.active_provider_name,
            "first",
        )

    def test_accepts_custom_selection_strategy(
        self,
    ) -> None:
        strategy = ProviderSelectionStrategy()

        bootstrap = ProviderBootstrap(
            [
                lambda: NamedMockProvider("first"),
            ],
            selection_strategy=strategy,
        )

        registry = bootstrap.build_registry()

        self.assertIs(
            registry.selection_strategy,
            strategy,
        )

    def test_build_orchestrator_returns_configured_instance(
        self,
    ) -> None:
        bootstrap = ProviderBootstrap(
            [
                lambda: NamedMockProvider("first"),
            ]
        )

        orchestrator = bootstrap.build_orchestrator()

        self.assertIsInstance(
            orchestrator,
            AIOrchestrator,
        )
        self.assertTrue(orchestrator.registry.contains("first"))

    def test_default_gemini_bootstrap_registers_gemini(
        self,
    ) -> None:
        bootstrap = gemini_provider_bootstrap(FakeGeminiClient())

        registry = bootstrap.build_registry()
        provider = registry.get("gemini")

        self.assertIsInstance(
            provider,
            GeminiIntelligenceProvider,
        )
        self.assertEqual(
            registry.active_provider_name,
            "gemini",
        )
        self.assertTrue(provider.capabilities.supports_model("gemini-test-model"))

    def test_default_gemini_bootstrap_builds_orchestrator(
        self,
    ) -> None:
        bootstrap = gemini_provider_bootstrap(FakeGeminiClient())

        orchestrator = bootstrap.build_orchestrator()

        self.assertEqual(
            orchestrator.registry.active_provider_name,
            "gemini",
        )

    def test_rejects_invalid_factory_collection(
        self,
    ) -> None:
        with self.assertRaisesRegex(
            TypeError,
            "sequence",
        ):
            ProviderBootstrap("invalid")  # type: ignore[arg-type]

    def test_rejects_non_callable_factory(
        self,
    ) -> None:
        with self.assertRaisesRegex(
            TypeError,
            "callable",
        ):
            ProviderBootstrap(
                [
                    object(),  # type: ignore[list-item]
                ]
            )

    def test_rejects_blank_active_provider_name(
        self,
    ) -> None:
        with self.assertRaisesRegex(
            ValueError,
            "cannot be blank",
        ):
            ProviderBootstrap(
                [],
                active_provider_name=" ",
            )

    def test_rejects_invalid_active_provider_type(
        self,
    ) -> None:
        with self.assertRaisesRegex(
            TypeError,
            "active_provider_name",
        ):
            ProviderBootstrap(
                [],
                active_provider_name=(1),  # type: ignore[arg-type]
            )

    def test_rejects_invalid_selection_strategy(
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
            ProviderBootstrap(
                [],
                selection_strategy=invalid_strategy,
            )

    def test_rejects_factory_returning_invalid_object(
        self,
    ) -> None:
        def invalid_factory() -> IntelligenceProvider:
            return cast(
                IntelligenceProvider,
                object(),
            )

        bootstrap = ProviderBootstrap(
            [
                invalid_factory,
            ]
        )

        with self.assertRaisesRegex(
            TypeError,
            "must return",
        ):
            bootstrap.build_registry()

    def test_unknown_active_provider_is_rejected(
        self,
    ) -> None:
        bootstrap = ProviderBootstrap(
            [
                lambda: NamedMockProvider("first"),
            ],
            active_provider_name="missing",
        )

        with self.assertRaisesRegex(
            KeyError,
            "not registered",
        ):
            bootstrap.build_registry()

    def test_duplicate_provider_names_are_rejected(
        self,
    ) -> None:
        bootstrap = ProviderBootstrap(
            [
                lambda: NamedMockProvider("duplicate"),
                lambda: NamedMockProvider("duplicate"),
            ]
        )

        with self.assertRaisesRegex(
            ValueError,
            "already registered",
        ):
            bootstrap.build_registry()


if __name__ == "__main__":
    unittest.main()
