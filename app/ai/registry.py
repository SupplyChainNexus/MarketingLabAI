"""Registry for configured AI intelligence providers."""

from __future__ import annotations

from app.ai.models import (
    IntelligenceRequest,
    IntelligenceResponse,
)
from app.ai.provider import IntelligenceProvider
from app.ai.requirements import ProviderRequirements
from app.ai.selection import ProviderSelectionStrategy


class IntelligenceProviderRegistry:
    """Register, select, and use intelligence providers."""

    def __init__(
        self,
        selection_strategy: ProviderSelectionStrategy | None = None,
    ) -> None:
        if selection_strategy is not None and not isinstance(
            selection_strategy,
            ProviderSelectionStrategy,
        ):
            raise TypeError(
                "selection_strategy must be a " "ProviderSelectionStrategy."
            )

        self._providers: dict[
            str,
            IntelligenceProvider,
        ] = {}
        self._active_provider_name: str | None = None
        self._selection_strategy = (
            selection_strategy
            if selection_strategy is not None
            else ProviderSelectionStrategy()
        )

    @property
    def selection_strategy(
        self,
    ) -> ProviderSelectionStrategy:
        """Return the configured selection strategy."""

        return self._selection_strategy

    def register(
        self,
        provider: IntelligenceProvider,
        *,
        make_active: bool = False,
        replace: bool = False,
    ) -> None:
        """Register an intelligence provider."""

        if not isinstance(
            provider,
            IntelligenceProvider,
        ):
            raise TypeError("provider must implement " "IntelligenceProvider.")

        provider_name = provider.provider_name.strip()

        if not provider_name:
            raise ValueError("provider_name is required.")

        if provider_name in self._providers and not replace:
            raise ValueError(f"Provider '{provider_name}' " "is already registered.")

        self._providers[provider_name] = provider

        if make_active or self._active_provider_name is None:
            self._active_provider_name = provider_name

    def unregister(
        self,
        provider_name: str,
    ) -> IntelligenceProvider:
        """Remove and return a registered provider."""

        provider_name = provider_name.strip()

        if provider_name not in self._providers:
            raise KeyError(f"Provider '{provider_name}' " "is not registered.")

        provider = self._providers.pop(provider_name)

        if self._active_provider_name == provider_name:
            self._active_provider_name = next(
                iter(self._providers),
                None,
            )

        return provider

    def get(
        self,
        provider_name: str,
    ) -> IntelligenceProvider:
        """Return a registered provider by name."""

        provider_name = provider_name.strip()

        try:
            return self._providers[provider_name]
        except KeyError as error:
            raise KeyError(
                f"Provider '{provider_name}' " "is not registered."
            ) from error

    def set_active(
        self,
        provider_name: str,
    ) -> None:
        """Select the active provider."""

        provider_name = provider_name.strip()

        if provider_name not in self._providers:
            raise KeyError(f"Provider '{provider_name}' " "is not registered.")

        self._active_provider_name = provider_name

    def active_provider(
        self,
    ) -> IntelligenceProvider:
        """Return the currently active provider."""

        if self._active_provider_name is None:
            raise RuntimeError("No active intelligence provider " "is configured.")

        return self.get(self._active_provider_name)

    @property
    def active_provider_name(
        self,
    ) -> str | None:
        """Return the active provider name."""

        return self._active_provider_name

    def list_names(self) -> list[str]:
        """Return registered provider names in sorted order."""

        return sorted(self._providers)

    def contains(
        self,
        provider_name: str,
    ) -> bool:
        """Return whether a provider is registered."""

        return provider_name.strip() in self._providers

    def count(self) -> int:
        """Return the number of registered providers."""

        return len(self._providers)

    def select(
        self,
        requirements: ProviderRequirements,
    ) -> IntelligenceProvider:
        """Select the first compatible provider."""

        if not isinstance(
            requirements,
            ProviderRequirements,
        ):
            raise TypeError("requirements must be a " "ProviderRequirements.")

        return self._selection_strategy.select(
            list(self._providers.values()),
            requirements,
        )

    def compatible_providers(
        self,
        requirements: ProviderRequirements,
    ) -> list[IntelligenceProvider]:
        """Return all registered compatible providers."""

        if not isinstance(
            requirements,
            ProviderRequirements,
        ):
            raise TypeError("requirements must be a " "ProviderRequirements.")

        return self._selection_strategy.compatible_providers(
            list(self._providers.values()),
            requirements,
        )

    def generate(
        self,
        request: IntelligenceRequest,
        *,
        provider_name: str | None = None,
        requirements: ProviderRequirements | None = None,
    ) -> IntelligenceResponse:
        """Generate using explicit, selected, or active provider."""

        if not isinstance(
            request,
            IntelligenceRequest,
        ):
            raise TypeError("request must be an " "IntelligenceRequest.")

        if requirements is not None and not isinstance(
            requirements,
            ProviderRequirements,
        ):
            raise TypeError("requirements must be a " "ProviderRequirements.")

        if provider_name is not None:
            provider = self.get(provider_name)
        elif requirements is not None:
            provider = self.select(requirements)
        else:
            provider = self.active_provider()

        return provider.generate(request)
