"""Evidence-grounded value proposition candidate building."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum

from app.positioning_intelligence.differentiation import DifferentiationReport
from app.positioning_intelligence.models import PositioningDecision
from app.positioning_intelligence.relevance import TargetProductRelevance


class CandidateStatus(StrEnum):
    INCOMPLETE = "incomplete"
    READY_FOR_REVIEW = "ready_for_review"


@dataclass(frozen=True, slots=True)
class ValuePropositionGap:
    code: str
    explanation: str


@dataclass(frozen=True, slots=True)
class ValuePropositionCandidate:
    positioning_id: str
    positioning_version: int
    statement: str
    offer_framing: str
    status: CandidateStatus
    confidence: float
    confidence_basis: str
    limitations: tuple[str, ...] = field(default_factory=tuple)
    prohibited_claims: tuple[str, ...] = field(default_factory=tuple)
    provenance: tuple[str, ...] = field(default_factory=tuple)
    gaps: tuple[ValuePropositionGap, ...] = field(default_factory=tuple)

    @property
    def is_ready(self) -> bool:
        return self.status is CandidateStatus.READY_FOR_REVIEW


class ValuePropositionBuilder:
    """Build a review candidate without granting positioning approval."""

    def build(
        self,
        decision: PositioningDecision,
        relevance: TargetProductRelevance,
        differentiation: DifferentiationReport,
    ) -> ValuePropositionCandidate:
        if not isinstance(decision, PositioningDecision):
            raise TypeError("decision must be a PositioningDecision.")
        if not isinstance(relevance, TargetProductRelevance):
            raise TypeError("relevance must be a TargetProductRelevance.")
        if not isinstance(differentiation, DifferentiationReport):
            raise TypeError("differentiation must be a DifferentiationReport.")
        identity = (decision.positioning_id, decision.version)
        if identity != (
            relevance.positioning_id,
            relevance.positioning_version,
        ) or identity != (
            differentiation.positioning_id,
            differentiation.positioning_version,
        ):
            raise ValueError(
                "candidate inputs belong to different positioning versions."
            )

        gaps: list[ValuePropositionGap] = []
        if not relevance.matches:
            gaps.append(
                ValuePropositionGap(
                    "relevance_missing",
                    "No supported target-product relevance is available.",
                )
            )
        if not differentiation.selections:
            gaps.append(
                ValuePropositionGap(
                    "differentiation_missing",
                    "No governed differentiator and proof selection is available.",
                )
            )
        verified = tuple(item for item in decision.evidence if item.verified)
        if not verified:
            gaps.append(
                ValuePropositionGap(
                    "verified_evidence_missing",
                    "No verified positioning evidence is recorded.",
                )
            )
        gaps.extend(
            ValuePropositionGap(item.code, item.explanation)
            for item in differentiation.gaps
        )
        status = (
            CandidateStatus.READY_FOR_REVIEW if not gaps else CandidateStatus.INCOMPLETE
        )
        confidence = min((item.confidence for item in verified), default=0.0)
        confidence_basis = (
            "Minimum confidence across verified positioning evidence."
            if verified
            else "No verified positioning evidence."
        )
        statement = ""
        offer_framing = ""
        provenance: tuple[str, ...] = ()
        if status is CandidateStatus.READY_FOR_REVIEW:
            match = relevance.matches[0]
            selection = differentiation.selections[0]
            statement = (
                f"For {relevance.target_name}, {relevance.product_name} "
                f"supports {match.customer_statement.lower()} through "
                f"{selection.statement.lower()}."
            )
            if relevance.offer_name:
                offer_framing = (
                    f"{relevance.offer_name} is the selected offer for this "
                    "positioning candidate."
                )
            provenance = tuple(
                dict.fromkeys(
                    [item.source for item in verified] + list(selection.provenance)
                )
            )
        limitations = tuple(
            dict.fromkeys(
                list(relevance.limitations)
                + list(decision.assumptions)
                + [item.reason for item in decision.unknowns]
            )
        )
        return ValuePropositionCandidate(
            decision.positioning_id,
            decision.version,
            statement,
            offer_framing,
            status,
            confidence,
            confidence_basis,
            limitations,
            relevance.prohibited_claims,
            provenance,
            tuple(gaps),
        )
