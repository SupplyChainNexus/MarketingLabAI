"""Tests for deterministic target-product relevance."""

import tempfile
import unittest
from pathlib import Path

from app.customer_intelligence import CustomerIntelligenceProfile, CustomerPersona
from app.database.connection import SQLiteDatabase
from app.database.repositories import BrandRepository, CustomerIntelligenceRepository
from app.positioning_intelligence import (
    PositioningDecision,
    TargetKind,
    TargetProductRelevanceEvaluator,
)
from app.product_intelligence import (
    ProductEvidence,
    ProductIntelligenceProfile,
    ProductIntelligenceRepository,
    ProductRecord,
    ProductType,
    VerifiedOffer,
)


class PositioningRelevanceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.folder = tempfile.TemporaryDirectory()
        self.database = SQLiteDatabase(Path(self.folder.name) / "db.sqlite")
        self.brands = BrandRepository(self.database)
        self.customers = CustomerIntelligenceRepository(self.database)
        self.products = ProductIntelligenceRepository(self.database)
        self.brands.save({"brand_id": "brand", "tenant_id": "default", "name": "Brand"})
        self.customers.save(
            CustomerIntelligenceProfile(
                brand_id="brand",
                personas=[
                    CustomerPersona(
                        "persona",
                        "Owner",
                        pain_points=["Fragmented marketing approval"],
                        desired_outcomes=["Consistent marketing decisions"],
                    )
                ],
            )
        )
        self.products.save(
            ProductIntelligenceProfile(
                "default",
                "brand",
                products=[
                    ProductRecord(
                        "product",
                        "Marketing workspace",
                        ProductType.SERVICE,
                        evidence=[ProductEvidence("Synthetic catalogue")],
                        features=["Governed approval workflow"],
                        benefits=["Consistent marketing decisions"],
                        proof_points=["Synthetic workflow test"],
                        limitations=["Synthetic evidence only"],
                        prohibited_claims=["Do not claim proven revenue growth"],
                        offers=[VerifiedOffer("offer", "Synthetic offer")],
                    )
                ],
            )
        )
        self.evaluator = TargetProductRelevanceEvaluator(self.customers, self.products)

    def tearDown(self) -> None:
        self.folder.cleanup()

    def decision(self, **changes: object) -> PositioningDecision:
        values: dict[str, object] = {
            "positioning_id": "positioning",
            "version": 1,
            "tenant_id": "default",
            "brand_id": "brand",
            "target_kind": TargetKind.PERSONA,
            "target_id": "persona",
            "product_id": "product",
            "offer_id": "offer",
        }
        values.update(changes)
        return PositioningDecision(**values)

    def test_resolves_references_and_explains_recorded_intersections(self) -> None:
        result = self.evaluator.evaluate(self.decision())
        self.assertEqual(result.target_name, "Owner")
        self.assertEqual(result.product_name, "Marketing workspace")
        self.assertEqual(result.offer_name, "Synthetic offer")
        self.assertTrue(result.has_supported_relevance)
        shared_terms = {term for match in result.matches for term in match.shared_terms}
        self.assertIn("marketing", shared_terms)
        self.assertIn("Synthetic evidence only", result.limitations)
        self.assertIn("Do not claim proven revenue growth", result.prohibited_claims)

    def test_unknown_target_product_and_offer_are_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "target"):
            self.evaluator.evaluate(self.decision(target_id="missing"))
        with self.assertRaisesRegex(ValueError, "product"):
            self.evaluator.evaluate(self.decision(product_id="missing"))
        with self.assertRaisesRegex(ValueError, "offer"):
            self.evaluator.evaluate(self.decision(offer_id="missing"))

    def test_cross_tenant_product_context_is_not_read(self) -> None:
        with self.assertRaises(FileNotFoundError):
            self.evaluator.evaluate(self.decision(tenant_id="another"))

    def test_missing_support_is_reported_as_gaps_not_invented(self) -> None:
        self.customers.save(
            CustomerIntelligenceProfile(
                brand_id="brand",
                personas=[CustomerPersona("persona", "Owner")],
            )
        )
        result = self.evaluator.evaluate(self.decision())
        codes = {gap.code for gap in result.gaps}
        self.assertIn("target_context_missing", codes)
        self.assertFalse(result.has_supported_relevance)

    def test_use_case_model_gap_is_explicit(self) -> None:
        result = self.evaluator.evaluate(self.decision())
        self.assertIn("use_cases_unmodelled", {gap.code for gap in result.gaps})


if __name__ == "__main__":
    unittest.main()
