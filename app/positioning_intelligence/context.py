"""Provider-neutral rendering of approved Positioning Intelligence."""

from __future__ import annotations

from app.positioning_intelligence.models import PositioningDecision, PositioningStatus
from app.positioning_intelligence.repository import PositioningRepository


class PositioningContextProvider:
    """Resolve and render one current approved positioning version."""

    def __init__(self, repository: PositioningRepository) -> None:
        if not isinstance(repository, PositioningRepository):
            raise TypeError("repository must be a PositioningRepository.")
        self.repository = repository

    def resolve(
        self,
        *,
        tenant_id: str,
        brand_id: str,
        positioning_id: str,
        positioning_version: int,
    ) -> PositioningDecision:
        decision = self.repository.get(
            tenant_id=tenant_id,
            positioning_id=positioning_id,
            version=positioning_version,
        )
        latest = self.repository.latest(
            tenant_id=tenant_id,
            positioning_id=positioning_id,
        )
        if decision.brand_id != brand_id:
            raise ValueError("Positioning and requested brand differ.")
        if latest.version != decision.version:
            raise ValueError("Positioning reference is stale.")
        if decision.status is not PositioningStatus.APPROVED:
            raise ValueError("Positioning reference is not currently approved.")
        return decision

    def build(self, **reference: object) -> str:
        decision = self.resolve(**reference)
        evidence = [item for item in decision.evidence if item.verified]
        lines = [
            "APPROVED POSITIONING — HUMAN REVIEWED",
            f"Positioning reference: {decision.positioning_id} v{decision.version}",
            f"Target: {decision.target_kind.value}:{decision.target_id}",
            f"Product: {decision.product_id}",
            f"Value proposition: {decision.value_proposition}",
        ]
        if decision.offer_id:
            lines.append(f"Offer: {decision.offer_id}")
        if decision.differentiators:
            lines.append("Differentiators: " + "; ".join(decision.differentiators))
        if decision.proof_points:
            lines.append("Proof: " + "; ".join(decision.proof_points))
        if evidence:
            lines.append(
                "Verified evidence: "
                + "; ".join(f"{item.source}: {item.summary}" for item in evidence)
            )
        limitations = list(decision.assumptions) + [
            f"{item.field_name}: {item.reason}" for item in decision.unknowns
        ]
        if limitations:
            lines.append("Limitations and unknowns: " + "; ".join(limitations))
        return "\n".join(lines)
