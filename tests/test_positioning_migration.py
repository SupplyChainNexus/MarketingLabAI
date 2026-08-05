"""Tests for Positioning Intelligence schema migration 14."""

import tempfile
import unittest
from pathlib import Path

from app.database.connection import SQLiteDatabase


class PositioningMigrationTests(unittest.TestCase):
    def test_migration_fourteen_is_idempotent(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            database = SQLiteDatabase(Path(folder) / "db.sqlite")
            database.initialise()
            database.initialise()
            with database.connection() as connection:
                columns = {
                    row["name"]
                    for row in connection.execute(
                        "PRAGMA table_info(positioning_decisions)"
                    )
                }
                migrations = connection.execute(
                    "SELECT description FROM schema_migrations WHERE version = 14"
                ).fetchall()

        self.assertEqual(
            columns,
            {
                "positioning_id",
                "version",
                "tenant_id",
                "brand_id",
                "target_kind",
                "target_id",
                "product_id",
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
            "Add versioned Positioning Intelligence decisions",
        )


if __name__ == "__main__":
    unittest.main()
