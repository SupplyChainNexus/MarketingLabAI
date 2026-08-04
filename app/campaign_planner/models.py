"""Provider-neutral campaign planning domain models."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from enum import StrEnum
from typing import Any, Iterable, Mapping
from uuid import uuid4


def _required_text(field_name: str, value: str) -> str:
    if not isinstance(value, str):
        raise TypeError(f"{field_name} must be a string.")
    cleaned = value.strip()
    if not cleaned:
        raise ValueError(f"{field_name} is required.")
    return cleaned


def _optional_text(field_name: str, value: str) -> str:
    if not isinstance(value, str):
        raise TypeError(f"{field_name} must be a string.")
    return value.strip()


def _unique_names(field_name: str, values: Iterable[str]) -> None:
    seen: set[str] = set()
    for value in values:
        cleaned = _required_text(field_name, value)
        key = cleaned.casefold()
        if key in seen:
            raise ValueError(f"{field_name} must be unique.")
        seen.add(key)


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _datetime_value(field_name: str, value: datetime) -> datetime:
    if not isinstance(value, datetime):
        raise TypeError(f"{field_name} must be a datetime.")
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{field_name} must include timezone information.")
    return value.astimezone(timezone.utc)


def _date_value(field_name: str, value: date) -> date:
    if isinstance(value, datetime) or not isinstance(value, date):
        raise TypeError(f"{field_name} must be a date.")
    return value


class CampaignStatus(StrEnum):
    """Lifecycle states for a campaign plan."""

    DRAFT = "draft"
    PLANNED = "planned"
    APPROVED = "approved"
    ACTIVE = "active"
    COMPLETED = "completed"
    ARCHIVED = "archived"


_ALLOWED_TRANSITIONS: dict[CampaignStatus, frozenset[CampaignStatus]] = {
    CampaignStatus.DRAFT: frozenset({CampaignStatus.PLANNED}),
    CampaignStatus.PLANNED: frozenset({CampaignStatus.DRAFT, CampaignStatus.APPROVED}),
    CampaignStatus.APPROVED: frozenset({CampaignStatus.PLANNED, CampaignStatus.ACTIVE}),
    CampaignStatus.ACTIVE: frozenset({CampaignStatus.COMPLETED}),
    CampaignStatus.COMPLETED: frozenset({CampaignStatus.ARCHIVED}),
    CampaignStatus.ARCHIVED: frozenset(),
}


@dataclass(frozen=True, slots=True)
class CampaignObjective:
    """The business result a campaign is intended to achieve."""

    statement: str
    rationale: str = ""

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "statement", _required_text("statement", self.statement)
        )
        object.__setattr__(
            self, "rationale", _optional_text("rationale", self.rationale)
        )

    def to_dict(self) -> dict[str, str]:
        return {"statement": self.statement, "rationale": self.rationale}

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> CampaignObjective:
        return cls(
            statement=data["statement"],
            rationale=data.get("rationale", ""),
        )


@dataclass(frozen=True, slots=True)
class CampaignAudience:
    """The audience segment a campaign is intended to reach."""

    name: str
    description: str
    segment_id: str = ""

    def __post_init__(self) -> None:
        object.__setattr__(self, "name", _required_text("name", self.name))
        object.__setattr__(
            self,
            "description",
            _required_text("description", self.description),
        )
        object.__setattr__(
            self,
            "segment_id",
            _optional_text("segment_id", self.segment_id),
        )

    def to_dict(self) -> dict[str, str]:
        return {
            "name": self.name,
            "description": self.description,
            "segment_id": self.segment_id,
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> CampaignAudience:
        return cls(
            name=data["name"],
            description=data["description"],
            segment_id=data.get("segment_id", ""),
        )


@dataclass(frozen=True, slots=True)
class CampaignChannel:
    """A channel selected for campaign execution."""

    name: str
    purpose: str = ""

    def __post_init__(self) -> None:
        object.__setattr__(self, "name", _required_text("name", self.name))
        object.__setattr__(self, "purpose", _optional_text("purpose", self.purpose))

    def to_dict(self) -> dict[str, str]:
        return {"name": self.name, "purpose": self.purpose}

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> CampaignChannel:
        return cls(name=data["name"], purpose=data.get("purpose", ""))


@dataclass(frozen=True, slots=True)
class CampaignMetric:
    """A measurable result used to judge campaign success."""

    name: str
    target: str
    measurement_method: str = ""

    def __post_init__(self) -> None:
        object.__setattr__(self, "name", _required_text("name", self.name))
        object.__setattr__(self, "target", _required_text("target", self.target))
        object.__setattr__(
            self,
            "measurement_method",
            _optional_text("measurement_method", self.measurement_method),
        )

    def to_dict(self) -> dict[str, str]:
        return {
            "name": self.name,
            "target": self.target,
            "measurement_method": self.measurement_method,
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> CampaignMetric:
        return cls(
            name=data["name"],
            target=data["target"],
            measurement_method=data.get("measurement_method", ""),
        )


@dataclass(frozen=True, slots=True)
class CampaignTimeline:
    """The planned campaign start and end dates."""

    start_date: date
    end_date: date

    def __post_init__(self) -> None:
        start_date = _date_value("start_date", self.start_date)
        end_date = _date_value("end_date", self.end_date)
        if end_date < start_date:
            raise ValueError("end_date cannot be earlier than start_date.")
        object.__setattr__(self, "start_date", start_date)
        object.__setattr__(self, "end_date", end_date)

    @property
    def duration_days(self) -> int:
        return (self.end_date - self.start_date).days + 1

    def includes(self, value: date) -> bool:
        checked_value = _date_value("value", value)
        return self.start_date <= checked_value <= self.end_date

    def to_dict(self) -> dict[str, str]:
        return {
            "start_date": self.start_date.isoformat(),
            "end_date": self.end_date.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> CampaignTimeline:
        return cls(
            start_date=date.fromisoformat(data["start_date"]),
            end_date=date.fromisoformat(data["end_date"]),
        )


@dataclass(slots=True)
class CampaignPlan:
    """A reviewable, provider-neutral marketing campaign plan."""

    tenant_id: str
    brand_id: str
    name: str
    objective: CampaignObjective
    audience: CampaignAudience
    timeline: CampaignTimeline
    channels: tuple[CampaignChannel, ...]
    success_metrics: tuple[CampaignMetric, ...]
    owner: str
    campaign_id: str = field(default_factory=lambda: str(uuid4()))
    version: int = 1
    status: CampaignStatus = CampaignStatus.DRAFT
    notes: str = ""
    created_at: datetime = field(default_factory=_utc_now)
    updated_at: datetime = field(default_factory=_utc_now)

    def __post_init__(self) -> None:
        self.tenant_id = _required_text("tenant_id", self.tenant_id)
        self.brand_id = _required_text("brand_id", self.brand_id)
        self.name = _required_text("name", self.name)
        self.owner = _required_text("owner", self.owner)
        self.campaign_id = _required_text("campaign_id", self.campaign_id)
        self.notes = _optional_text("notes", self.notes)

        if isinstance(self.version, bool) or not isinstance(self.version, int):
            raise TypeError("version must be an integer.")
        if self.version < 1:
            raise ValueError("version must be at least 1.")

        if not isinstance(self.objective, CampaignObjective):
            raise TypeError("objective must be a CampaignObjective.")
        if not isinstance(self.audience, CampaignAudience):
            raise TypeError("audience must be a CampaignAudience.")
        if not isinstance(self.timeline, CampaignTimeline):
            raise TypeError("timeline must be a CampaignTimeline.")

        if isinstance(self.channels, list):
            self.channels = tuple(self.channels)
        if not isinstance(self.channels, tuple):
            raise TypeError("channels must be a tuple of CampaignChannel values.")
        if not self.channels:
            raise ValueError("At least one campaign channel is required.")
        if not all(isinstance(channel, CampaignChannel) for channel in self.channels):
            raise TypeError("channels must contain CampaignChannel values.")
        _unique_names(
            "Campaign channel names",
            (channel.name for channel in self.channels),
        )

        if isinstance(self.success_metrics, list):
            self.success_metrics = tuple(self.success_metrics)
        if not isinstance(self.success_metrics, tuple):
            raise TypeError("success_metrics must be a tuple of CampaignMetric values.")
        if not self.success_metrics:
            raise ValueError("At least one campaign success metric is required.")
        if not all(
            isinstance(metric, CampaignMetric) for metric in self.success_metrics
        ):
            raise TypeError("success_metrics must contain CampaignMetric values.")
        _unique_names(
            "Campaign metric names",
            (metric.name for metric in self.success_metrics),
        )

        if not isinstance(self.status, CampaignStatus):
            self.status = CampaignStatus(self.status)

        self.created_at = _datetime_value("created_at", self.created_at)
        self.updated_at = _datetime_value("updated_at", self.updated_at)
        if self.updated_at < self.created_at:
            raise ValueError("updated_at cannot be earlier than created_at.")

    def transition_to(
        self,
        status: CampaignStatus,
        *,
        changed_at: datetime | None = None,
    ) -> None:
        """Move the campaign plan through its controlled lifecycle."""

        if not isinstance(status, CampaignStatus):
            status = CampaignStatus(status)
        if status == self.status:
            return
        if status not in _ALLOWED_TRANSITIONS[self.status]:
            raise ValueError(
                "Campaign status cannot transition from "
                f"{self.status.value} to {status.value}."
            )
        self.status = status
        self.updated_at = _datetime_value("changed_at", changed_at or _utc_now())

    def to_dict(self) -> dict[str, Any]:
        """Return a detached serialisable representation."""

        return {
            "campaign_id": self.campaign_id,
            "version": self.version,
            "tenant_id": self.tenant_id,
            "brand_id": self.brand_id,
            "name": self.name,
            "objective": self.objective.to_dict(),
            "audience": self.audience.to_dict(),
            "timeline": self.timeline.to_dict(),
            "channels": [channel.to_dict() for channel in self.channels],
            "success_metrics": [metric.to_dict() for metric in self.success_metrics],
            "owner": self.owner,
            "status": self.status.value,
            "notes": self.notes,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> CampaignPlan:
        """Rebuild a CampaignPlan from serialised data."""

        return cls(
            campaign_id=data["campaign_id"],
            version=data.get("version", 1),
            tenant_id=data["tenant_id"],
            brand_id=data["brand_id"],
            name=data["name"],
            objective=CampaignObjective.from_dict(data["objective"]),
            audience=CampaignAudience.from_dict(data["audience"]),
            timeline=CampaignTimeline.from_dict(data["timeline"]),
            channels=tuple(
                CampaignChannel.from_dict(item) for item in data["channels"]
            ),
            success_metrics=tuple(
                CampaignMetric.from_dict(item) for item in data["success_metrics"]
            ),
            owner=data["owner"],
            status=CampaignStatus(data["status"]),
            notes=data.get("notes", ""),
            created_at=datetime.fromisoformat(data["created_at"]),
            updated_at=datetime.fromisoformat(data["updated_at"]),
        )
