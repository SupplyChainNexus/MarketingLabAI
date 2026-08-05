"""Tests for tenant-scoped Product Intelligence persistence."""

import tempfile
import unittest
from pathlib import Path

from app.database.connection import SQLiteDatabase
from app.database.repositories import BrandRepository
from app.product_intelligence import (
    ProductEvidence,
    ProductIntelligenceProfile,
    ProductIntelligenceRepository,
    ProductRecord,
    ProductType,
)


class ProductIntelligenceRepositoryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.folder = tempfile.TemporaryDirectory()
        self.database = SQLiteDatabase(Path(self.folder.name) / "db.sqlite")
        self.database.initialise()
        self.brands = BrandRepository(self.database)
        self.repository = ProductIntelligenceRepository(self.database)
        self.brands.save(
            {"brand_id": "brand-one", "tenant_id": "default", "name": "Brand One"}
        )

    def tearDown(self) -> None:
        self.folder.cleanup()

    def profile(self, *, tenant_id: str = "default", name: str = "Service"):
        return ProductIntelligenceProfile(
            tenant_id=tenant_id,
            brand_id="brand-one",
            products=[
                ProductRecord(
                    "service-one",
                    name,
                    ProductType.SERVICE,
                    evidence=[ProductEvidence("Synthetic founder-approved catalogue")],
                )
            ],
        )

    def test_round_trip_and_current_snapshot_update(self) -> None:
        self.repository.save(self.profile())
        self.repository.save(self.profile(name="Updated Service"))

        restored = self.repository.get(tenant_id="default", brand_id="brand-one")

        self.assertEqual(restored.products[0].name, "Updated Service")
        self.assertTrue(
            self.repository.exists(tenant_id="default", brand_id="brand-one")
        )

    def test_tenant_ownership_is_enforced(self) -> None:
        with self.assertRaisesRegex(ValueError, "tenant and brand differ"):
            self.repository.save(self.profile(tenant_id="another-tenant"))

    def test_cross_tenant_read_does_not_leak(self) -> None:
        self.repository.save(self.profile())
        self.assertFalse(
            self.repository.exists(tenant_id="another-tenant", brand_id="brand-one")
        )
        with self.assertRaises(FileNotFoundError):
            self.repository.get(tenant_id="another-tenant", brand_id="brand-one")


if __name__ == "__main__":
    unittest.main()
