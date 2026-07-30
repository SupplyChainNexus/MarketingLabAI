"""Tests for the MarketingLabAI domain event bus."""

from __future__ import annotations

import tempfile
import unittest
from dataclasses import FrozenInstanceError
from pathlib import Path
from unittest.mock import Mock

from app.database.connection import SQLiteDatabase
from app.database.repositories import BrandRepository, MemoryRepository
from app.events.bus import EventBus, EventDispatchError
from app.events.memory import MemoryEventRecorder
from app.events.models import DomainEvent
from app.memory.constants import MemoryEventType


class DomainEventTests(unittest.TestCase):
    def test_domain_event_round_trip(self) -> None:
        event = DomainEvent(
            event_id="event-1",
            event_type=MemoryEventType.CAMPAIGN_CREATED,
            brand_id="test-brand",
            source="campaign-engine",
            summary="Campaign created.",
            payload={"campaign_id": "campaign-1"},
            occurred_at="2026-07-30T10:00:00+00:00",
        )

        restored = DomainEvent.from_dict(event.to_dict())

        self.assertEqual(restored.event_id, "event-1")
        self.assertEqual(restored.brand_id, "test-brand")
        self.assertEqual(
            dict(restored.payload),
            {"campaign_id": "campaign-1"},
        )

    def test_domain_event_generates_identity_and_timestamp(self) -> None:
        event = DomainEvent(
            event_type="test.created",
            brand_id="test-brand",
            source="test-suite",
            summary="Test event created.",
        )

        self.assertTrue(event.event_id)
        self.assertTrue(event.occurred_at)

    def test_domain_event_is_immutable(self) -> None:
        event = DomainEvent(
            event_type="test.created",
            brand_id="test-brand",
            source="test-suite",
            summary="Test event created.",
        )

        with self.assertRaises(FrozenInstanceError):
            event.summary = "Changed"  # type: ignore[misc]

        with self.assertRaises(TypeError):
            event.payload["changed"] = True  # type: ignore[index]

    def test_domain_event_rejects_missing_required_fields(self) -> None:
        with self.assertRaisesRegex(ValueError, "event_type"):
            DomainEvent(
                event_type="",
                brand_id="test-brand",
                source="test-suite",
                summary="Test event.",
            )

    def test_domain_event_rejects_non_mapping_payload(self) -> None:
        with self.assertRaisesRegex(TypeError, "mapping"):
            DomainEvent(
                event_type="test.created",
                brand_id="test-brand",
                source="test-suite",
                summary="Test event.",
                payload=["invalid"],  # type: ignore[arg-type]
            )


class EventBusTests(unittest.TestCase):
    def setUp(self) -> None:
        self.bus = EventBus()
        self.event = DomainEvent(
            event_id="event-1",
            event_type="campaign.created",
            brand_id="test-brand",
            source="campaign-engine",
            summary="Campaign created.",
        )

    def test_publish_calls_matching_handler(self) -> None:
        handler = Mock()
        self.bus.subscribe("campaign.created", handler)

        self.bus.publish(self.event)

        handler.assert_called_once_with(self.event)

    def test_publish_does_not_call_unrelated_handler(self) -> None:
        handler = Mock()
        self.bus.subscribe("campaign.published", handler)

        self.bus.publish(self.event)

        handler.assert_not_called()

    def test_wildcard_handler_receives_every_event(self) -> None:
        handler = Mock()
        self.bus.subscribe_all(handler)

        self.bus.publish(self.event)

        handler.assert_called_once_with(self.event)

    def test_duplicate_subscription_is_ignored(self) -> None:
        handler = Mock()

        self.bus.subscribe("campaign.created", handler)
        self.bus.subscribe("campaign.created", handler)

        self.assertEqual(
            self.bus.subscriber_count("campaign.created"),
            1,
        )

        self.bus.publish(self.event)

        handler.assert_called_once_with(self.event)

    def test_same_handler_is_not_called_twice_for_exact_and_wildcard(self) -> None:
        handler = Mock()

        self.bus.subscribe("campaign.created", handler)
        self.bus.subscribe_all(handler)

        self.bus.publish(self.event)

        handler.assert_called_once_with(self.event)

    def test_unsubscribe_removes_handler(self) -> None:
        handler = Mock()
        self.bus.subscribe("campaign.created", handler)

        removed = self.bus.unsubscribe(
            "campaign.created",
            handler,
        )

        self.assertTrue(removed)

        self.bus.publish(self.event)

        handler.assert_not_called()

    def test_unsubscribe_reports_missing_subscription(self) -> None:
        handler = Mock()

        removed = self.bus.unsubscribe(
            "campaign.created",
            handler,
        )

        self.assertFalse(removed)

    def test_clear_removes_all_subscriptions(self) -> None:
        first_handler = Mock()
        second_handler = Mock()

        self.bus.subscribe("campaign.created", first_handler)
        self.bus.subscribe_all(second_handler)

        self.bus.clear()

        self.assertEqual(self.bus.subscriber_count(), 0)

    def test_failing_handler_does_not_stop_later_handlers(self) -> None:
        calls: list[str] = []

        def failing_handler(_: DomainEvent) -> None:
            calls.append("failed")
            raise RuntimeError("Handler failure")

        def successful_handler(_: DomainEvent) -> None:
            calls.append("succeeded")

        self.bus.subscribe("campaign.created", failing_handler)
        self.bus.subscribe("campaign.created", successful_handler)

        with self.assertRaises(EventDispatchError) as context:
            self.bus.publish(self.event)

        self.assertEqual(calls, ["failed", "succeeded"])
        self.assertEqual(len(context.exception.failures), 1)
        self.assertIsInstance(
            context.exception.failures[0].error,
            RuntimeError,
        )

    def test_publish_rejects_non_event(self) -> None:
        with self.assertRaisesRegex(TypeError, "DomainEvent"):
            self.bus.publish("invalid")  # type: ignore[arg-type]


class MemoryEventRecorderTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.database = SQLiteDatabase(
            Path(self.temporary_directory.name) / "marketinglabai.db"
        )
        self.database.initialise()

        self.brand_repository = BrandRepository(self.database)
        self.memory_repository = MemoryRepository(self.database)

        self.brand_repository.save(
            {
                "brand_id": "test-brand",
                "name": "Test Brand",
            }
        )

    def tearDown(self) -> None:
        self.temporary_directory.cleanup()

    def test_recorder_stores_domain_event_in_memory(self) -> None:
        recorder = MemoryEventRecorder(self.memory_repository)
        bus = EventBus()
        bus.subscribe_all(recorder)

        event = DomainEvent(
            event_id="campaign-event-1",
            event_type=MemoryEventType.CAMPAIGN_CREATED,
            brand_id="test-brand",
            source="campaign-engine",
            summary="Campaign created.",
            payload={"campaign_id": "campaign-1"},
            occurred_at="2026-07-30T10:00:00+00:00",
        )

        bus.publish(event)

        stored = self.memory_repository.get("event-campaign-event-1")

        self.assertEqual(
            stored.event_type,
            MemoryEventType.CAMPAIGN_CREATED,
        )
        self.assertEqual(stored.source, "campaign-engine")
        self.assertEqual(
            stored.payload["campaign_id"],
            "campaign-1",
        )
        self.assertEqual(
            stored.payload["domain_event_id"],
            "campaign-event-1",
        )
        self.assertEqual(
            stored.created_at,
            "2026-07-30T10:00:00+00:00",
        )

    def test_recorder_preserves_append_only_memory(self) -> None:
        recorder = MemoryEventRecorder(self.memory_repository)
        bus = EventBus()
        bus.subscribe_all(recorder)

        event = DomainEvent(
            event_id="campaign-event-1",
            event_type=MemoryEventType.CAMPAIGN_CREATED,
            brand_id="test-brand",
            source="campaign-engine",
            summary="Campaign created.",
        )

        bus.publish(event)

        with self.assertRaises(EventDispatchError) as context:
            bus.publish(event)

        self.assertEqual(len(context.exception.failures), 1)
        self.assertIsInstance(
            context.exception.failures[0].error,
            ValueError,
        )
        self.assertEqual(
            self.memory_repository.count("test-brand"),
            1,
        )


if __name__ == "__main__":
    unittest.main()
