from pathlib import Path


def replace_once(path: Path, old: str, new: str) -> None:
    content = path.read_text(encoding="utf-8")

    if old not in content:
        raise RuntimeError(
            f"Could not find the expected insertion point in {path}."
        )

    path.write_text(
        content.replace(old, new, 1),
        encoding="utf-8",
    )


def append_once(path: Path, marker: str, content: str) -> None:
    existing = path.read_text(encoding="utf-8")

    if marker in existing:
        print(f"Skipped existing change in {path}")
        return

    path.write_text(
        existing.rstrip() + "\n\n\n" + content.strip() + "\n",
        encoding="utf-8",
    )


project_root = Path.cwd()

connection_path = project_root / "app" / "database" / "connection.py"
repositories_path = project_root / "app" / "database" / "repositories.py"
sqlite_tests_path = project_root / "tests" / "test_sqlite_database.py"

memory_directory = project_root / "app" / "memory"
memory_directory.mkdir(parents=True, exist_ok=True)

(memory_directory / "__init__.py").write_text(
    '''"""Institutional memory services for MarketingLabAI."""

from app.memory.constants import MemoryEventType
from app.memory.models import MemoryEvent

__all__ = [
    "MemoryEvent",
    "MemoryEventType",
]
''',
    encoding="utf-8",
)

(memory_directory / "constants.py").write_text(
    '''"""Standard event types used by the MarketingLabAI memory engine."""

from enum import StrEnum


class MemoryEventType(StrEnum):
    """Recognised institutional memory event types."""

    CAMPAIGN_CREATED = "campaign.created"
    CAMPAIGN_APPROVED = "campaign.approved"
    CAMPAIGN_PUBLISHED = "campaign.published"
    CAMPAIGN_PERFORMANCE_RECORDED = "campaign.performance_recorded"
    COMPLIANCE_PASSED = "compliance.passed"
    COMPLIANCE_FAILED = "compliance.failed"
    COMPANY_BRAIN_UPDATED = "company_brain.updated"
    VOICE_UPDATED = "voice.updated"
    RESEARCH_IMPORTED = "research.imported"
    CUSTOMER_FEEDBACK_ADDED = "customer_feedback.added"
''',
    encoding="utf-8",
)

(memory_directory / "models.py").write_text(
    '''"""Domain models for the MarketingLabAI memory engine."""

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
''',
    encoding="utf-8",
)

table_anchor = '''                CREATE TABLE IF NOT EXISTS data_migration_log (
'''

memory_table = '''                CREATE TABLE IF NOT EXISTS memory_events (
                    memory_id TEXT PRIMARY KEY,
                    brand_id TEXT NOT NULL,
                    event_type TEXT NOT NULL,
                    source TEXT NOT NULL,
                    summary TEXT NOT NULL,
                    payload_json TEXT NOT NULL DEFAULT '{}',
                    created_at TEXT NOT NULL,
                    FOREIGN KEY (brand_id)
                        REFERENCES brands(brand_id)
                        ON DELETE CASCADE
                );

                CREATE TABLE IF NOT EXISTS data_migration_log (
'''

replace_once(connection_path, table_anchor, memory_table)

index_anchor = '''                CREATE INDEX IF NOT EXISTS idx_data_migration_log_record
                    ON data_migration_log(source_type, record_id);
'''

memory_indexes = '''                CREATE INDEX IF NOT EXISTS idx_memory_events_brand
                    ON memory_events(brand_id);

                CREATE INDEX IF NOT EXISTS idx_memory_events_type
                    ON memory_events(brand_id, event_type);

                CREATE INDEX IF NOT EXISTS idx_memory_events_created
                    ON memory_events(brand_id, created_at);

                CREATE INDEX IF NOT EXISTS idx_data_migration_log_record
                    ON data_migration_log(source_type, record_id);
'''

replace_once(connection_path, index_anchor, memory_indexes)

migration_anchor = '''            connection.execute(
                """
                INSERT OR IGNORE INTO schema_migrations (
                    version,
                    description,
                    applied_at
                )
                VALUES (
                    2,
                    'Add versioned compliance rules',
                    strftime('%Y-%m-%dT%H:%M:%fZ', 'now')
                )
                """
            )
'''

migration_replacement = migration_anchor + '''

            connection.execute(
                """
                INSERT OR IGNORE INTO schema_migrations (
                    version,
                    description,
                    applied_at
                )
                VALUES (
                    3,
                    'Add institutional memory events',
                    strftime('%Y-%m-%dT%H:%M:%fZ', 'now')
                )
                """
            )
'''

replace_once(connection_path, migration_anchor, migration_replacement)

repository_import_anchor = (
    "from app.intelligence.models import BusinessIntelligenceProfile\n"
)

repository_import_replacement = (
    "from app.intelligence.models import BusinessIntelligenceProfile\n"
    "from app.memory.models import MemoryEvent\n"
)

replace_once(
    repositories_path,
    repository_import_anchor,
    repository_import_replacement,
)

memory_repository = '''
class MemoryRepository:
    """Store and retrieve institutional memory events in SQLite."""

    def __init__(self, database: SQLiteDatabase | None = None) -> None:
        self.database = database or SQLiteDatabase()
        self.database.initialise()

    def save(self, event: MemoryEvent) -> None:
        """Store a new memory event.

        Memory records are append-only. Existing IDs cannot be overwritten.
        """

        if not isinstance(event, MemoryEvent):
            raise TypeError("event must be a MemoryEvent.")

        timestamp = event.created_at or current_utc_timestamp()
        payload = event.to_dict()
        payload["created_at"] = timestamp

        with self.database.transaction() as connection:
            try:
                connection.execute(
                    """
                    INSERT INTO memory_events (
                        memory_id,
                        brand_id,
                        event_type,
                        source,
                        summary,
                        payload_json,
                        created_at
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        event.memory_id,
                        event.brand_id,
                        event.event_type,
                        event.source,
                        event.summary,
                        encode_json(payload),
                        timestamp,
                    ),
                )
            except Exception as error:
                if "UNIQUE constraint failed" in str(error):
                    raise ValueError(
                        f"A memory event with ID "
                        f"'{event.memory_id}' already exists."
                    ) from error

                raise

        event.created_at = timestamp

    def get(self, memory_id: str) -> MemoryEvent:
        """Return one memory event by ID."""

        with self.database.connection() as connection:
            row = connection.execute(
                """
                SELECT payload_json
                FROM memory_events
                WHERE memory_id = ?
                """,
                (memory_id,),
            ).fetchone()

        if row is None:
            raise FileNotFoundError(
                f"No memory event exists with ID '{memory_id}'."
            )

        payload = decode_json(str(row["payload_json"]))

        if not isinstance(payload, dict):
            raise ValueError(
                f"Invalid stored memory payload for '{memory_id}'."
            )

        return MemoryEvent.from_dict(payload)

    def list(
        self,
        brand_id: str,
        *,
        event_type: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[MemoryEvent]:
        """Return memory events for a brand, newest first."""

        if limit < 1:
            raise ValueError("limit must be at least 1.")

        if offset < 0:
            raise ValueError("offset cannot be negative.")

        query = """
            SELECT payload_json
            FROM memory_events
            WHERE brand_id = ?
        """
        parameters: list[Any] = [brand_id]

        if event_type is not None:
            query += " AND event_type = ?"
            parameters.append(event_type)

        query += """
            ORDER BY created_at DESC, memory_id DESC
            LIMIT ? OFFSET ?
        """
        parameters.extend([limit, offset])

        with self.database.connection() as connection:
            rows = connection.execute(
                query,
                tuple(parameters),
            ).fetchall()

        return [
            MemoryEvent.from_dict(
                decode_json(str(row["payload_json"]))
            )
            for row in rows
        ]

    def search(
        self,
        brand_id: str,
        search_text: str,
        *,
        limit: int = 50,
    ) -> list[MemoryEvent]:
        """Search summaries, sources, event types, and JSON payloads."""

        search_text = search_text.strip()

        if not search_text:
            return []

        if limit < 1:
            raise ValueError("limit must be at least 1.")

        pattern = f"%{search_text}%"

        with self.database.connection() as connection:
            rows = connection.execute(
                """
                SELECT payload_json
                FROM memory_events
                WHERE brand_id = ?
                  AND (
                      summary LIKE ?
                      OR source LIKE ?
                      OR event_type LIKE ?
                      OR payload_json LIKE ?
                  )
                ORDER BY created_at DESC, memory_id DESC
                LIMIT ?
                """,
                (
                    brand_id,
                    pattern,
                    pattern,
                    pattern,
                    pattern,
                    limit,
                ),
            ).fetchall()

        return [
            MemoryEvent.from_dict(
                decode_json(str(row["payload_json"]))
            )
            for row in rows
        ]

    def count(
        self,
        brand_id: str | None = None,
        *,
        event_type: str | None = None,
    ) -> int:
        """Return the number of matching memory events."""

        query = "SELECT COUNT(*) AS total FROM memory_events"
        conditions: list[str] = []
        parameters: list[Any] = []

        if brand_id is not None:
            conditions.append("brand_id = ?")
            parameters.append(brand_id)

        if event_type is not None:
            conditions.append("event_type = ?")
            parameters.append(event_type)

        if conditions:
            query += " WHERE " + " AND ".join(conditions)

        with self.database.connection() as connection:
            row = connection.execute(
                query,
                tuple(parameters),
            ).fetchone()

        return int(row["total"]) if row else 0
'''

append_once(
    repositories_path,
    "class MemoryRepository:",
    memory_repository,
)

old_table_expectation = '''            [
                "brands",
                "business_intelligence_profiles",
                "compliance_rules",
                "data_migration_log",
                "schema_migrations",
            ],
'''

new_table_expectation = '''            [
                "brands",
                "business_intelligence_profiles",
                "compliance_rules",
                "data_migration_log",
                "memory_events",
                "schema_migrations",
            ],
'''

replace_once(
    sqlite_tests_path,
    old_table_expectation,
    new_table_expectation,
)

(project_root / "tests" / "test_memory_engine.py").write_text(
    '''"""Tests for the MarketingLabAI institutional memory engine."""

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
        self.memory_repository.save(
            self.create_event(memory_id="memory-1")
        )
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
        self.memory_repository.save(
            self.create_event(memory_id="memory-1")
        )
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
        self.memory_repository.save(
            self.create_event(memory_id="memory-1")
        )
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
        self.database_path = (
            Path(self.temporary_directory.name) / "marketinglabai.db"
        )

    def tearDown(self) -> None:
        self.temporary_directory.cleanup()

    def test_initialise_adds_memory_schema_to_existing_database(self) -> None:
        connection = sqlite3.connect(self.database_path)
        connection.executescript(
            """
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
            """
        )
        connection.commit()
        connection.close()

        database = SQLiteDatabase(self.database_path)
        database.initialise()

        self.assertIn("memory_events", database.table_names())

        with database.connection() as migrated_connection:
            row = migrated_connection.execute(
                """
                SELECT description
                FROM schema_migrations
                WHERE version = 3
                """
            ).fetchone()

        self.assertIsNotNone(row)
        self.assertEqual(
            row["description"],
            "Add institutional memory events",
        )


if __name__ == "__main__":
    unittest.main()
''',
    encoding="utf-8",
)

print("Memory Engine v1 files created and updated successfully.")
