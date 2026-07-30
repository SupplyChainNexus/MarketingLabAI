"""Domain models for the MarketingLabAI memory engine."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass
class MemoryEvent:
    """An immutable-in-purpose record of an important business event."""

    memory_id: str
    brand_id: str
    event_type: str
    source: str
    summary: str
    payload: dict[str, Any] = field(default_factory=dict)
    created_at: str = ""

    def __post_init__(self) -> None:
        """Validate required identity and classification fields."""

        self.memory_id = self.memory_id.strip()
        self.brand_id = self.brand_id.strip()
        self.event_type = self.event_type.strip()
        self.source = self.source.strip()
        self.summary = self.summary.strip()

        if not self.memory_id:
            raise ValueError("memory_id is required.")

        if not self.brand_id:
            raise ValueError("brand_id is required.")

        if not self.event_type:
            raise ValueError("event_type is required.")

        if not self.source:
            raise ValueError("Memory event source is required.")

        if not self.summary:
            raise ValueError("Memory event summary is required.")

        if not isinstance(self.payload, dict):
            raise TypeError("Memory event payload must be a dictionary.")

    def to_dict(self) -> dict[str, Any]:
        """Return a serialisable representation of the event."""

        return asdict(self)

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "MemoryEvent":
        """Create a memory event from stored data."""

        return cls(
            memory_id=str(payload.get("memory_id", "")),
            brand_id=str(payload.get("brand_id", "")),
            event_type=str(payload.get("event_type", "")),
            source=str(payload.get("source", "")),
            summary=str(payload.get("summary", "")),
            payload=dict(payload.get("payload", {})),
            created_at=str(payload.get("created_at", "")),
        )
