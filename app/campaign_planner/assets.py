"""Campaign deliverable planning models."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import IntEnum, StrEnum
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


def _clean_text_tuple(field_name: str, values: Iterable[str]) -> tuple[str, ...]:
    if isinstance(values, (str, bytes)) or not isinstance(values, Iterable):
        raise TypeError(f"{field_name} must be an iterable of strings.")
    cleaned: list[str] = []
    seen: set[str] = set()
    for value in values:
        item = _required_text(field_name, value)
        key = item.casefold()
        if key in seen:
            continue
        seen.add(key)
        cleaned.append(item)
    return tuple(cleaned)


class CampaignAssetStatus(StrEnum):
    """Lifecycle states for campaign deliverables."""

    PLANNED = "planned"
    READY = "ready"
    IN_PROGRESS = "in_progress"
    UNDER_REVIEW = "under_review"
    APPROVED = "approved"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class CampaignPriority(IntEnum):
    """Execution priority where lower numeric values run first."""

    CRITICAL = 1
    HIGH = 2
    NORMAL = 3
    LOW = 4


_ALLOWED_ASSET_TRANSITIONS = {
    CampaignAssetStatus.PLANNED: frozenset(
        {CampaignAssetStatus.READY, CampaignAssetStatus.CANCELLED}
    ),
    CampaignAssetStatus.READY: frozenset(
        {CampaignAssetStatus.IN_PROGRESS, CampaignAssetStatus.CANCELLED}
    ),
    CampaignAssetStatus.IN_PROGRESS: frozenset(
        {CampaignAssetStatus.UNDER_REVIEW, CampaignAssetStatus.CANCELLED}
    ),
    CampaignAssetStatus.UNDER_REVIEW: frozenset(
        {CampaignAssetStatus.IN_PROGRESS, CampaignAssetStatus.APPROVED}
    ),
    CampaignAssetStatus.APPROVED: frozenset({CampaignAssetStatus.COMPLETED}),
    CampaignAssetStatus.COMPLETED: frozenset(),
    CampaignAssetStatus.CANCELLED: frozenset(),
}


@dataclass(frozen=True, slots=True)
class CampaignAssetType:
    """Provider-neutral classification for a campaign deliverable."""

    name: str
    category: str = ""

    def __post_init__(self) -> None:
        object.__setattr__(self, "name", _required_text("name", self.name))
        object.__setattr__(
            self,
            "category",
            _optional_text("category", self.category),
        )

    def to_dict(self) -> dict[str, str]:
        return {"name": self.name, "category": self.category}

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "CampaignAssetType":
        return cls(name=data["name"], category=data.get("category", ""))


@dataclass(frozen=True, slots=True)
class DefinitionOfDoneItem:
    """A measurable completion condition for a campaign deliverable."""

    description: str
    completed: bool = False

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "description",
            _required_text("description", self.description),
        )
        if not isinstance(self.completed, bool):
            raise TypeError("completed must be a boolean.")

    def to_dict(self) -> dict[str, Any]:
        return {
            "description": self.description,
            "completed": self.completed,
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "DefinitionOfDoneItem":
        return cls(
            description=data["description"],
            completed=data.get("completed", False),
        )


@dataclass(slots=True)
class CampaignAsset:
    """A planned unit of marketing work, not a stored file."""

    campaign_id: str
    name: str
    channel: str
    asset_type: CampaignAssetType
    owner: str
    asset_id: str = field(default_factory=lambda: str(uuid4()))
    purpose: str = ""
    priority: CampaignPriority = CampaignPriority.NORMAL
    status: CampaignAssetStatus = CampaignAssetStatus.PLANNED
    dependency_ids: tuple[str, ...] = ()
    definition_of_done: tuple[DefinitionOfDoneItem, ...] = ()
    notes: str = ""

    def __post_init__(self) -> None:
        self.campaign_id = _required_text("campaign_id", self.campaign_id)
        self.asset_id = _required_text("asset_id", self.asset_id)
        self.name = _required_text("name", self.name)
        self.channel = _required_text("channel", self.channel)
        self.owner = _required_text("owner", self.owner)
        self.purpose = _optional_text("purpose", self.purpose)
        self.notes = _optional_text("notes", self.notes)

        if not isinstance(self.asset_type, CampaignAssetType):
            raise TypeError("asset_type must be a CampaignAssetType.")
        if not isinstance(self.priority, CampaignPriority):
            self.priority = CampaignPriority(self.priority)
        if not isinstance(self.status, CampaignAssetStatus):
            self.status = CampaignAssetStatus(self.status)

        self.dependency_ids = _clean_text_tuple(
            "dependency_ids",
            self.dependency_ids,
        )
        if self.asset_id in self.dependency_ids:
            raise ValueError("A campaign asset cannot depend on itself.")

        if not isinstance(self.definition_of_done, tuple):
            self.definition_of_done = tuple(self.definition_of_done)
        if not all(
            isinstance(item, DefinitionOfDoneItem) for item in self.definition_of_done
        ):
            raise TypeError(
                "definition_of_done must contain DefinitionOfDoneItem values."
            )

    @property
    def completion_ratio(self) -> float:
        if not self.definition_of_done:
            return 0.0
        completed = sum(item.completed for item in self.definition_of_done)
        return completed / len(self.definition_of_done)

    @property
    def definition_complete(self) -> bool:
        return bool(self.definition_of_done) and all(
            item.completed for item in self.definition_of_done
        )

    def transition_to(self, status: CampaignAssetStatus) -> None:
        if not isinstance(status, CampaignAssetStatus):
            status = CampaignAssetStatus(status)
        if status == self.status:
            return
        if status not in _ALLOWED_ASSET_TRANSITIONS[self.status]:
            raise ValueError(
                "Campaign asset status cannot transition from "
                f"{self.status.value} to {status.value}."
            )
        if (
            status
            in {
                CampaignAssetStatus.APPROVED,
                CampaignAssetStatus.COMPLETED,
            }
            and not self.definition_complete
        ):
            raise ValueError("Definition of done must be complete before approval.")
        self.status = status

    def mark_definition_item(self, description: str, completed: bool = True) -> None:
        cleaned = _required_text("description", description)
        if not isinstance(completed, bool):
            raise TypeError("completed must be a boolean.")
        updated: list[DefinitionOfDoneItem] = []
        found = False
        for item in self.definition_of_done:
            if item.description.casefold() == cleaned.casefold():
                updated.append(DefinitionOfDoneItem(item.description, completed))
                found = True
            else:
                updated.append(item)
        if not found:
            raise ValueError("Definition of done item was not found.")
        self.definition_of_done = tuple(updated)

    @property
    def duplicate_key(self) -> tuple[str, str, str]:
        return (
            self.channel.casefold(),
            self.asset_type.name.casefold(),
            self.name.casefold(),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "campaign_id": self.campaign_id,
            "asset_id": self.asset_id,
            "name": self.name,
            "channel": self.channel,
            "asset_type": self.asset_type.to_dict(),
            "owner": self.owner,
            "purpose": self.purpose,
            "priority": self.priority.name.lower(),
            "status": self.status.value,
            "dependency_ids": list(self.dependency_ids),
            "definition_of_done": [item.to_dict() for item in self.definition_of_done],
            "notes": self.notes,
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "CampaignAsset":
        return cls(
            campaign_id=data["campaign_id"],
            asset_id=data["asset_id"],
            name=data["name"],
            channel=data["channel"],
            asset_type=CampaignAssetType.from_dict(data["asset_type"]),
            owner=data["owner"],
            purpose=data.get("purpose", ""),
            priority=CampaignPriority[data.get("priority", "normal").upper()],
            status=CampaignAssetStatus(data.get("status", "planned")),
            dependency_ids=tuple(data.get("dependency_ids", ())),
            definition_of_done=tuple(
                DefinitionOfDoneItem.from_dict(item)
                for item in data.get("definition_of_done", ())
            ),
            notes=data.get("notes", ""),
        )
