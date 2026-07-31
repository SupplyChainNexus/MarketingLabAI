"""Tests for CreateBrandCommand."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from app.commands.brands import CreateBrandCommand
from app.database.connection import SQLiteDatabase
from app.database.repositories import BrandRepository
from app.tenants.models import Tenant
from app.tenants.repository import TenantRepository


class CreateBrandCommandTests(unittest.TestCase):

    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()

        self.database = SQLiteDatabase(Path(self.temp.name) / "marketinglabai.db")

        self.database.initialise()

        self.tenants = TenantRepository(self.database)
        self.brands = BrandRepository(self.database)

    def tearDown(self) -> None:
        self.temp.cleanup()

    def test_create_brand(self):

        command = CreateBrandCommand(
            payload={
                "brand_id": "brand-one",
                "name": "Brand One",
            },
            tenant_repository=self.tenants,
            brand_repository=self.brands,
        )

        brand = command.execute()

        self.assertEqual(
            brand["brand_id"],
            "brand-one",
        )

        self.assertEqual(
            brand["tenant_id"],
            "default",
        )

    def test_create_brand_for_explicit_tenant(self):

        self.tenants.save(
            Tenant(
                tenant_id="tenant-two",
                name="Tenant Two",
            )
        )

        command = CreateBrandCommand(
            payload={
                "brand_id": "brand-two",
                "name": "Brand Two",
                "tenant_id": "tenant-two",
            },
            tenant_repository=self.tenants,
            brand_repository=self.brands,
        )

        brand = command.execute()

        self.assertEqual(
            brand["tenant_id"],
            "tenant-two",
        )

    def test_unknown_tenant_is_rejected(self):

        with self.assertRaisesRegex(
            ValueError,
            "does not exist",
        ):

            CreateBrandCommand(
                payload={
                    "brand_id": "brand",
                    "name": "Brand",
                    "tenant_id": "missing",
                },
                tenant_repository=self.tenants,
                brand_repository=self.brands,
            ).execute()


if __name__ == "__main__":
    unittest.main()
