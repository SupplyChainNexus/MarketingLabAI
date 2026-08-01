"""Tests for Prompt Pack database schema migration."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from app.database.connection import SQLiteDatabase


class PromptPackMigrationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.database = SQLiteDatabase(
            Path(self.temporary_directory.name) / "marketinglabai.db"
        )

    def tearDown(self) -> None:
        self.temporary_directory.cleanup()

    def test_initialise_creates_prompt_pack_table(
        self,
    ) -> None:
        self.database.initialise()

        self.assertIn(
            "prompt_packs",
            self.database.table_names(),
        )

    def test_prompt_pack_table_has_expected_columns(
        self,
    ) -> None:
        self.database.initialise()

        with self.database.connection() as connection:
            rows = connection.execute("PRAGMA table_info(prompt_packs)").fetchall()

        columns = {str(row["name"]) for row in rows}

        self.assertEqual(
            columns,
            {
                "prompt_pack_id",
                "version",
                "tenant_id",
                "brand_id",
                "name",
                "task_type",
                "channel",
                "enabled",
                "payload_json",
                "created_at",
                "updated_at",
            },
        )

    def test_initialise_records_schema_version_six(
        self,
    ) -> None:
        self.database.initialise()

        with self.database.connection() as connection:
            row = connection.execute("""
                SELECT description
                FROM schema_migrations
                WHERE version = 6
                """).fetchone()

        self.assertIsNotNone(row)
        self.assertEqual(
            row["description"],
            "Add versioned prompt packs",
        )

    def test_prompt_pack_schema_is_idempotent(
        self,
    ) -> None:
        self.database.initialise()
        self.database.initialise()

        with self.database.connection() as connection:
            row = connection.execute("""
                SELECT COUNT(*) AS total
                FROM schema_migrations
                WHERE version = 6
                """).fetchone()

        self.assertEqual(
            int(row["total"]),
            1,
        )


if __name__ == "__main__":
    unittest.main()
