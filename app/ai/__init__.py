"""Provider-neutral AI infrastructure."""

from app.ai.assembler import (
    AIContext,
    AIContextAssembler,
)
from app.ai.context import CompanyBrainPromptBuilder
from app.ai.memory import MemoryPromptBuilder
from app.ai.models import (
    IntelligenceRequest,
    IntelligenceResponse,
)
from app.ai.orchestrator import AIOrchestrator
from app.ai.prompt import (
    PromptComposer,
    PromptSection,
)
from app.ai.provider import IntelligenceProvider
from app.ai.providers.mock import MockIntelligenceProvider
from app.ai.registry import IntelligenceProviderRegistry

__all__ = [
    "AIContext",
    "AIContextAssembler",
    "AIOrchestrator",
    "CompanyBrainPromptBuilder",
    "IntelligenceProvider",
    "IntelligenceProviderRegistry",
    "IntelligenceRequest",
    "IntelligenceResponse",
    "MemoryPromptBuilder",
    "MockIntelligenceProvider",
    "PromptComposer",
    "PromptSection",
]
