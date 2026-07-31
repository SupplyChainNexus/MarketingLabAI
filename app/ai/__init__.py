"""Provider-neutral AI infrastructure."""

from app.ai.models import (
    IntelligenceRequest,
    IntelligenceResponse,
)
from app.ai.provider import IntelligenceProvider
from app.ai.providers.mock import MockIntelligenceProvider
from app.ai.registry import IntelligenceProviderRegistry

__all__ = [
    "IntelligenceProvider",
    "IntelligenceProviderRegistry",
    "IntelligenceRequest",
    "IntelligenceResponse",
    "MockIntelligenceProvider",
]
