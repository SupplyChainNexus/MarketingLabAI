"""Tests for tenant application commands."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from app.commands.tenants import CreateTenantCommand
from app.database.connection import SQLiteDatabase
from app.tenants.repository import TenantRepository


class CreateTenantCommandTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.database = SQLiteDatabase(
            Path(self.temporary_directory.name) / "marketinglabai.db"
        )
        self.database.initialise()
        self.repository = TenantRepository(self.database)

    def tearDown(self) -> None:
        self.temporary_directory.cleanup()

    def test_command_creates_tenant(self) -> None:
        command = CreateTenantCommand(
            tenant_id="tenant-one",
            name="Tenant One",
            repository=self.repository,
        )

        tenant = command.execute()

        self.assertEqual(tenant.tenant_id, "tenant-one")
        self.assertEqual(tenant.name, "Tenant One")
        self.assertEqual(tenant.status, "active")
        self.assertTrue(tenant.created_at)
        self.assertTrue(tenant.updated_at)
        self.assertTrue(self.repository.exists("tenant-one"))

    def test_command_cleans_input_values(self) -> None:
        command = CreateTenantCommand(
            tenant_id=" tenant-one ",
            name=" Tenant One ",
            status=" ACTIVE ",
            repository=self.repository,
        )

        tenant = command.execute()

        self.assertEqual(tenant.tenant_id, "tenant-one")
        self.assertEqual(tenant.name, "Tenant One")
        self.assertEqual(tenant.status, "active")

    def test_command_can_create_inactive_tenant(self) -> None:
        command = CreateTenantCommand(
            tenant_id="tenant-one",
            name="Tenant One",
            status="inactive",
            repository=self.repository,
        )

        tenant = command.execute()

        self.assertEqual(tenant.status, "inactive")
        self.assertFalse(tenant.is_active)

    def test_command_rejects_duplicate_tenant(self) -> None:
        CreateTenantCommand(
            tenant_id="tenant-one",
            name="Tenant One",
            repository=self.repository,
        ).execute()

        with self.assertRaisesRegex(
            ValueError,
            "already exists",
        ):
            CreateTenantCommand(
                tenant_id="tenant-one",
                name="Duplicate Tenant",
                repository=self.repository,
            ).execute()

        self.assertEqual(self.repository.count(), 2)

    def test_command_rejects_blank_identifier(self) -> None:
        with self.assertRaisesRegex(
            ValueError,
            "tenant_id",
        ):
            CreateTenantCommand(
                tenant_id=" ",
                name="Tenant One",
                repository=self.repository,
            ).execute()

    def test_command_rejects_blank_name(self) -> None:
        with self.assertRaisesRegex(
            ValueError,
            "name",
        ):
            CreateTenantCommand(
                tenant_id="tenant-one",
                name=" ",
                repository=self.repository,
            ).execute()

    def test_command_rejects_invalid_status(self) -> None:
        with self.assertRaisesRegex(
            ValueError,
            "status",
        ):
            CreateTenantCommand(
                tenant_id="tenant-one",
                name="Tenant One",
                status="suspended",
                repository=self.repository,
            ).execute()

    def test_failed_duplicate_does_not_modify_original(self) -> None:
        original = CreateTenantCommand(
            tenant_id="tenant-one",
            name="Original Tenant",
            repository=self.repository,
        ).execute()

        with self.assertRaises(ValueError):
            CreateTenantCommand(
                tenant_id="tenant-one",
                name="Replacement Tenant",
                repository=self.repository,
            ).execute()

        restored = self.repository.get("tenant-one")

        self.assertEqual(
            restored.name,
            original.name,
        )


if __name__ == "__main__":
    unittest.main()
