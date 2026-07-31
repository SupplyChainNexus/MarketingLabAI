"""Tests for tenant ownership of brands."""

from __future__ import annotations

import sqlite3
import tempfile
import unittest
from pathlib import Path

from app.database.connection import SQLiteDatabase
from app.database.repositories import BrandRepository
from app.tenants.models import DEFAULT_TENANT_ID, Tenant
from app.tenants.repository import TenantRepository


class BrandOwnershipTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.database = SQLiteDatabase(
            Path(self.temporary_directory.name) / "marketinglabai.db"
        )
        self.database.initialise()

        self.tenants = TenantRepository(self.database)
        self.brands = BrandRepository(self.database)

    def tearDown(self) -> None:
        self.temporary_directory.cleanup()

    def test_brand_defaults_to_default_tenant(self) -> None:
        self.brands.save(
            {
                "brand_id": "brand-one",
                "name": "Brand One",
            }
        )

        self.assertEqual(
            self.brands.tenant_id_for("brand-one"),
            DEFAULT_TENANT_ID,
        )

    def test_brand_can_belong_to_explicit_tenant(self) -> None:
        self.tenants.save(
            Tenant(
                tenant_id="tenant-one",
                name="Tenant One",
            )
        )

        self.brands.save(
            {
                "brand_id": "brand-one",
                "tenant_id": "tenant-one",
                "name": "Brand One",
            }
        )

        self.assertEqual(
            self.brands.tenant_id_for("brand-one"),
            "tenant-one",
        )

    def test_unknown_tenant_is_rejected(self) -> None:
        with self.assertRaisesRegex(
            sqlite3.IntegrityError,
            "Unknown tenant_id",
        ):
            self.brands.save(
                {
                    "brand_id": "brand-one",
                    "tenant_id": "missing-tenant",
                    "name": "Brand One",
                }
            )

    def test_list_ids_can_filter_by_tenant(self) -> None:
        self.tenants.save(
            Tenant(
                tenant_id="tenant-one",
                name="Tenant One",
            )
        )

        self.brands.save(
            {
                "brand_id": "default-brand",
                "name": "Default Brand",
            }
        )
        self.brands.save(
            {
                "brand_id": "tenant-brand",
                "tenant_id": "tenant-one",
                "name": "Tenant Brand",
            }
        )

        self.assertEqual(
            self.brands.list_ids(DEFAULT_TENANT_ID),
            ["default-brand"],
        )
        self.assertEqual(
            self.brands.list_ids("tenant-one"),
            ["tenant-brand"],
        )

    def test_count_can_filter_by_tenant(self) -> None:
        self.tenants.save(
            Tenant(
                tenant_id="tenant-one",
                name="Tenant One",
            )
        )

        self.brands.save(
            {
                "brand_id": "default-brand",
                "name": "Default Brand",
            }
        )
        self.brands.save(
            {
                "brand_id": "tenant-brand",
                "tenant_id": "tenant-one",
                "name": "Tenant Brand",
            }
        )

        self.assertEqual(self.brands.count(), 2)
        self.assertEqual(
            self.brands.count(DEFAULT_TENANT_ID),
            1,
        )
        self.assertEqual(
            self.brands.count("tenant-one"),
            1,
        )

    def test_existing_brand_can_move_to_another_tenant(self) -> None:
        self.tenants.save(
            Tenant(
                tenant_id="tenant-one",
                name="Tenant One",
            )
        )

        payload = {
            "brand_id": "brand-one",
            "name": "Brand One",
        }
        self.brands.save(payload)

        payload["tenant_id"] = "tenant-one"
        self.brands.save(payload)

        self.assertEqual(
            self.brands.tenant_id_for("brand-one"),
            "tenant-one",
        )

    def test_missing_brand_ownership_raises(self) -> None:
        with self.assertRaisesRegex(
            FileNotFoundError,
            "missing-brand",
        ):
            self.brands.tenant_id_for("missing-brand")


if __name__ == "__main__":
    unittest.main()
