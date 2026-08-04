"""Tests for the versioned Campaign Plan SQLite schema."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from app.database.connection import SQLiteDatabase


class CampaignPlanMigrationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.database = SQLiteDatabase(
            Path(self.temporary_directory.name) / "marketinglabai.db"
        )

    def tearDown(self) -> None:
        self.temporary_directory.cleanup()

    def test_initialise_creates_campaign_plans_table(self) -> None:
        self.database.initialise()
        self.assertIn("campaign_plans", self.database.table_names())

    def test_campaign_plans_table_has_expected_columns(self) -> None:
        self.database.initialise()
        with self.database.connection() as connection:
            rows = connection.execute("PRAGMA table_info(campaign_plans)").fetchall()
        self.assertEqual(
            {str(row["name"]) for row in rows},
            {
                "campaign_id", "version", "tenant_id", "brand_id", "name",
                "status", "payload_json", "created_at", "updated_at",
            },
        )

    def test_initialise_records_schema_version_nine_idempotently(self) -> None:
        self.database.initialise()
        self.database.initialise()
        with self.database.connection() as connection:
            rows = connection.execute(
                "SELECT description FROM schema_migrations WHERE version = 9"
            ).fetchall()
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["description"], "Add versioned campaign plans")


if __name__ == "__main__":
    unittest.main()
