"""Deterministic target-product relevance evaluation."""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from app.customer_intelligence.models import CustomerIntelligenceProfile
from app.database.repositories import CustomerIntelligenceRepository
from app.positioning_intelligence.models import PositioningDecision, TargetKind
from app.product_intelligence.models import ProductIntelligenceProfile, ProductRecord
from app.product_intelligence.repository import ProductIntelligenceRepository

_IGNORED_WORDS = {
    "a",
    "an",
    "and",
    "are",
    "for",
    "from",
    "in",
    "of",
    "on",
    "or",
    "the",
    "their",
    "to",
    "with",
}


def normalized_terms(value: str) -> set[str]:
    return {
        term
        for term in re.findall(r"[a-z0-9]+", value.casefold())
        if len(term) > 2 and term not in _IGNORED_WORDS
    }


@dataclass(frozen=True, slots=True)
class RelevanceMatch:
    customer_statement: str
    product_statement: str
    shared_terms: tuple[str, ...]
    explanation: str


@dataclass(frozen=True, slots=True)
class RelevanceGap:
    code: str
    explanation: str


@dataclass(frozen=True, slots=True)
class TargetProductRelevance:
    positioning_id: str
    positioning_version: int
    target_name: str
    product_name: str
    offer_name: str = ""
    matches: tuple[RelevanceMatch, ...] = field(default_factory=tuple)
    gaps: tuple[RelevanceGap, ...] = field(default_factory=tuple)
    limitations: tuple[str, ...] = field(default_factory=tuple)
    prohibited_claims: tuple[str, ...] = field(default_factory=tuple)

    @property
    def has_supported_relevance(self) -> bool:
        return bool(self.matches)


class TargetProductRelevanceEvaluator:
    """Resolve governed references and explain lexical evidence intersections."""

    def __init__(
        self,
        customers: CustomerIntelligenceRepository,
        products: ProductIntelligenceRepository,
    ) -> None:
        if not isinstance(customers, CustomerIntelligenceRepository):
            raise TypeError("customers must be a CustomerIntelligenceRepository.")
        if not isinstance(products, ProductIntelligenceRepository):
            raise TypeError("products must be a ProductIntelligenceRepository.")
        self.customers = customers
        self.products = products

    def evaluate(self, decision: PositioningDecision) -> TargetProductRelevance:
        if not isinstance(decision, PositioningDecision):
            raise TypeError("decision must be a PositioningDecision.")
        customer_profile = self.customers.get(decision.brand_id)
        product_profile = self.products.get(
            tenant_id=decision.tenant_id,
            brand_id=decision.brand_id,
        )
        target_name, customer_statements = self._resolve_target(
            customer_profile, decision
        )
        product = self._resolve_product(product_profile, decision.product_id)
        offer_name, offer_limitations, offer_claims = self._resolve_offer(
            product, decision.offer_id
        )
        product_statements = product.features + product.benefits
        matches = self._matches(customer_statements, product_statements)
        gaps: list[RelevanceGap] = []
        if not customer_statements:
            gaps.append(
                RelevanceGap(
                    "target_context_missing",
                    "The target has no needs or outcomes.",
                )
            )
        if not product_statements:
            gaps.append(
                RelevanceGap(
                    "product_value_missing",
                    "The product has no features or benefits.",
                )
            )
        if customer_statements and product_statements and not matches:
            gaps.append(
                RelevanceGap(
                    "no_supported_intersection",
                    "No explicit wording intersection supports relevance.",
                )
            )
        if not product.proof_points:
            gaps.append(
                RelevanceGap(
                    "proof_missing",
                    "The product has no recorded proof points.",
                )
            )
        gaps.append(
            RelevanceGap(
                "use_cases_unmodelled",
                "Product use cases are not yet a governed field.",
            )
        )
        return TargetProductRelevance(
            positioning_id=decision.positioning_id,
            positioning_version=decision.version,
            target_name=target_name,
            product_name=product.name,
            offer_name=offer_name,
            matches=tuple(matches),
            gaps=tuple(gaps),
            limitations=tuple(product.limitations + offer_limitations),
            prohibited_claims=tuple(product.prohibited_claims + offer_claims),
        )

    @staticmethod
    def _resolve_target(
        profile: CustomerIntelligenceProfile,
        decision: PositioningDecision,
    ) -> tuple[str, list[str]]:
        if decision.target_kind is TargetKind.SEGMENT:
            candidates = profile.segments
            id_name = "segment_id"
            fields = ("description", "characteristics")
        elif decision.target_kind is TargetKind.PERSONA:
            candidates = profile.personas
            id_name = "persona_id"
            fields = ("pain_points", "desired_outcomes", "decision_criteria")
        else:
            candidates = profile.ideal_customer_profiles
            id_name = "icp_id"
            fields = ("description", "needs", "buying_criteria")
        target = next(
            (
                item
                for item in candidates
                if getattr(item, id_name) == decision.target_id
            ),
            None,
        )
        if target is None:
            raise ValueError(
                "Positioning target does not exist in Customer Intelligence."
            )
        statements: list[str] = []
        for field_name in fields:
            value = getattr(target, field_name)
            values = value if isinstance(value, list) else [value]
            statements.extend(item for item in values if item)
        return target.name, statements

    @staticmethod
    def _resolve_product(
        profile: ProductIntelligenceProfile, product_id: str
    ) -> ProductRecord:
        product = next(
            (item for item in profile.products if item.product_id == product_id),
            None,
        )
        if product is None:
            raise ValueError(
                "Positioning product does not exist in Product Intelligence."
            )
        return product

    @staticmethod
    def _resolve_offer(
        product: ProductRecord, offer_id: str
    ) -> tuple[str, list[str], list[str]]:
        if not offer_id:
            return "", [], []
        offer = next(
            (item for item in product.offers if item.offer_id == offer_id),
            None,
        )
        if offer is None:
            raise ValueError(
                "Positioning offer does not exist on the selected product."
            )
        return offer.name, offer.limitations, offer.prohibited_claims

    @staticmethod
    def _matches(
        customer_statements: list[str], product_statements: list[str]
    ) -> list[RelevanceMatch]:
        matches: list[RelevanceMatch] = []
        for customer in customer_statements:
            for product in product_statements:
                shared = tuple(
                    sorted(normalized_terms(customer) & normalized_terms(product))
                )
                if shared:
                    matches.append(
                        RelevanceMatch(
                            customer,
                            product,
                            shared,
                            "Shared recorded terms: " + ", ".join(shared),
                        )
                    )
        return matches
