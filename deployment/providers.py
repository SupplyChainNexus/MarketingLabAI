"""Production provider-registry factory used by the hosted runtime."""

from __future__ import annotations

from app.ai.bootstrap import gemini_provider_bootstrap
from app.ai.registry import IntelligenceProviderRegistry


def create_registry(_configuration) -> IntelligenceProviderRegistry:
    """Build the configured Gemini registry without weakening provider contracts."""

    return gemini_provider_bootstrap().build_registry()
