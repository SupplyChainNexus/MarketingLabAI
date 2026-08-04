"""Structured validation for Campaign Planner workflows."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping


def _required_text(field_name: str, value: str) -> str:
    if not isinstance(value, str):
        raise TypeError(f"{field_name} must be a string.")
    cleaned = value.strip()
    if not cleaned:
        raise ValueError(f"{field_name} is required.")
    return cleaned


@dataclass(frozen=True, slots=True)
class CampaignValidationIssue:
    code: str
    field: str
    message: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "code", _required_text("code", self.code))
        object.__setattr__(self, "field", _required_text("field", self.field))
        object.__setattr__(self, "message", _required_text("message", self.message))

    def to_dict(self) -> dict[str, str]:
        return {"code": self.code, "field": self.field, "message": self.message}

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "CampaignValidationIssue":
        return cls(code=data["code"], field=data["field"], message=data["message"])


@dataclass(frozen=True, slots=True)
class CampaignValidationResult:
    issues: tuple[CampaignValidationIssue, ...] = ()

    def __post_init__(self) -> None:
        if not isinstance(self.issues, tuple):
            object.__setattr__(self, "issues", tuple(self.issues))
        if not all(isinstance(i, CampaignValidationIssue) for i in self.issues):
            raise TypeError("issues must contain CampaignValidationIssue values.")

    @property
    def is_valid(self) -> bool:
        return not self.issues

    @property
    def fields(self) -> tuple[str, ...]:
        return tuple(dict.fromkeys(i.field for i in self.issues))

    def for_field(self, field_name: str) -> tuple[CampaignValidationIssue, ...]:
        field_name = _required_text("field_name", field_name)
        return tuple(i for i in self.issues if i.field == field_name)

    def to_dict(self) -> dict[str, Any]:
        return {"is_valid": self.is_valid, "issues": [i.to_dict() for i in self.issues]}

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "CampaignValidationResult":
        return cls(
            tuple(CampaignValidationIssue.from_dict(i) for i in data.get("issues", ()))
        )


class CampaignPlanValidator:
    def validate_for_planning(self, plan: object) -> CampaignValidationResult:
        from app.campaign_planner.models import CampaignPlan

        if not isinstance(plan, CampaignPlan):
            raise TypeError("plan must be a CampaignPlan.")
        issues = []
        if not plan.objective.statement:
            issues.append(
                CampaignValidationIssue(
                    "objective_required",
                    "objective",
                    "A campaign objective is required.",
                )
            )
        if not plan.audience.name or not plan.audience.description:
            issues.append(
                CampaignValidationIssue(
                    "audience_required",
                    "audience",
                    "A defined campaign audience is required.",
                )
            )
        if not plan.channels:
            issues.append(
                CampaignValidationIssue(
                    "channels_required",
                    "channels",
                    "At least one campaign channel is required.",
                )
            )
        if not plan.success_metrics:
            issues.append(
                CampaignValidationIssue(
                    "metrics_required",
                    "success_metrics",
                    "At least one success metric is required.",
                )
            )
        return CampaignValidationResult(tuple(issues))

    def validate_for_approval(self, plan: object) -> CampaignValidationResult:
        from app.campaign_planner.models import CampaignPlan

        if not isinstance(plan, CampaignPlan):
            raise TypeError("plan must be a CampaignPlan.")
        issues = list(self.validate_for_planning(plan).issues)
        if not plan.owner:
            issues.append(
                CampaignValidationIssue(
                    "owner_required",
                    "owner",
                    "A campaign owner is required before approval.",
                )
            )
        if not plan.objective.rationale:
            issues.append(
                CampaignValidationIssue(
                    "rationale_required",
                    "objective",
                    "Campaign objective rationale is required before approval.",
                )
            )
        if any(not metric.measurement_method for metric in plan.success_metrics):
            issues.append(
                CampaignValidationIssue(
                    "measurement_method_required",
                    "success_metrics",
                    "Every success metric requires a measurement method before approval.",
                )
            )
        return CampaignValidationResult(tuple(issues))
