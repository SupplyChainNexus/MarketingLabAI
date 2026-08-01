"""Simple domain event publisher."""

from __future__ import annotations

from app.events.bus import EventBus
from app.events.models import DomainEvent


class EventPublisher:
    """Publish domain events."""

    def __init__(
        self,
        event_bus: EventBus | None = None,
    ) -> None:
        self.event_bus = event_bus or EventBus()

    def publish(
        self,
        event: DomainEvent,
    ) -> None:
        """Publish a domain event."""

        self.event_bus.publish(event)
