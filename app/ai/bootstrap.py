"""Explicit composition root for AI provider infrastructure."""

from __future__ import annotations

from collections.abc import Callable, Sequence

from app.ai.assembler import AIContextAssembler
from app.ai.orchestrator import AIOrchestrator
from app.ai.provider import IntelligenceProvider
from app.ai.providers.gemini import (
    GeminiIntelligenceProvider,
    GeminiTextClient,
)
from app.ai.registry import IntelligenceProviderRegistry
from app.ai.selection import ProviderSelectionStrategy

ProviderFactory = Callable[[], IntelligenceProvider]


class ProviderBootstrap:
    """Construct and register configured intelligence providers."""

    def __init__(
        self,
        provider_factories: Sequence[ProviderFactory],
        *,
        active_provider_name: str | None = None,
        selection_strategy: ProviderSelectionStrategy | None = None,
    ) -> None:
        if isinstance(
            provider_factories,
            (str, bytes),
        ) or not isinstance(
            provider_factories,
            Sequence,
        ):
            raise TypeError("provider_factories must be a sequence.")

        validated_factories: list[ProviderFactory] = []

        for factory in provider_factories:
            if not callable(factory):
                raise TypeError(
                    "provider_factories must contain " "callable factories."
                )

            validated_factories.append(factory)

        if active_provider_name is not None:
            if not isinstance(
                active_provider_name,
                str,
            ):
                raise TypeError("active_provider_name must be " "a string or None.")

            active_provider_name = active_provider_name.strip()

            if not active_provider_name:
                raise ValueError("active_provider_name cannot be blank.")

        if selection_strategy is not None and not isinstance(
            selection_strategy,
            ProviderSelectionStrategy,
        ):
            raise TypeError(
                "selection_strategy must be a " "ProviderSelectionStrategy."
            )

        self._provider_factories = tuple(validated_factories)
        self._active_provider_name = active_provider_name
        self._selection_strategy = selection_strategy

    @property
    def active_provider_name(
        self,
    ) -> str | None:
        """Return the configured active-provider name."""

        return self._active_provider_name

    @property
    def provider_count(self) -> int:
        """Return the number of configured provider factories."""

        return len(self._provider_factories)

    def build_registry(
        self,
    ) -> IntelligenceProviderRegistry:
        """Construct providers and return a configured registry."""

        registry = IntelligenceProviderRegistry(self._selection_strategy)

        for factory in self._provider_factories:
            provider = factory()

            if not isinstance(
                provider,
                IntelligenceProvider,
            ):
                raise TypeError(
                    "Provider factory must return an " "IntelligenceProvider."
                )

            registry.register(provider)

        if self._active_provider_name is not None:
            registry.set_active(self._active_provider_name)

        return registry

    def build_orchestrator(
        self,
        *,
        context_assembler: AIContextAssembler | None = None,
    ) -> AIOrchestrator:
        """Return an orchestrator using a newly built registry."""

        if context_assembler is not None and not isinstance(
            context_assembler,
            AIContextAssembler,
        ):
            raise TypeError("context_assembler must be an " "AIContextAssembler.")

        return AIOrchestrator(
            self.build_registry(),
            context_assembler=context_assembler,
        )


def gemini_provider_bootstrap(
    client: GeminiTextClient | None = None,
) -> ProviderBootstrap:
    """Return the default Gemini provider composition root."""

    def create_gemini_provider() -> IntelligenceProvider:
        return GeminiIntelligenceProvider(client)

    return ProviderBootstrap(
        [
            create_gemini_provider,
        ],
        active_provider_name="gemini",
    )
