"""Tests for compliance evaluation orchestration."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from app.compliance.engine import (
    ComplianceEngine,
    prohibited_phrase_evaluator,
)
from app.compliance.models import (
    BrandRule,
    ComplianceStatus,
    ReviewSubjectType,
)
from app.compliance.repository import BrandRuleRepository
from app.database.connection import SQLiteDatabase
from app.database.repositories import BrandRepository


class ComplianceEngineTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory()
        database = SQLiteDatabase(
            Path(self.temporary_directory.name) / "marketinglabai.db"
        )
        database.initialise()

        BrandRepository(database).save(
            {
                "brand_id": "test-brand",
                "name": "Test Brand",
            }
        )

        self.repository = BrandRuleRepository(database)
        self.rule = BrandRule(
            rule_id="no-guarantees",
            brand_id="test-brand",
            name="No guarantees",
            description="Unsupported guarantees are prohibited.",
        )
        self.repository.save(self.rule)

    def tearDown(self) -> None:
        self.temporary_directory.cleanup()

    def test_compliant_content_produces_compliant_report(self) -> None:
        engine = ComplianceEngine(
            self.repository,
            {"no-guarantees": prohibited_phrase_evaluator("guaranteed results")},
        )

        report = engine.evaluate(
            brand_id="test-brand",
            subject_id="campaign-001",
            subject_type=ReviewSubjectType.TEXT,
            content="Results depend on each customer's circumstances.",
        )

        self.assertEqual(report.status, ComplianceStatus.COMPLIANT)
        self.assertEqual(len(report.findings), 1)
        self.assertEqual(
            report.findings[0].status,
            ComplianceStatus.COMPLIANT,
        )
        self.assertEqual(report.ruleset_version, "no-guarantees:v1")
        self.assertIsNotNone(report.completed_at)

    def test_prohibited_phrase_produces_non_compliant_report(self) -> None:
        engine = ComplianceEngine(
            self.repository,
            {"no-guarantees": prohibited_phrase_evaluator("guaranteed results")},
        )

        report = engine.evaluate(
            brand_id="test-brand",
            subject_id="campaign-001",
            subject_type="text",
            content="Buy today for guaranteed results.",
        )

        self.assertEqual(report.status, ComplianceStatus.NON_COMPLIANT)
        self.assertEqual(
            report.findings[0].status,
            ComplianceStatus.NON_COMPLIANT,
        )
        self.assertEqual(
            report.findings[0].evidence,
            ["guaranteed results"],
        )

    def test_missing_evaluator_requires_review(self) -> None:
        engine = ComplianceEngine(self.repository)

        report = engine.evaluate(
            brand_id="test-brand",
            subject_id="campaign-001",
            subject_type="text",
            content="Sample campaign.",
        )

        self.assertEqual(
            report.status,
            ComplianceStatus.REQUIRES_REVIEW,
        )
        self.assertEqual(
            report.findings[0].status,
            ComplianceStatus.REQUIRES_REVIEW,
        )

    def test_rules_for_other_subject_types_are_skipped(self) -> None:
        image_rule = BrandRule(
            rule_id="image-rule",
            brand_id="test-brand",
            name="Image review",
            description="Review image content.",
            subject_types=[ReviewSubjectType.IMAGE],
        )
        self.repository.save(image_rule)

        engine = ComplianceEngine(
            self.repository,
            {"no-guarantees": prohibited_phrase_evaluator("guaranteed results")},
        )

        report = engine.evaluate(
            brand_id="test-brand",
            subject_id="campaign-001",
            subject_type="text",
            content="Ordinary campaign content.",
        )

        self.assertEqual(len(report.findings), 1)
        self.assertEqual(report.findings[0].rule_id, "no-guarantees")

    def test_no_applicable_rules_is_compliant(self) -> None:
        report = ComplianceEngine(self.repository).evaluate(
            brand_id="test-brand",
            subject_id="image-001",
            subject_type="image",
            content="",
        )

        self.assertEqual(report.status, ComplianceStatus.COMPLIANT)
        self.assertEqual(report.findings, [])

    def test_invalid_evaluator_result_is_rejected(self) -> None:
        def invalid_evaluator(
            rule: BrandRule,
            subject_id: str,
            subject_type: ReviewSubjectType,
            content: str,
        ):
            other_rule = BrandRule(
                rule_id="other-rule",
                brand_id=rule.brand_id,
                name="Other",
                description="Other rule.",
            )
            return ComplianceEngine.create_finding(
                rule=other_rule,
                subject_id=subject_id,
                subject_type=subject_type,
                status=ComplianceStatus.COMPLIANT,
                message="Invalid result.",
            )

        engine = ComplianceEngine(
            self.repository,
            {"no-guarantees": invalid_evaluator},
        )

        with self.assertRaisesRegex(ValueError, "different rule"):
            engine.evaluate(
                brand_id="test-brand",
                subject_id="campaign-001",
                subject_type="text",
                content="Sample campaign.",
            )


if __name__ == "__main__":
    unittest.main()
