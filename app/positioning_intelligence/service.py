"""Lifecycle service for immutable Positioning Intelligence decisions."""

from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime

from app.positioning_intelligence.models import PositioningDecision, PositioningStatus
from app.positioning_intelligence.repository import PositioningRepository


def _now() -> str:
    return datetime.now(UTC).isoformat()


class PositioningService:
    def __init__(self, repository: PositioningRepository) -> None:
        if not isinstance(repository, PositioningRepository):
            raise TypeError("repository must be a PositioningRepository.")
        self.repository = repository

    def create(self, decision: PositioningDecision) -> PositioningDecision:
        if decision.version != 1 or decision.status is not PositioningStatus.DRAFT:
            raise ValueError("new positioning must begin as draft version 1.")
        self.repository.save(decision)
        return decision

    def revise(
        self, decision: PositioningDecision, **changes: object
    ) -> PositioningDecision:
        current = self.repository.latest(
            tenant_id=decision.tenant_id,
            positioning_id=decision.positioning_id,
        )
        if current != decision:
            raise ValueError("positioning revision must start from the latest version.")
        protected = {
            "positioning_id",
            "version",
            "tenant_id",
            "brand_id",
            "status",
            "created_at",
            "updated_at",
            "approved_at",
        }
        if protected.intersection(changes):
            raise ValueError("protected positioning fields cannot be revised.")
        revised = replace(
            current,
            **changes,
            version=current.version + 1,
            status=PositioningStatus.DRAFT,
            created_at=_now(),
            updated_at=_now(),
            approved_at="",
        )
        self.repository.save(revised)
        return revised

    def approve(self, decision: PositioningDecision) -> PositioningDecision:
        current = self.repository.latest(
            tenant_id=decision.tenant_id,
            positioning_id=decision.positioning_id,
        )
        if current != decision:
            raise ValueError("only the latest positioning version may be approved.")
        if current.status is not PositioningStatus.DRAFT:
            raise ValueError("only draft positioning may be approved.")
        approved_at = _now()
        approved = replace(
            current,
            version=current.version + 1,
            status=PositioningStatus.APPROVED,
            created_at=approved_at,
            updated_at=approved_at,
            approved_at=approved_at,
        )
        self.repository.save(approved)
        return approved
