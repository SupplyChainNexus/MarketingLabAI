"""Tests for deterministic verified Product Intelligence context."""

import tempfile
import unittest
from pathlib import Path

from app.database.connection import SQLiteDatabase
from app.database.repositories import BrandRepository
from app.product_intelligence import (
    FactStatus,
    ProductContextProvider,
    ProductEvidence,
    ProductIntelligenceProfile,
    ProductIntelligenceRepository,
    ProductRecord,
    ProductType,
    VerifiedFact,
    VerifiedOffer,
)


class ProductContextProviderTests(unittest.TestCase):
    def setUp(self) -> None:
        self.folder = tempfile.TemporaryDirectory()
        database = SQLiteDatabase(Path(self.folder.name) / "db.sqlite")
        database.initialise()
        BrandRepository(database).save(
            {"brand_id": "brand-one", "tenant_id": "default", "name": "Brand"}
        )
        self.repository = ProductIntelligenceRepository(database)
        self.provider = ProductContextProvider(self.repository)

    def tearDown(self) -> None:
        self.folder.cleanup()

    def test_missing_profile_returns_empty_context(self) -> None:
        self.assertEqual(
            self.provider.build(tenant_id="default", brand_id="brand-one"), ""
        )

    def test_context_marks_unknowns_and_prohibited_claims(self) -> None:
        evidence = ProductEvidence("Synthetic approved offer sheet")
        self.repository.save(
            ProductIntelligenceProfile(
                tenant_id="default",
                brand_id="brand-one",
                products=[
                    ProductRecord(
                        "service",
                        "Priority sourcing",
                        ProductType.SERVICE,
                        evidence=[evidence],
                        benefits=["Faster sourcing response"],
                        prohibited_claims=["Guaranteed delivery"],
                        offers=[
                            VerifiedOffer(
                                "pilot",
                                "Pilot offer",
                                price=VerifiedFact(
                                    FactStatus.VERIFIED, "R500 synthetic", [evidence]
                                ),
                            )
                        ],
                    )
                ],
            )
        )

        context = self.provider.build(tenant_id="default", brand_id="brand-one")

        self.assertIn("Price: R500 synthetic", context)
        self.assertIn("Availability: Unknown", context)
        self.assertIn("Warranty: Unknown", context)
        self.assertIn("Prohibited claims: Guaranteed delivery", context)
        self.assertIn("Verified sources: Synthetic approved offer sheet", context)


if __name__ == "__main__":
    unittest.main()
