"""Synchronous publish-and-subscribe event bus."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Callable
from dataclasses import dataclass

from app.events.models import DomainEvent

EventHandler = Callable[[DomainEvent], None]
WILDCARD_EVENT_TYPE = "*"


@dataclass(frozen=True)
class EventDispatchFailure:
    """Information about one failed event handler."""

    event: DomainEvent
    handler: EventHandler
    error: Exception


class EventDispatchError(RuntimeError):
    """Raised after one or more event handlers fail."""

    def __init__(
        self,
        event: DomainEvent,
        failures: list[EventDispatchFailure],
    ) -> None:
        self.event = event
        self.failures = tuple(failures)

        super().__init__(
            f"{len(failures)} handler(s) failed while dispatching "
            f"event '{event.event_type}'."
        )


class EventBus:
    """Dispatch domain events to subscribed handlers."""

    def __init__(self) -> None:
        self._subscriptions: dict[str, list[EventHandler]] = defaultdict(list)

    def subscribe(
        self,
        event_type: str,
        handler: EventHandler,
    ) -> None:
        """Subscribe a handler to an event type."""

        event_type = event_type.strip()

        if not event_type:
            raise ValueError("event_type is required.")

        if not callable(handler):
            raise TypeError("handler must be callable.")

        handlers = self._subscriptions[event_type]

        if handler not in handlers:
            handlers.append(handler)

    def subscribe_all(self, handler: EventHandler) -> None:
        """Subscribe a handler to every published event."""

        self.subscribe(WILDCARD_EVENT_TYPE, handler)

    def unsubscribe(
        self,
        event_type: str,
        handler: EventHandler,
    ) -> bool:
        """Remove a subscription and report whether it existed."""

        event_type = event_type.strip()
        handlers = self._subscriptions.get(event_type)

        if not handlers or handler not in handlers:
            return False

        handlers.remove(handler)

        if not handlers:
            self._subscriptions.pop(event_type, None)

        return True

    def unsubscribe_all(self, handler: EventHandler) -> bool:
        """Remove a wildcard subscription."""

        return self.unsubscribe(WILDCARD_EVENT_TYPE, handler)

    def publish(self, event: DomainEvent) -> None:
        """Dispatch an event to all matching subscribers.

        Every matching handler is attempted. If handlers fail, dispatch
        continues and an EventDispatchError is raised afterward.
        """

        if not isinstance(event, DomainEvent):
            raise TypeError("event must be a DomainEvent.")

        handlers = self._matching_handlers(event.event_type)
        failures: list[EventDispatchFailure] = []

        for handler in handlers:
            try:
                handler(event)
            except Exception as error:
                failures.append(
                    EventDispatchFailure(
                        event=event,
                        handler=handler,
                        error=error,
                    )
                )

        if failures:
            raise EventDispatchError(event, failures)

    def subscriber_count(
        self,
        event_type: str | None = None,
    ) -> int:
        """Return the number of registered subscriptions."""

        if event_type is not None:
            return len(self._subscriptions.get(event_type.strip(), []))

        return sum(len(handlers) for handlers in self._subscriptions.values())

    def clear(self, event_type: str | None = None) -> None:
        """Remove subscriptions for one event type or the entire bus."""

        if event_type is None:
            self._subscriptions.clear()
            return

        self._subscriptions.pop(event_type.strip(), None)

    def _matching_handlers(
        self,
        event_type: str,
    ) -> list[EventHandler]:
        """Return a stable, deduplicated handler snapshot."""

        handlers = [
            *self._subscriptions.get(event_type, []),
            *self._subscriptions.get(WILDCARD_EVENT_TYPE, []),
        ]

        unique_handlers: list[EventHandler] = []

        for handler in handlers:
            if handler not in unique_handlers:
                unique_handlers.append(handler)

        return unique_handlers
