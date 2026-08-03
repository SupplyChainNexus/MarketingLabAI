"Tests for Marketing Brief SQLite schema migration."

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from app.database.connection import SQLiteDatabase


class MarketingBriefMigrationTests(unittest.TestCase):
    "Validate the versioned Marketing Brief schema."

    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.database = SQLiteDatabase(
            Path(self.temporary_directory.name) / "marketinglabai.db"
        )

    def tearDown(self) -> None:
        self.temporary_directory.cleanup()

    def test_initialise_creates_marketing_briefs_table(
        self,
    ) -> None:
        self.database.initialise()

        self.assertIn(
            "marketing_briefs",
            self.database.table_names(),
        )

    def test_marketing_briefs_table_has_expected_columns(
        self,
    ) -> None:
        self.database.initialise()

        with self.database.connection() as connection:
            rows = connection.execute("PRAGMA table_info(marketing_briefs)").fetchall()

        columns = {str(row["name"]) for row in rows}

        self.assertEqual(
            columns,
            {
                "brief_id",
                "version",
                "tenant_id",
                "brand_id",
                "name",
                "status",
                "payload_json",
                "created_at",
                "updated_at",
            },
        )

    def test_initialise_records_schema_version_eight(
        self,
    ) -> None:
        self.database.initialise()

        with self.database.connection() as connection:
            row = connection.execute("""
                SELECT description
                FROM schema_migrations
                WHERE version = 8
                """).fetchone()

        self.assertIsNotNone(row)
        self.assertEqual(
            row["description"],
            "Add versioned marketing briefs",
        )

    def test_marketing_brief_schema_is_idempotent(
        self,
    ) -> None:
        self.database.initialise()
        self.database.initialise()

        with self.database.connection() as connection:
            row = connection.execute("""
                SELECT COUNT(*) AS total
                FROM schema_migrations
                WHERE version = 8
                """).fetchone()

        self.assertEqual(int(row["total"]), 1)


if __name__ == "__main__":
    unittest.main()
