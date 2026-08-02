"""Deterministic capability-based AI provider selection."""

from __future__ import annotations

from collections.abc import Sequence

from app.ai.provider import IntelligenceProvider
from app.ai.requirements import ProviderRequirements


class ProviderSelectionStrategy:
    """Select the first provider satisfying all requirements."""

    def select(
        self,
        providers: Sequence[IntelligenceProvider],
        requirements: ProviderRequirements,
    ) -> IntelligenceProvider:
        """Return the first compatible provider."""

        if isinstance(
            providers,
            (str, bytes),
        ) or not isinstance(
            providers,
            Sequence,
        ):
            raise TypeError("providers must be a sequence.")

        if not isinstance(
            requirements,
            ProviderRequirements,
        ):
            raise TypeError("requirements must be a " "ProviderRequirements.")

        for provider in providers:
            if not isinstance(
                provider,
                IntelligenceProvider,
            ):
                raise TypeError(
                    "providers must contain only " "IntelligenceProvider instances."
                )

            if self.is_compatible(
                provider,
                requirements,
            ):
                return provider

        raise LookupError("No compatible intelligence provider " "was found.")

    def compatible_providers(
        self,
        providers: Sequence[IntelligenceProvider],
        requirements: ProviderRequirements,
    ) -> list[IntelligenceProvider]:
        """Return every provider satisfying the requirements."""

        if isinstance(
            providers,
            (str, bytes),
        ) or not isinstance(
            providers,
            Sequence,
        ):
            raise TypeError("providers must be a sequence.")

        if not isinstance(
            requirements,
            ProviderRequirements,
        ):
            raise TypeError("requirements must be a " "ProviderRequirements.")

        compatible: list[IntelligenceProvider] = []

        for provider in providers:
            if not isinstance(
                provider,
                IntelligenceProvider,
            ):
                raise TypeError(
                    "providers must contain only " "IntelligenceProvider instances."
                )

            if self.is_compatible(
                provider,
                requirements,
            ):
                compatible.append(provider)

        return compatible

    @staticmethod
    def is_compatible(
        provider: IntelligenceProvider,
        requirements: ProviderRequirements,
    ) -> bool:
        """Return whether a provider satisfies all requirements."""

        if not isinstance(
            provider,
            IntelligenceProvider,
        ):
            raise TypeError("provider must be an " "IntelligenceProvider.")

        if not isinstance(
            requirements,
            ProviderRequirements,
        ):
            raise TypeError("requirements must be a " "ProviderRequirements.")

        capabilities = provider.capabilities

        if requirements.model and not capabilities.supports_model(requirements.model):
            return False

        if requirements.requires_streaming and not capabilities.supports_streaming:
            return False

        if requirements.requires_tools and not capabilities.supports_tools:
            return False

        if (
            requirements.requires_structured_output
            and not capabilities.supports_structured_output
        ):
            return False

        if requirements.requires_image_input and not capabilities.supports_images:
            return False

        if requirements.requires_document_input and not capabilities.supports_documents:
            return False

        minimum_context_tokens = requirements.minimum_context_tokens

        if minimum_context_tokens is not None:
            maximum_context_tokens = capabilities.maximum_context_tokens

            if maximum_context_tokens is None:
                return False

            if maximum_context_tokens < minimum_context_tokens:
                return False

        return True
