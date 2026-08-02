"""Provider contract for AI intelligence services."""

from __future__ import annotations

from abc import ABC, abstractmethod

from app.ai.capabilities import ProviderCapabilities
from app.ai.models import (
    IntelligenceRequest,
    IntelligenceResponse,
)


class IntelligenceProvider(ABC):
    """Abstract interface implemented by every AI provider."""

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Return the stable provider identifier."""

    @property
    @abstractmethod
    def capabilities(self) -> ProviderCapabilities:
        """Return the provider's declared capabilities."""

    @abstractmethod
    def generate(
        self,
        request: IntelligenceRequest,
    ) -> IntelligenceResponse:
        """Generate an AI response."""
