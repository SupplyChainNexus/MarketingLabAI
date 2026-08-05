"""Governed differentiation and proof selection."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum

from app.positioning_intelligence.models import PositioningDecision
from app.positioning_intelligence.relevance import (
    TargetProductRelevance,
    normalized_terms,
)
from app.product_intelligence import ProductIntelligenceRepository


def _required(value: str, name: str) -> str:
    if not isinstance(value, str):
        raise TypeError(f"{name} must be a string.")
    value = value.strip()
    if not value:
        raise ValueError(f"{name} is required.")
    return value


class EvidenceReviewStatus(StrEnum):
    UNREVIEWED = "unreviewed"
    VERIFIED = "verified"
    REJECTED = "rejected"


@dataclass(frozen=True, slots=True)
class AlternativeEvidence:
    alternative: str
    statement: str
    source: str
    status: EvidenceReviewStatus = EvidenceReviewStatus.UNREVIEWED
    observed_at: str = ""

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "alternative",
            _required(self.alternative, "alternative"),
        )
        object.__setattr__(self, "statement", _required(self.statement, "statement"))
        object.__setattr__(self, "source", _required(self.source, "source"))
        object.__setattr__(self, "status", EvidenceReviewStatus(self.status))
        if not isinstance(self.observed_at, str):
            raise TypeError("observed_at must be a string.")
        object.__setattr__(self, "observed_at", self.observed_at.strip())
        if self.status is EvidenceReviewStatus.VERIFIED and not self.observed_at:
            raise ValueError("verified alternative evidence requires observed_at.")


@dataclass(frozen=True, slots=True)
class DifferentiationSelection:
    statement: str
    product_support: tuple[str, ...]
    proof_points: tuple[str, ...]
    alternative_evidence: tuple[AlternativeEvidence, ...]
    provenance: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class DifferentiationGap:
    code: str
    statement: str
    explanation: str


@dataclass(frozen=True, slots=True)
class DifferentiationReport:
    positioning_id: str
    positioning_version: int
    selections: tuple[DifferentiationSelection, ...] = field(default_factory=tuple)
    gaps: tuple[DifferentiationGap, ...] = field(default_factory=tuple)


class DifferentiationProofEvaluator:
    """Select only traceable differentiation and proof."""

    def __init__(self, products: ProductIntelligenceRepository) -> None:
        if not isinstance(products, ProductIntelligenceRepository):
            raise TypeError("products must be a ProductIntelligenceRepository.")
        self.products = products

    def evaluate(
        self,
        decision: PositioningDecision,
        relevance: TargetProductRelevance,
        alternatives: tuple[AlternativeEvidence, ...] = (),
    ) -> DifferentiationReport:
        if not isinstance(decision, PositioningDecision):
            raise TypeError("decision must be a PositioningDecision.")
        if not isinstance(relevance, TargetProductRelevance):
            raise TypeError("relevance must be a TargetProductRelevance.")
        if (
            relevance.positioning_id != decision.positioning_id
            or relevance.positioning_version != decision.version
        ):
            raise ValueError("relevance belongs to another positioning version.")
        if not isinstance(alternatives, tuple) or any(
            not isinstance(item, AlternativeEvidence) for item in alternatives
        ):
            raise TypeError("alternatives must contain AlternativeEvidence objects.")

        profile = self.products.get(
            tenant_id=decision.tenant_id,
            brand_id=decision.brand_id,
        )
        product = next(
            (
                item
                for item in profile.products
                if item.product_id == decision.product_id
            ),
            None,
        )
        if product is None:
            raise ValueError(
                "Positioning product does not exist in Product Intelligence."
            )

        support = product.features + product.benefits
        prohibited = {_normal(item) for item in relevance.prohibited_claims}
        declared_alternatives = {_normal(item) for item in decision.alternatives}
        verified_alternatives = tuple(
            item
            for item in alternatives
            if item.status is EvidenceReviewStatus.VERIFIED
            and _normal(item.alternative) in declared_alternatives
        )
        selections: list[DifferentiationSelection] = []
        gaps: list[DifferentiationGap] = []
        for statement in decision.differentiators:
            normalized = _normal(statement)
            if any(
                normalized == claim or normalized in claim or claim in normalized
                for claim in prohibited
            ):
                gaps.append(
                    DifferentiationGap(
                        "prohibited_claim",
                        statement,
                        "The claim conflicts with a prohibited claim boundary.",
                    )
                )
                continue
            statement_terms = normalized_terms(statement)
            product_support = tuple(
                item for item in support if normalized_terms(item) & statement_terms
            )
            if not product_support:
                gaps.append(
                    DifferentiationGap(
                        "product_support_missing",
                        statement,
                        "No recorded feature or benefit supports the claim.",
                    )
                )
                continue
            supported_terms = statement_terms.copy()
            for value in product_support:
                supported_terms.update(normalized_terms(value))
            proof = tuple(
                item
                for item in product.proof_points
                if normalized_terms(item) & supported_terms
            )
            if not proof:
                gaps.append(
                    DifferentiationGap(
                        "proof_missing",
                        statement,
                        "No recorded proof point supports the claim.",
                    )
                )
                continue
            alternative_support = tuple(
                item
                for item in verified_alternatives
                if normalized_terms(item.statement) & statement_terms
            )
            if decision.alternatives and not alternative_support:
                gaps.append(
                    DifferentiationGap(
                        "alternative_evidence_missing",
                        statement,
                        "No reviewed evidence for a declared alternative supports "
                        "a comparative distinction.",
                    )
                )
                continue
            sources = tuple(
                dict.fromkeys(
                    [item.source for item in product.evidence]
                    + [item.source for item in alternative_support]
                )
            )
            selections.append(
                DifferentiationSelection(
                    statement,
                    product_support,
                    proof,
                    alternative_support,
                    sources,
                )
            )
        if not decision.differentiators:
            gaps.append(
                DifferentiationGap(
                    "differentiators_missing",
                    "",
                    "No proposed differentiators were recorded.",
                )
            )
        return DifferentiationReport(
            decision.positioning_id,
            decision.version,
            tuple(selections),
            tuple(gaps),
        )


def _normal(value: str) -> str:
    return " ".join(value.lower().split())
