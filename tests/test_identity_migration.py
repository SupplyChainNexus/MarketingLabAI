"""Tests for identity and authorization schema migration 11."""

import tempfile
import unittest
from pathlib import Path

from app.database.connection import SQLiteDatabase


class IdentityMigrationTests(unittest.TestCase):
    def test_migration_eleven_is_idempotent(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            database = SQLiteDatabase(Path(folder) / "db.sqlite")
            database.initialise()
            database.initialise()
            with database.connection() as connection:
                rows = connection.execute(
                    "SELECT description FROM schema_migrations WHERE version = 11"
                ).fetchall()
            self.assertIn("tenant_memberships", database.table_names())
            self.assertIn("authorization_audit_events", database.table_names())
            self.assertEqual(len(rows), 1)
            self.assertEqual(
                rows[0]["description"],
                "Add identity memberships and authorization audit",
            )


if __name__ == "__main__":
    unittest.main()
