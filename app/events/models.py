"""Domain event models for MarketingLabAI."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from types import MappingProxyType
from typing import Any, Mapping
from uuid import uuid4


def current_utc_timestamp() -> str:
    """Return the current UTC timestamp."""

    return datetime.now(UTC).isoformat()


def create_event_id() -> str:
    """Create a unique domain event identifier."""

    return str(uuid4())


@dataclass(frozen=True)
class DomainEvent:
    """An immutable record describing something that happened."""

    event_type: str
    brand_id: str
    source: str
    summary: str
    payload: Mapping[str, Any] = field(default_factory=dict)
    event_id: str = field(default_factory=create_event_id)
    occurred_at: str = field(default_factory=current_utc_timestamp)

    def __post_init__(self) -> None:
        """Clean and validate event data."""

        event_id = self.event_id.strip()
        event_type = self.event_type.strip()
        brand_id = self.brand_id.strip()
        source = self.source.strip()
        summary = self.summary.strip()
        occurred_at = self.occurred_at.strip()

        if not event_id:
            raise ValueError("event_id is required.")

        if not event_type:
            raise ValueError("event_type is required.")

        if not brand_id:
            raise ValueError("brand_id is required.")

        if not source:
            raise ValueError("Event source is required.")

        if not summary:
            raise ValueError("Event summary is required.")

        if not occurred_at:
            raise ValueError("occurred_at is required.")

        if not isinstance(self.payload, Mapping):
            raise TypeError("Event payload must be a mapping.")

        object.__setattr__(self, "event_id", event_id)
        object.__setattr__(self, "event_type", event_type)
        object.__setattr__(self, "brand_id", brand_id)
        object.__setattr__(self, "source", source)
        object.__setattr__(self, "summary", summary)
        object.__setattr__(self, "occurred_at", occurred_at)
        object.__setattr__(
            self,
            "payload",
            MappingProxyType(dict(self.payload)),
        )

    def to_dict(self) -> dict[str, Any]:
        """Return a serialisable event representation."""

        return {
            "event_id": self.event_id,
            "event_type": self.event_type,
            "brand_id": self.brand_id,
            "source": self.source,
            "summary": self.summary,
            "payload": dict(self.payload),
            "occurred_at": self.occurred_at,
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "DomainEvent":
        """Create a domain event from serialised data."""

        event_payload = payload.get("payload", {})

        if not isinstance(event_payload, Mapping):
            raise TypeError("Stored event payload must be a mapping.")

        return cls(
            event_id=str(payload.get("event_id", "")),
            event_type=str(payload.get("event_type", "")),
            brand_id=str(payload.get("brand_id", "")),
            source=str(payload.get("source", "")),
            summary=str(payload.get("summary", "")),
            payload=dict(event_payload),
            occurred_at=str(payload.get("occurred_at", "")),
        )
