"""Memory Engine subscriber for domain events."""

from __future__ import annotations

from app.database.repositories import MemoryRepository
from app.events.models import DomainEvent
from app.memory.models import MemoryEvent


class MemoryEventRecorder:
    """Record published domain events in institutional memory."""

    def __init__(
        self,
        repository: MemoryRepository | None = None,
    ) -> None:
        self.repository = repository or MemoryRepository()

    def __call__(self, event: DomainEvent) -> None:
        """Convert and store a domain event as a memory event."""

        memory_event = MemoryEvent(
            memory_id=f"event-{event.event_id}",
            brand_id=event.brand_id,
            event_type=event.event_type,
            source=event.source,
            summary=event.summary,
            payload={
                "domain_event_id": event.event_id,
                "occurred_at": event.occurred_at,
                **dict(event.payload),
            },
            created_at=event.occurred_at,
        )

        self.repository.save(memory_event)
