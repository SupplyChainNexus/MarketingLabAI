"""Application services for Campaign Planner workflows."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from app.campaign_planner.models import CampaignPlan, CampaignStatus
from app.campaign_planner.validation import (
    CampaignPlanValidator,
    CampaignValidationResult,
)


class CampaignPlanningService:
    _UPDATABLE_FIELDS = frozenset(
        {
            "name",
            "objective",
            "audience",
            "timeline",
            "channels",
            "success_metrics",
            "owner",
            "notes",
        }
    )

    def __init__(self, validator: CampaignPlanValidator | None = None) -> None:
        if validator is not None and not isinstance(validator, CampaignPlanValidator):
            raise TypeError("validator must be a CampaignPlanValidator.")
        self.validator = validator or CampaignPlanValidator()

    def create_plan(self, **values: Any) -> CampaignPlan:
        plan = CampaignPlan(**values)
        self._raise_for_invalid(self.validator.validate_for_planning(plan))
        return plan

    def revise_plan(self, plan: CampaignPlan, **changes: Any) -> CampaignPlan:
        self._require_plan(plan)
        if plan.status not in {CampaignStatus.DRAFT, CampaignStatus.PLANNED}:
            raise ValueError("Only draft or planned Campaign Plans may be revised.")
        unknown = set(changes) - self._UPDATABLE_FIELDS
        if unknown:
            raise ValueError(
                "Unsupported campaign update fields: "
                + ", ".join(sorted(unknown))
                + "."
            )
        source = plan.to_dict()
        source.update(changes)
        source["status"] = CampaignStatus.DRAFT.value
        source["updated_at"] = datetime.now(plan.updated_at.tzinfo).isoformat()
        revised = CampaignPlan.from_dict(source)
        self._raise_for_invalid(self.validator.validate_for_planning(revised))
        return revised

    def evaluate_readiness(self, plan: CampaignPlan) -> CampaignValidationResult:
        self._require_plan(plan)
        return self.validator.validate_for_approval(plan)

    def mark_planned(
        self, plan: CampaignPlan, *, changed_at: datetime | None = None
    ) -> CampaignPlan:
        self._require_plan(plan)
        self._raise_for_invalid(self.validator.validate_for_planning(plan))
        plan.transition_to(CampaignStatus.PLANNED, changed_at=changed_at)
        return plan

    def approve(
        self, plan: CampaignPlan, *, changed_at: datetime | None = None
    ) -> CampaignPlan:
        self._require_plan(plan)
        if plan.status is not CampaignStatus.PLANNED:
            raise ValueError("Only a planned Campaign Plan may be approved.")
        self._raise_for_invalid(self.validator.validate_for_approval(plan))
        plan.transition_to(CampaignStatus.APPROVED, changed_at=changed_at)
        return plan

    def activate(
        self, plan: CampaignPlan, *, changed_at: datetime | None = None
    ) -> CampaignPlan:
        self._require_plan(plan)
        plan.transition_to(CampaignStatus.ACTIVE, changed_at=changed_at)
        return plan

    def complete(
        self, plan: CampaignPlan, *, changed_at: datetime | None = None
    ) -> CampaignPlan:
        self._require_plan(plan)
        plan.transition_to(CampaignStatus.COMPLETED, changed_at=changed_at)
        return plan

    def archive(
        self, plan: CampaignPlan, *, changed_at: datetime | None = None
    ) -> CampaignPlan:
        self._require_plan(plan)
        plan.transition_to(CampaignStatus.ARCHIVED, changed_at=changed_at)
        return plan

    @staticmethod
    def _require_plan(plan: object) -> None:
        if not isinstance(plan, CampaignPlan):
            raise TypeError("plan must be a CampaignPlan.")

    @staticmethod
    def _raise_for_invalid(result: CampaignValidationResult) -> None:
        if not result.is_valid:
            raise ValueError("; ".join(i.message for i in result.issues))
