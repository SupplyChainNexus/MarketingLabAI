"""Tests for the domain event publisher."""

from __future__ import annotations

import unittest

from app.events.brand_events import BrandCreatedEvent
from app.events.bus import EventBus
from app.events.publisher import EventPublisher


class EventPublisherTests(unittest.TestCase):
    def test_publish_delivers_event(self) -> None:
        received: list[BrandCreatedEvent] = []
        event_bus = EventBus()

        event_bus.subscribe(
            "brand.created",
            received.append,
        )

        publisher = EventPublisher(event_bus)
        event = BrandCreatedEvent(
            tenant_id="default",
            brand_id="brand-one",
            brand_name="Brand One",
        )

        publisher.publish(event)

        self.assertEqual(received, [event])


if __name__ == "__main__":
    unittest.main()
