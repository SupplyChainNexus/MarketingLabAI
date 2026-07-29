"""Tests for MarketingLabAI compliance domain models."""

import unittest

from app.compliance.models import (
    BrandRule,
    ComplianceFinding,
    ComplianceReport,
    ComplianceStatus,
    EvaluationMethod,
    ReviewSubjectType,
    RuleSeverity,
)


class BrandRuleTests(unittest.TestCase):
    """Validate compliance rule behaviour."""

    def test_rule_requires_core_identifiers(self) -> None:
        with self.assertRaisesRegex(ValueError, "rule_id is required"):
            BrandRule(
                rule_id=" ",
                brand_id="nexus",
                name="Required disclaimer",
                description="Require the approved disclaimer.",
            )

    def test_rule_cleans_values_and_deduplicates_subject_types(self) -> None:
        rule = BrandRule(
            rule_id="  rule-001  ",
            brand_id="  nexus  ",
            name="  Required disclaimer  ",
            description="  Require the approved disclaimer.  ",
            subject_types=[
                ReviewSubjectType.TEXT,
                ReviewSubjectType.VIDEO,
                ReviewSubjectType.TEXT,
            ],
        )

        self.assertEqual(rule.rule_id, "rule-001")
        self.assertEqual(rule.brand_id, "nexus")
        self.assertEqual(rule.name, "Required disclaimer")
        self.assertEqual(
            rule.subject_types,
            [
                ReviewSubjectType.TEXT,
                ReviewSubjectType.VIDEO,
            ],
        )

    def test_rule_accepts_stored_enum_strings(self) -> None:
        rule = BrandRule(
            rule_id="rule-001",
            brand_id="nexus",
            name="Required disclaimer",
            description="Require the approved disclaimer.",
            severity="blocker",
            evaluation_method="evidence",
            subject_types=["image", "video"],
        )

        self.assertEqual(rule.severity, RuleSeverity.BLOCKER)
        self.assertEqual(
            rule.evaluation_method,
            EvaluationMethod.EVIDENCE,
        )
        self.assertTrue(rule.applies_to(ReviewSubjectType.VIDEO))

    def test_rule_rejects_invalid_version(self) -> None:
        with self.assertRaisesRegex(ValueError, "version must be at least 1"):
            BrandRule(
                rule_id="rule-001",
                brand_id="nexus",
                name="Required disclaimer",
                description="Require the approved disclaimer.",
                version=0,
            )

    def test_rule_round_trip_dictionary_conversion(self) -> None:
        rule = BrandRule(
            rule_id="rule-001",
            brand_id="nexus",
            name="Required disclaimer",
            description="Require the approved disclaimer.",
            severity=RuleSeverity.BLOCKER,
            evaluation_method=EvaluationMethod.EVIDENCE,
            subject_types=[
                ReviewSubjectType.TEXT,
                ReviewSubjectType.VIDEO,
            ],
            category="legal",
            evidence_required=True,
            version=2,
        )

        restored_rule = BrandRule.from_dict(rule.to_dict())

        self.assertEqual(restored_rule, rule)
        self.assertEqual(
            rule.to_dict()["subject_types"],
            ["text", "video"],
        )


class ComplianceFindingTests(unittest.TestCase):
    """Validate individual compliance findings."""

    def test_finding_cleans_and_deduplicates_evidence(self) -> None:
        finding = ComplianceFinding(
            finding_id="finding-001",
            rule_id="rule-001",
            subject_id="asset-001",
            subject_type=ReviewSubjectType.VIDEO,
            status=ComplianceStatus.NON_COMPLIANT,
            severity=RuleSeverity.BLOCKER,
            evaluation_method=EvaluationMethod.DETERMINISTIC,
            message="Unsupported guarantee detected.",
            evidence=[
                "  Guaranteed results  ",
                "Guaranteed results",
                "",
            ],
            timestamp_start_seconds=12.0,
            timestamp_end_seconds=17.0,
        )

        self.assertEqual(finding.evidence, ["Guaranteed results"])

    def test_finding_rejects_negative_timestamp(self) -> None:
        with self.assertRaisesRegex(
            ValueError,
            "timestamp_start_seconds cannot be negative",
        ):
            ComplianceFinding(
                finding_id="finding-001",
                rule_id="rule-001",
                subject_id="asset-001",
                subject_type=ReviewSubjectType.VIDEO,
                status=ComplianceStatus.NON_COMPLIANT,
                severity=RuleSeverity.BLOCKER,
                evaluation_method=EvaluationMethod.DETERMINISTIC,
                message="Unsupported guarantee detected.",
                timestamp_start_seconds=-1.0,
            )

    def test_finding_rejects_reversed_timestamp_range(self) -> None:
        with self.assertRaisesRegex(
            ValueError,
            "timestamp_end_seconds cannot be earlier",
        ):
            ComplianceFinding(
                finding_id="finding-001",
                rule_id="rule-001",
                subject_id="asset-001",
                subject_type=ReviewSubjectType.VIDEO,
                status=ComplianceStatus.NON_COMPLIANT,
                severity=RuleSeverity.BLOCKER,
                evaluation_method=EvaluationMethod.DETERMINISTIC,
                message="Unsupported guarantee detected.",
                timestamp_start_seconds=17.0,
                timestamp_end_seconds=12.0,
            )

    def test_finding_round_trip_dictionary_conversion(self) -> None:
        finding = ComplianceFinding(
            finding_id="finding-001",
            rule_id="rule-001",
            subject_id="asset-001",
            subject_type=ReviewSubjectType.IMAGE,
            status=ComplianceStatus.REQUIRES_REVIEW,
            severity=RuleSeverity.WARNING,
            evaluation_method=EvaluationMethod.MODEL_ASSISTED,
            message="Logo placement requires review.",
            evidence=["Logo appears near the lower edge."],
            recommendation="Confirm the approved safe-area spacing.",
        )

        restored_finding = ComplianceFinding.from_dict(finding.to_dict())

        self.assertEqual(restored_finding, finding)


class ComplianceReportTests(unittest.TestCase):
    """Validate compliance report behaviour."""

    def test_report_adds_matching_finding(self) -> None:
        report = ComplianceReport(
            report_id="report-001",
            brand_id="nexus",
            subject_id="asset-001",
            subject_type=ReviewSubjectType.VIDEO,
        )
        finding = ComplianceFinding(
            finding_id="finding-001",
            rule_id="rule-001",
            subject_id="asset-001",
            subject_type=ReviewSubjectType.VIDEO,
            status=ComplianceStatus.NON_COMPLIANT,
            severity=RuleSeverity.BLOCKER,
            evaluation_method=EvaluationMethod.DETERMINISTIC,
            message="Unsupported guarantee detected.",
        )

        report.add_finding(finding)

        self.assertEqual(report.findings, [finding])

    def test_report_rejects_finding_for_different_subject(self) -> None:
        report = ComplianceReport(
            report_id="report-001",
            brand_id="nexus",
            subject_id="asset-001",
            subject_type=ReviewSubjectType.TEXT,
        )
        finding = ComplianceFinding(
            finding_id="finding-001",
            rule_id="rule-001",
            subject_id="asset-002",
            subject_type=ReviewSubjectType.TEXT,
            status=ComplianceStatus.NON_COMPLIANT,
            severity=RuleSeverity.ERROR,
            evaluation_method=EvaluationMethod.DETERMINISTIC,
            message="Prohibited phrase detected.",
        )

        with self.assertRaisesRegex(
            ValueError,
            "does not belong to the report subject",
        ):
            report.add_finding(finding)

    def test_report_round_trip_dictionary_conversion(self) -> None:
        finding = ComplianceFinding(
            finding_id="finding-001",
            rule_id="rule-001",
            subject_id="asset-001",
            subject_type=ReviewSubjectType.TEXT,
            status=ComplianceStatus.COMPLIANT,
            severity=RuleSeverity.INFO,
            evaluation_method=EvaluationMethod.DETERMINISTIC,
            message="Required call to action is present.",
        )
        report = ComplianceReport(
            report_id="report-001",
            brand_id="nexus",
            subject_id="asset-001",
            subject_type=ReviewSubjectType.TEXT,
            status=ComplianceStatus.COMPLIANT,
            findings=[finding],
            summary="All deterministic checks passed.",
            ruleset_version="1.0",
        )

        restored_report = ComplianceReport.from_dict(report.to_dict())

        self.assertEqual(restored_report, report)
        self.assertIsInstance(
            restored_report.findings[0],
            ComplianceFinding,
        )


if __name__ == "__main__":
    unittest.main()
