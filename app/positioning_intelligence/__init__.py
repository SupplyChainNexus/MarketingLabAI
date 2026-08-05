"""Public Positioning Intelligence API."""

from app.positioning_intelligence.differentiation import (
    AlternativeEvidence,
    DifferentiationGap,
    DifferentiationProofEvaluator,
    DifferentiationReport,
    DifferentiationSelection,
    EvidenceReviewStatus,
)
from app.positioning_intelligence.models import (
    PositioningDecision,
    PositioningEvidence,
    PositioningStatus,
    PositioningUnknown,
    TargetKind,
)
from app.positioning_intelligence.relevance import (
    RelevanceGap,
    RelevanceMatch,
    TargetProductRelevance,
    TargetProductRelevanceEvaluator,
    normalized_terms,
)
from app.positioning_intelligence.repository import PositioningRepository
from app.positioning_intelligence.service import PositioningService

__all__ = [
    "AlternativeEvidence",
    "DifferentiationGap",
    "DifferentiationProofEvaluator",
    "DifferentiationReport",
    "DifferentiationSelection",
    "EvidenceReviewStatus",
    "PositioningDecision",
    "PositioningEvidence",
    "PositioningRepository",
    "PositioningService",
    "PositioningStatus",
    "PositioningUnknown",
    "RelevanceGap",
    "RelevanceMatch",
    "TargetKind",
    "TargetProductRelevance",
    "TargetProductRelevanceEvaluator",
    "normalized_terms",
]
