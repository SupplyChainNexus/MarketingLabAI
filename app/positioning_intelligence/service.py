"""Lifecycle service for immutable Positioning Intelligence decisions."""

from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime

from app.positioning_intelligence.models import PositioningDecision, PositioningStatus
from app.positioning_intelligence.repository import PositioningRepository
from app.positioning_intelligence.value_proposition import ValuePropositionCandidate


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

    def approve_candidate(
        self,
        decision: PositioningDecision,
        candidate: ValuePropositionCandidate,
    ) -> PositioningDecision:
        if not isinstance(candidate, ValuePropositionCandidate):
            raise TypeError("candidate must be a ValuePropositionCandidate.")
        if not candidate.is_ready:
            raise ValueError(
                "only a ready value proposition candidate may be approved."
            )
        if (
            candidate.positioning_id != decision.positioning_id
            or candidate.positioning_version != decision.version
        ):
            raise ValueError("candidate belongs to another positioning version.")
        if decision.value_proposition != candidate.statement:
            raise ValueError("decision must record the reviewed candidate statement.")
        return self.approve(decision)

    def retire(self, decision: PositioningDecision) -> PositioningDecision:
        current = self.repository.latest(
            tenant_id=decision.tenant_id,
            positioning_id=decision.positioning_id,
        )
        if current != decision:
            raise ValueError("only the latest positioning version may be retired.")
        if current.status is not PositioningStatus.APPROVED:
            raise ValueError("only approved positioning may be retired.")
        retired_at = _now()
        retired = replace(
            current,
            version=current.version + 1,
            status=PositioningStatus.RETIRED,
            created_at=retired_at,
            updated_at=retired_at,
            approved_at="",
        )
        self.repository.save(retired)
        return retired

    def replace(
        self,
        retired: PositioningDecision,
        replacement: PositioningDecision,
    ) -> PositioningDecision:
        current = self.repository.latest(
            tenant_id=retired.tenant_id,
            positioning_id=retired.positioning_id,
        )
        if current != retired or current.status is not PositioningStatus.RETIRED:
            raise ValueError("replacement requires the latest retired positioning.")
        if (
            replacement.positioning_id == retired.positioning_id
            or replacement.version != 1
            or replacement.status is not PositioningStatus.DRAFT
        ):
            raise ValueError("replacement must be a new draft positioning identity.")
        if (
            replacement.tenant_id != retired.tenant_id
            or replacement.brand_id != retired.brand_id
        ):
            raise ValueError("replacement must preserve tenant and brand ownership.")
        self.repository.save(replacement)
        return replacement
