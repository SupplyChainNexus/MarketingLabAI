"""Tests for the MarketingLabAI institutional memory engine."""

from __future__ import annotations

import sqlite3
import tempfile
import unittest
from pathlib import Path

from app.database.connection import SQLiteDatabase
from app.database.repositories import BrandRepository, MemoryRepository
from app.memory.constants import MemoryEventType
from app.memory.models import MemoryEvent


class MemoryEventModelTests(unittest.TestCase):
    def test_memory_event_round_trip(self) -> None:
        event = MemoryEvent(
            memory_id="memory-1",
            brand_id="test-brand",
            event_type=MemoryEventType.CAMPAIGN_CREATED,
            source="campaign-engine",
            summary="A campaign was created.",
            payload={"campaign_id": "campaign-1"},
        )

        restored = MemoryEvent.from_dict(event.to_dict())

        self.assertEqual(restored.memory_id, "memory-1")
        self.assertEqual(restored.brand_id, "test-brand")
        self.assertEqual(
            restored.payload,
            {"campaign_id": "campaign-1"},
        )

    def test_memory_event_rejects_missing_required_fields(self) -> None:
        with self.assertRaisesRegex(ValueError, "memory_id"):
            MemoryEvent(
                memory_id="",
                brand_id="test-brand",
                event_type="campaign.created",
                source="campaign-engine",
                summary="Created.",
            )

    def test_memory_event_rejects_non_dictionary_payload(self) -> None:
        with self.assertRaisesRegex(TypeError, "dictionary"):
            MemoryEvent(
                memory_id="memory-1",
                brand_id="test-brand",
                event_type="campaign.created",
                source="campaign-engine",
                summary="Created.",
                payload=["invalid"],  # type: ignore[arg-type]
            )


class MemoryRepositoryTests(unittest.TestCase):
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

    def create_event(
        self,
        *,
        memory_id: str = "memory-1",
        event_type: str = MemoryEventType.CAMPAIGN_CREATED,
        summary: str = "A campaign was created.",
    ) -> MemoryEvent:
        return MemoryEvent(
            memory_id=memory_id,
            brand_id="test-brand",
            event_type=event_type,
            source="campaign-engine",
            summary=summary,
            payload={
                "campaign_id": "campaign-1",
                "objective": "Awareness",
            },
        )

    def test_repository_round_trip(self) -> None:
        event = self.create_event()

        self.memory_repository.save(event)
        restored = self.memory_repository.get("memory-1")

        self.assertEqual(restored.memory_id, event.memory_id)
        self.assertEqual(restored.event_type, event.event_type)
        self.assertEqual(restored.payload, event.payload)
        self.assertTrue(restored.created_at)

    def test_repository_is_append_only(self) -> None:
        event = self.create_event()

        self.memory_repository.save(event)

        with self.assertRaisesRegex(ValueError, "already exists"):
            self.memory_repository.save(event)

        self.assertEqual(
            self.memory_repository.count("test-brand"),
            1,
        )

    def test_list_returns_brand_events(self) -> None:
        self.memory_repository.save(self.create_event(memory_id="memory-1"))
        self.memory_repository.save(
            self.create_event(
                memory_id="memory-2",
                event_type=MemoryEventType.COMPLIANCE_PASSED,
                summary="Campaign compliance passed.",
            )
        )

        events = self.memory_repository.list("test-brand")

        self.assertEqual(len(events), 2)
        self.assertEqual(
            {event.memory_id for event in events},
            {"memory-1", "memory-2"},
        )

    def test_list_filters_by_event_type(self) -> None:
        self.memory_repository.save(self.create_event(memory_id="memory-1"))
        self.memory_repository.save(
            self.create_event(
                memory_id="memory-2",
                event_type=MemoryEventType.COMPLIANCE_PASSED,
                summary="Campaign compliance passed.",
            )
        )

        events = self.memory_repository.list(
            "test-brand",
            event_type=MemoryEventType.COMPLIANCE_PASSED,
        )

        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].memory_id, "memory-2")

    def test_search_finds_summary_and_payload_content(self) -> None:
        self.memory_repository.save(self.create_event())

        summary_results = self.memory_repository.search(
            "test-brand",
            "campaign was created",
        )
        payload_results = self.memory_repository.search(
            "test-brand",
            "Awareness",
        )

        self.assertEqual(len(summary_results), 1)
        self.assertEqual(len(payload_results), 1)

    def test_count_filters_by_brand_and_event_type(self) -> None:
        self.memory_repository.save(self.create_event(memory_id="memory-1"))
        self.memory_repository.save(
            self.create_event(
                memory_id="memory-2",
                event_type=MemoryEventType.COMPLIANCE_PASSED,
                summary="Campaign compliance passed.",
            )
        )

        self.assertEqual(
            self.memory_repository.count("test-brand"),
            2,
        )
        self.assertEqual(
            self.memory_repository.count(
                "test-brand",
                event_type=MemoryEventType.COMPLIANCE_PASSED,
            ),
            1,
        )

    def test_deleting_brand_deletes_memory_events(self) -> None:
        self.memory_repository.save(self.create_event())

        with self.database.transaction() as connection:
            connection.execute(
                "DELETE FROM brands WHERE brand_id = ?",
                ("test-brand",),
            )

        self.assertEqual(
            self.memory_repository.count("test-brand"),
            0,
        )


class MemorySchemaMigrationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.database_path = Path(self.temporary_directory.name) / "marketinglabai.db"

    def tearDown(self) -> None:
        self.temporary_directory.cleanup()

    def test_initialise_adds_memory_schema_to_existing_database(self) -> None:
        connection = sqlite3.connect(self.database_path)
        connection.executescript("""
            CREATE TABLE schema_migrations (
                version INTEGER PRIMARY KEY,
                description TEXT NOT NULL,
                applied_at TEXT NOT NULL
            );

            CREATE TABLE brands (
                brand_id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                industry TEXT NOT NULL DEFAULT '',
                description TEXT NOT NULL DEFAULT '',
                target_audience_json TEXT NOT NULL DEFAULT '[]',
                products_json TEXT NOT NULL DEFAULT '[]',
                values_json TEXT NOT NULL DEFAULT '[]',
                website TEXT NOT NULL DEFAULT '',
                payload_json TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );

            INSERT INTO schema_migrations (
                version,
                description,
                applied_at
            )
            VALUES (
                1,
                'Initial MarketingLabAI relational schema',
                '2026-01-01T00:00:00+00:00'
            );
            """)
        connection.commit()
        connection.close()

        database = SQLiteDatabase(self.database_path)
        database.initialise()

        self.assertIn("memory_events", database.table_names())

        with database.connection() as migrated_connection:
            row = migrated_connection.execute("""
                SELECT description
                FROM schema_migrations
                WHERE version = 3
                """).fetchone()

        self.assertIsNotNone(row)
        self.assertEqual(
            row["description"],
            "Add institutional memory events",
        )


if __name__ == "__main__":
    unittest.main()
