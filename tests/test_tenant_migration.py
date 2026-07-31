"""Tests for tenant database migration."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from app.database.connection import SQLiteDatabase
from app.tenants.models import DEFAULT_TENANT_ID
from app.tenants.repository import TenantRepository


class TenantMigrationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.database = SQLiteDatabase(
            Path(self.temporary_directory.name) / "marketinglabai.db"
        )

    def tearDown(self) -> None:
        self.temporary_directory.cleanup()

    def test_initialise_creates_tenants_table(self) -> None:
        self.database.initialise()

        self.assertIn(
            "tenants",
            self.database.table_names(),
        )

    def test_initialise_creates_default_tenant(self) -> None:
        self.database.initialise()

        repository = TenantRepository(self.database)
        tenant = repository.get(DEFAULT_TENANT_ID)

        self.assertEqual(tenant.name, "Default Tenant")
        self.assertEqual(tenant.status, "active")
        self.assertTrue(tenant.created_at)
        self.assertTrue(tenant.updated_at)

    def test_initialise_records_schema_version_four(self) -> None:
        self.database.initialise()

        with self.database.connection() as connection:
            row = connection.execute("""
                SELECT description
                FROM schema_migrations
                WHERE version = 4
                """).fetchone()

        self.assertIsNotNone(row)
        self.assertEqual(
            row["description"],
            "Add tenant persistence foundation",
        )

    def test_migration_is_idempotent(self) -> None:
        self.database.initialise()
        self.database.initialise()

        repository = TenantRepository(self.database)

        self.assertEqual(repository.count(), 1)


if __name__ == "__main__":
    unittest.main()
