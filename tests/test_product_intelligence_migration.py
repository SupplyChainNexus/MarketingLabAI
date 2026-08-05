"""Tests for Product Intelligence schema migration 10."""

import tempfile
import unittest
from pathlib import Path

from app.database.connection import SQLiteDatabase


class ProductIntelligenceMigrationTests(unittest.TestCase):
    def test_initialise_creates_schema_and_records_version_ten_idempotently(self):
        with tempfile.TemporaryDirectory() as folder:
            database = SQLiteDatabase(Path(folder) / "db.sqlite")
            database.initialise()
            database.initialise()
            with database.connection() as connection:
                columns = {
                    row["name"]
                    for row in connection.execute(
                        "PRAGMA table_info(product_intelligence_profiles)"
                    )
                }
                migrations = connection.execute(
                    "SELECT description FROM schema_migrations WHERE version = 10"
                ).fetchall()

        self.assertEqual(
            columns, {"tenant_id", "brand_id", "payload_json", "updated_at"}
        )
        self.assertEqual(len(migrations), 1)
        self.assertEqual(
            migrations[0]["description"], "Add verified Product Intelligence profiles"
        )


if __name__ == "__main__":
    unittest.main()
