"""Lifecycle service for immutable Marketing Strategy decisions."""

from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime

from app.positioning_intelligence import PositioningRepository, PositioningStatus
from app.strategy_intelligence.models import StrategyDecision, StrategyStatus
from app.strategy_intelligence.repository import StrategyRepository


def _now() -> str:
    return datetime.now(UTC).isoformat()


class StrategyService:
    def __init__(
        self,
        repository: StrategyRepository,
        positioning_repository: PositioningRepository,
    ) -> None:
        if not isinstance(repository, StrategyRepository):
            raise TypeError("repository must be a StrategyRepository.")
        if not isinstance(positioning_repository, PositioningRepository):
            raise TypeError("positioning_repository must be a PositioningRepository.")
        self.repository = repository
        self.positioning_repository = positioning_repository

    def create(self, decision: StrategyDecision) -> StrategyDecision:
        if decision.version != 1 or decision.status is not StrategyStatus.DRAFT:
            raise ValueError("new strategy must begin as draft version 1.")
        self.repository.save(decision)
        return decision

    def revise(self, decision: StrategyDecision, **changes: object) -> StrategyDecision:
        current = self.repository.latest(
            tenant_id=decision.tenant_id, strategy_id=decision.strategy_id
        )
        if current != decision:
            raise ValueError("strategy revision must start from the latest version.")
        protected = {
            "strategy_id",
            "version",
            "tenant_id",
            "brand_id",
            "status",
            "created_at",
            "updated_at",
            "approved_at",
        }
        if protected.intersection(changes):
            raise ValueError("protected strategy fields cannot be revised.")
        revised = replace(
            current,
            **changes,
            version=current.version + 1,
            status=StrategyStatus.DRAFT,
            created_at=_now(),
            updated_at=_now(),
            approved_at="",
        )
        self.repository.save(revised)
        return revised

    def approve(self, decision: StrategyDecision) -> StrategyDecision:
        current = self.repository.latest(
            tenant_id=decision.tenant_id, strategy_id=decision.strategy_id
        )
        if current != decision:
            raise ValueError("only the latest strategy version may be approved.")
        if current.status is not StrategyStatus.DRAFT:
            raise ValueError("only draft strategy may be approved.")
        positioning = self.positioning_repository.get(
            tenant_id=current.tenant_id,
            positioning_id=current.positioning_id,
            version=current.positioning_version,
        )
        if positioning.brand_id != current.brand_id:
            raise ValueError("strategy and positioning brands differ.")
        if positioning.status is not PositioningStatus.APPROVED:
            raise ValueError("strategy approval requires approved positioning.")
        approved_at = _now()
        approved = replace(
            current,
            version=current.version + 1,
            status=StrategyStatus.APPROVED,
            created_at=approved_at,
            updated_at=approved_at,
            approved_at=approved_at,
        )
        self.repository.save(approved)
        return approved

    def retire(self, decision: StrategyDecision) -> StrategyDecision:
        current = self.repository.latest(
            tenant_id=decision.tenant_id, strategy_id=decision.strategy_id
        )
        if current != decision:
            raise ValueError("only the latest strategy version may be retired.")
        if current.status is not StrategyStatus.APPROVED:
            raise ValueError("only approved strategy may be retired.")
        retired_at = _now()
        retired = replace(
            current,
            version=current.version + 1,
            status=StrategyStatus.RETIRED,
            created_at=retired_at,
            updated_at=retired_at,
            approved_at="",
        )
        self.repository.save(retired)
        return retired
