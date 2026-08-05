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
from app.positioning_intelligence.value_proposition import (
    CandidateStatus,
    ValuePropositionBuilder,
    ValuePropositionCandidate,
    ValuePropositionGap,
)

__all__ = [
    "AlternativeEvidence",
    "CandidateStatus",
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
    "ValuePropositionBuilder",
    "ValuePropositionCandidate",
    "ValuePropositionGap",
    "normalized_terms",
]
