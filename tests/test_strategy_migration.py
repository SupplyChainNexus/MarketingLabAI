"""Tests for Marketing Strategy Intelligence schema migration 15."""

import tempfile
import unittest
from pathlib import Path

from app.database.connection import SQLiteDatabase


class StrategyMigrationTests(unittest.TestCase):
    def test_migration_fifteen_is_idempotent(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            database = SQLiteDatabase(Path(folder) / "db.sqlite")
            database.initialise()
            database.initialise()
            with database.connection() as connection:
                columns = {
                    row["name"]
                    for row in connection.execute(
                        "PRAGMA table_info(strategy_decisions)"
                    )
                }
                migrations = connection.execute(
                    "SELECT description FROM schema_migrations WHERE version = 15"
                ).fetchall()
        self.assertEqual(
            columns,
            {
                "strategy_id",
                "version",
                "tenant_id",
                "brand_id",
                "positioning_id",
                "positioning_version",
                "status",
                "payload_json",
                "created_at",
                "updated_at",
                "approved_at",
            },
        )
        self.assertEqual(len(migrations), 1)
        self.assertEqual(
            migrations[0]["description"],
            "Add versioned Marketing Strategy Intelligence decisions",
        )


if __name__ == "__main__":
    unittest.main()
