"""Provider-neutral rendering of approved Strategy Intelligence."""

from __future__ import annotations

from app.strategy_intelligence.models import StrategyDecision, StrategyStatus
from app.strategy_intelligence.repository import StrategyRepository


class StrategyContextProvider:
    """Resolve and render one current approved strategy version."""

    def __init__(self, repository: StrategyRepository) -> None:
        if not isinstance(repository, StrategyRepository):
            raise TypeError("repository must be a StrategyRepository.")
        self.repository = repository

    def resolve(
        self,
        *,
        tenant_id: str,
        brand_id: str,
        strategy_id: str,
        strategy_version: int,
    ) -> StrategyDecision:
        decision = self.repository.get(
            tenant_id=tenant_id,
            strategy_id=strategy_id,
            version=strategy_version,
        )
        latest = self.repository.latest(tenant_id=tenant_id, strategy_id=strategy_id)
        if decision.brand_id != brand_id:
            raise ValueError("Strategy and requested brand differ.")
        if latest.version != decision.version:
            raise ValueError("Strategy reference is stale.")
        if decision.status is not StrategyStatus.APPROVED:
            raise ValueError("Strategy reference is not currently approved.")
        return decision

    def build(self, **reference: object) -> str:
        decision = self.resolve(**reference)
        evidence = [item for item in decision.evidence if item.verified]
        lines = [
            "APPROVED MARKETING STRATEGY — HUMAN REVIEWED",
            f"Strategy reference: {decision.strategy_id} v{decision.version}",
            f"Positioning reference: {decision.positioning_id} v{decision.positioning_version}",
        ]
        if decision.planning_horizon:
            lines.append(f"Planning horizon: {decision.planning_horizon}")
        if decision.business_objectives:
            lines.append("Objectives: " + "; ".join(decision.business_objectives))
        if decision.strategic_choices:
            lines.append("Strategic choices: " + "; ".join(decision.strategic_choices))
        if decision.explicit_non_choices:
            lines.append(
                "Explicit non-choices: " + "; ".join(decision.explicit_non_choices)
            )
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
