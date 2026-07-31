"""Provider contract for AI intelligence services."""

from __future__ import annotations

from abc import ABC, abstractmethod

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

    @abstractmethod
    def generate(
        self,
        request: IntelligenceRequest,
    ) -> IntelligenceResponse:
        """Generate an AI response."""
