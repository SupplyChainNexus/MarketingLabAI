"""Application services for Campaign Planner workflows."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Iterable

from app.campaign_planner.assets import CampaignAsset
from app.campaign_planner.briefs import CampaignBriefReference
from app.campaign_planner.dependencies import CampaignDependencyPlanner
from app.campaign_planner.models import CampaignPlan, CampaignStatus
from app.campaign_planner.validation import (
    CampaignPlanValidator,
    CampaignValidationResult,
)


class CampaignPlanningService:
    """Create, revise and advance Campaign Plans deterministically."""

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

    def __init__(
        self,
        validator: CampaignPlanValidator | None = None,
        dependency_planner: CampaignDependencyPlanner | None = None,
    ) -> None:
        if validator is not None and not isinstance(
            validator,
            CampaignPlanValidator,
        ):
            raise TypeError("validator must be a CampaignPlanValidator.")
        if dependency_planner is not None and not isinstance(
            dependency_planner,
            CampaignDependencyPlanner,
        ):
            raise TypeError("dependency_planner must be a CampaignDependencyPlanner.")
        self.validator = validator or CampaignPlanValidator()
        self.dependency_planner = dependency_planner or CampaignDependencyPlanner()

    def create_plan(self, **values: Any) -> CampaignPlan:
        plan = CampaignPlan(**values)
        self._raise_for_invalid(self.validator.validate_for_planning(plan))
        return plan

    def revise_plan(self, plan: CampaignPlan, **changes: Any) -> CampaignPlan:
        self._require_plan(plan)
        if plan.status not in {CampaignStatus.DRAFT, CampaignStatus.PLANNED}:
            raise ValueError("Only draft or planned Campaign Plans may be revised.")
        unknown_fields = set(changes) - self._UPDATABLE_FIELDS
        if unknown_fields:
            names = ", ".join(sorted(unknown_fields))
            raise ValueError(f"Unsupported campaign update fields: {names}.")
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

    def add_asset(
        self,
        assets: Iterable[CampaignAsset],
        asset: CampaignAsset,
        *,
        campaign_id: str,
    ) -> tuple[CampaignAsset, ...]:
        current = self._asset_tuple(assets)
        if not isinstance(asset, CampaignAsset):
            raise TypeError("asset must be a CampaignAsset.")
        if asset.campaign_id != campaign_id:
            raise ValueError("Campaign asset belongs to a different campaign.")
        if any(existing.asset_id == asset.asset_id for existing in current):
            raise ValueError(f"Duplicate campaign asset id: {asset.asset_id}.")
        if any(existing.duplicate_key == asset.duplicate_key for existing in current):
            raise ValueError("A matching campaign asset already exists.")
        updated = current + (asset,)
        issues = self.dependency_planner.validate(updated)
        missing_only = [issue for issue in issues if issue.code == "dependency_cycle"]
        if missing_only:
            raise ValueError(missing_only[0].message)
        return updated

    def remove_asset(
        self,
        assets: Iterable[CampaignAsset],
        asset_id: str,
    ) -> tuple[CampaignAsset, ...]:
        current = self._asset_tuple(assets)
        cleaned_id = asset_id.strip() if isinstance(asset_id, str) else ""
        if not cleaned_id:
            raise ValueError("asset_id is required.")
        if not any(asset.asset_id == cleaned_id for asset in current):
            raise ValueError("Campaign asset was not found.")
        dependants = [
            asset.name for asset in current if cleaned_id in asset.dependency_ids
        ]
        if dependants:
            raise ValueError(
                "Campaign asset cannot be removed while dependants exist: "
                + ", ".join(sorted(dependants))
                + "."
            )
        return tuple(asset for asset in current if asset.asset_id != cleaned_id)

    def execution_order(
        self,
        assets: Iterable[CampaignAsset],
    ) -> tuple[CampaignAsset, ...]:
        return self.dependency_planner.execution_order(assets)

    def blocked_assets(
        self,
        assets: Iterable[CampaignAsset],
    ) -> tuple[CampaignAsset, ...]:
        return self.dependency_planner.blocked_assets(assets)

    def associate_brief(
        self,
        references: Iterable[CampaignBriefReference],
        reference: CampaignBriefReference,
        *,
        plan: CampaignPlan,
    ) -> tuple[CampaignBriefReference, ...]:
        """Associate one immutable brief version without changing either lifecycle."""

        self._require_plan(plan)
        current = self._brief_reference_tuple(references)
        if not isinstance(reference, CampaignBriefReference):
            raise TypeError("reference must be a CampaignBriefReference.")
        if reference.campaign_id != plan.campaign_id:
            raise ValueError("Marketing Brief reference belongs to another campaign.")
        if reference.tenant_id != plan.tenant_id:
            raise ValueError("Marketing Brief reference belongs to another tenant.")
        if reference.brand_id != plan.brand_id:
            raise ValueError("Marketing Brief reference belongs to another brand.")
        if reference in current:
            raise ValueError("Marketing Brief version is already associated.")
        return current + (reference,)

    @staticmethod
    def _asset_tuple(assets: Iterable[CampaignAsset]) -> tuple[CampaignAsset, ...]:
        if isinstance(assets, (str, bytes)):
            raise TypeError("assets must be an iterable of CampaignAsset values.")
        values = tuple(assets)
        if not all(isinstance(asset, CampaignAsset) for asset in values):
            raise TypeError("assets must contain CampaignAsset values.")
        return values

    @staticmethod
    def _brief_reference_tuple(
        references: Iterable[CampaignBriefReference],
    ) -> tuple[CampaignBriefReference, ...]:
        try:
            values = tuple(references)
        except TypeError as error:
            raise TypeError(
                "references must be an iterable of CampaignBriefReference values."
            ) from error
        if not all(isinstance(value, CampaignBriefReference) for value in values):
            raise TypeError("references must contain CampaignBriefReference values.")
        return values

    @staticmethod
    def _require_plan(plan: object) -> None:
        if not isinstance(plan, CampaignPlan):
            raise TypeError("plan must be a CampaignPlan.")

    @staticmethod
    def _raise_for_invalid(result: CampaignValidationResult) -> None:
        if result.is_valid:
            return
        raise ValueError("; ".join(issue.message for issue in result.issues))
