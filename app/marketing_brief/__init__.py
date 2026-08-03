"""Structured Marketing Brief domain."""

from app.marketing_brief.models import (
    BriefStatus,
    MarketingBrief,
    MarketingBriefEvidence,
)
from app.marketing_brief.prompt_builder import (
    MarketingBriefPromptBuilder,
)

__all__ = [
    "BriefStatus",
    "MarketingBrief",
    "MarketingBriefEvidence",
    "MarketingBriefPromptBuilder",
]
