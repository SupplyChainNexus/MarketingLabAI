"""Tests for the SQLite tenant repository."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from app.database.connection import SQLiteDatabase
from app.tenants.models import Tenant
from app.tenants.repository import TenantRepository


class TenantRepositoryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.database = SQLiteDatabase(
            Path(self.temporary_directory.name) / "marketinglabai.db"
        )
        self.database.initialise()

        self.repository = TenantRepository(self.database)

    def tearDown(self) -> None:
        self.temporary_directory.cleanup()

    def test_repository_saves_and_loads_tenant(self) -> None:
        tenant = Tenant(
            tenant_id="tenant-one",
            name="Tenant One",
        )

        self.repository.save(tenant)
        restored = self.repository.get("tenant-one")

        self.assertEqual(restored.tenant_id, "tenant-one")
        self.assertEqual(restored.name, "Tenant One")
        self.assertEqual(restored.status, "active")
        self.assertTrue(restored.created_at)
        self.assertTrue(restored.updated_at)

    def test_repository_updates_existing_tenant(self) -> None:
        tenant = Tenant(
            tenant_id="tenant-one",
            name="Original Name",
        )
        self.repository.save(tenant)

        tenant.name = "Updated Name"
        tenant.status = "inactive"
        self.repository.save(tenant)

        restored = self.repository.get("tenant-one")

        self.assertEqual(restored.name, "Updated Name")
        self.assertEqual(restored.status, "inactive")
        self.assertEqual(self.repository.count(), 2)

    def test_repository_reports_tenant_existence(self) -> None:
        self.assertFalse(self.repository.exists("tenant-one"))

        self.repository.save(
            Tenant(
                tenant_id="tenant-one",
                name="Tenant One",
            )
        )

        self.assertTrue(self.repository.exists("tenant-one"))

    def test_repository_lists_tenants_in_identifier_order(self) -> None:
        self.repository.save(
            Tenant(
                tenant_id="tenant-two",
                name="Tenant Two",
            )
        )
        self.repository.save(
            Tenant(
                tenant_id="tenant-one",
                name="Tenant One",
            )
        )

        tenants = self.repository.list()

        self.assertEqual(
            [tenant.tenant_id for tenant in tenants],
            ["default", "tenant-one", "tenant-two"],
        )

    def test_repository_counts_tenants(self) -> None:
        self.repository.save(
            Tenant(
                tenant_id="tenant-one",
                name="Tenant One",
            )
        )
        self.repository.save(
            Tenant(
                tenant_id="tenant-two",
                name="Tenant Two",
            )
        )

        self.assertEqual(self.repository.count(), 3)

    def test_repository_raises_for_missing_tenant(self) -> None:
        with self.assertRaisesRegex(
            FileNotFoundError,
            "missing-tenant",
        ):
            self.repository.get("missing-tenant")

    def test_repository_rejects_invalid_object(self) -> None:
        with self.assertRaisesRegex(TypeError, "Tenant"):
            self.repository.save({"tenant_id": "tenant-one"})  # type: ignore[arg-type]


if __name__ == "__main__":
    unittest.main()
