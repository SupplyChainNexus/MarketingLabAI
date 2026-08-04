"""Provider-neutral Marketing Brief references for Campaign Plans."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from app.campaign_planner.models import CampaignPlan, CampaignStatus


def _required_text(field_name: str, value: str) -> str:
    if not isinstance(value, str):
        raise TypeError(f"{field_name} must be a string.")
    cleaned = value.strip()
    if not cleaned:
        raise ValueError(f"{field_name} is required.")
    return cleaned


@dataclass(frozen=True, slots=True)
class CampaignBriefReference:
    """An explicit, version-aware link from a plan to a Marketing Brief."""

    campaign_id: str
    brief_id: str
    brief_version: int
    tenant_id: str
    brand_id: str

    def __post_init__(self) -> None:
        for field_name in ("campaign_id", "brief_id", "tenant_id", "brand_id"):
            object.__setattr__(
                self,
                field_name,
                _required_text(field_name, getattr(self, field_name)),
            )
        if isinstance(self.brief_version, bool) or not isinstance(
            self.brief_version, int
        ):
            raise TypeError("brief_version must be an integer.")
        if self.brief_version < 1:
            raise ValueError("brief_version must be at least 1.")


@dataclass(frozen=True, slots=True)
class CampaignPlanAuditMetadata:
    """Immutable campaign and brief identifiers returned after generation."""

    campaign_id: str
    campaign_status: CampaignStatus
    campaign_updated_at: datetime
    brief_id: str
    brief_version: int
    tenant_id: str
    brand_id: str

    def __post_init__(self) -> None:
        for field_name in ("campaign_id", "brief_id", "tenant_id", "brand_id"):
            object.__setattr__(
                self,
                field_name,
                _required_text(field_name, getattr(self, field_name)),
            )
        if not isinstance(self.campaign_status, CampaignStatus):
            object.__setattr__(
                self,
                "campaign_status",
                CampaignStatus(self.campaign_status),
            )
        if not isinstance(self.campaign_updated_at, datetime):
            raise TypeError("campaign_updated_at must be a datetime.")
        if (
            self.campaign_updated_at.tzinfo is None
            or self.campaign_updated_at.utcoffset() is None
        ):
            raise ValueError("campaign_updated_at must include timezone information.")
        if isinstance(self.brief_version, bool) or not isinstance(
            self.brief_version, int
        ):
            raise TypeError("brief_version must be an integer.")
        if self.brief_version < 1:
            raise ValueError("brief_version must be at least 1.")

    @classmethod
    def from_plan_and_reference(
        cls,
        plan: CampaignPlan,
        reference: CampaignBriefReference,
    ) -> "CampaignPlanAuditMetadata":
        if not isinstance(plan, CampaignPlan):
            raise TypeError("plan must be a CampaignPlan.")
        if not isinstance(reference, CampaignBriefReference):
            raise TypeError("reference must be a CampaignBriefReference.")
        if reference.campaign_id != plan.campaign_id:
            raise ValueError("Marketing Brief reference belongs to another campaign.")
        if reference.tenant_id != plan.tenant_id:
            raise ValueError("Marketing Brief reference belongs to another tenant.")
        if reference.brand_id != plan.brand_id:
            raise ValueError("Marketing Brief reference belongs to another brand.")
        return cls(
            campaign_id=plan.campaign_id,
            campaign_status=plan.status,
            campaign_updated_at=plan.updated_at,
            brief_id=reference.brief_id,
            brief_version=reference.brief_version,
            tenant_id=plan.tenant_id,
            brand_id=plan.brand_id,
        )
