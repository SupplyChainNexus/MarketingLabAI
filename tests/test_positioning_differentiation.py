"""Tests for governed differentiation and proof selection."""

import tempfile
import unittest
from pathlib import Path

from app.database.connection import SQLiteDatabase
from app.database.repositories import BrandRepository
from app.positioning_intelligence import (
    AlternativeEvidence,
    DifferentiationProofEvaluator,
    EvidenceReviewStatus,
    PositioningDecision,
    TargetKind,
    TargetProductRelevance,
)
from app.product_intelligence import (
    ProductEvidence,
    ProductIntelligenceProfile,
    ProductIntelligenceRepository,
    ProductRecord,
    ProductType,
)


class PositioningDifferentiationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.folder = tempfile.TemporaryDirectory()
        database = SQLiteDatabase(Path(self.folder.name) / "db.sqlite")
        BrandRepository(database).save(
            {"brand_id": "brand", "tenant_id": "default", "name": "Brand"}
        )
        self.products = ProductIntelligenceRepository(database)
        self.products.save(
            ProductIntelligenceProfile(
                "default",
                "brand",
                products=[
                    ProductRecord(
                        "product",
                        "Workspace",
                        ProductType.SERVICE,
                        evidence=[ProductEvidence("Synthetic catalogue")],
                        features=["Governed approval workflow"],
                        benefits=["Consistent marketing decisions"],
                        proof_points=["Synthetic workflow test"],
                        prohibited_claims=["Guaranteed revenue growth"],
                    )
                ],
            )
        )
        self.evaluator = DifferentiationProofEvaluator(self.products)

    def tearDown(self) -> None:
        self.folder.cleanup()

    @staticmethod
    def decision(**changes: object) -> PositioningDecision:
        values: dict[str, object] = {
            "positioning_id": "positioning",
            "version": 1,
            "tenant_id": "default",
            "brand_id": "brand",
            "target_kind": TargetKind.PERSONA,
            "target_id": "persona",
            "product_id": "product",
            "differentiators": ["Governed approval workflow"],
            "alternatives": ["Manual process"],
        }
        values.update(changes)
        return PositioningDecision(**values)

    @staticmethod
    def relevance(**changes: object) -> TargetProductRelevance:
        values: dict[str, object] = {
            "positioning_id": "positioning",
            "positioning_version": 1,
            "target_name": "Owner",
            "product_name": "Workspace",
            "prohibited_claims": ("Guaranteed revenue growth",),
        }
        values.update(changes)
        return TargetProductRelevance(**values)

    @staticmethod
    def alternative(
        status: EvidenceReviewStatus = EvidenceReviewStatus.VERIFIED,
    ) -> AlternativeEvidence:
        return AlternativeEvidence(
            "Manual process",
            "Manual process lacks a governed approval workflow",
            "Synthetic desk review",
            status,
            "2026-08-05",
        )

    def test_selects_only_supported_reviewed_differentiation(self) -> None:
        report = self.evaluator.evaluate(
            self.decision(), self.relevance(), (self.alternative(),)
        )
        self.assertEqual(len(report.selections), 1)
        selection = report.selections[0]
        self.assertEqual(selection.statement, "Governed approval workflow")
        self.assertEqual(selection.proof_points, ("Synthetic workflow test",))
        self.assertEqual(
            selection.provenance,
            ("Synthetic catalogue", "Synthetic desk review"),
        )
        self.assertFalse(report.gaps)

    def test_unreviewed_alternative_cannot_support_comparison(self) -> None:
        report = self.evaluator.evaluate(
            self.decision(),
            self.relevance(),
            (self.alternative(EvidenceReviewStatus.UNREVIEWED),),
        )
        self.assertFalse(report.selections)
        self.assertIn(
            "alternative_evidence_missing",
            {item.code for item in report.gaps},
        )

    def test_verified_alternative_requires_observation_timestamp(self) -> None:
        with self.assertRaisesRegex(ValueError, "observed_at"):
            AlternativeEvidence(
                "Manual process",
                "Manual process lacks a governed approval workflow",
                "Synthetic desk review",
                EvidenceReviewStatus.VERIFIED,
            )

    def test_evidence_for_undeclared_alternative_cannot_support_claim(self) -> None:
        evidence = AlternativeEvidence(
            "Undeclared competitor",
            "Competitor lacks a governed approval workflow",
            "Synthetic desk review",
            EvidenceReviewStatus.VERIFIED,
            "2026-08-05",
        )
        report = self.evaluator.evaluate(
            self.decision(),
            self.relevance(),
            (evidence,),
        )
        self.assertFalse(report.selections)
        self.assertEqual(report.gaps[0].code, "alternative_evidence_missing")

    def test_prohibited_claim_is_rejected_before_selection(self) -> None:
        report = self.evaluator.evaluate(
            self.decision(differentiators=["Guaranteed revenue growth"]),
            self.relevance(),
        )
        self.assertFalse(report.selections)
        self.assertEqual(report.gaps[0].code, "prohibited_claim")

    def test_missing_product_support_and_proof_remain_gaps(self) -> None:
        report = self.evaluator.evaluate(
            self.decision(
                differentiators=["Lowest market price"],
                alternatives=[],
            ),
            self.relevance(),
        )
        self.assertFalse(report.selections)
        self.assertEqual(report.gaps[0].code, "product_support_missing")

    def test_relevance_must_belong_to_same_immutable_version(self) -> None:
        with self.assertRaisesRegex(ValueError, "another positioning version"):
            self.evaluator.evaluate(
                self.decision(),
                self.relevance(positioning_version=2),
            )

    def test_cross_tenant_product_context_is_not_read(self) -> None:
        with self.assertRaises(FileNotFoundError):
            self.evaluator.evaluate(
                self.decision(tenant_id="another"),
                self.relevance(),
            )


if __name__ == "__main__":
    unittest.main()
