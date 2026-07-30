"""Tests for reusable deterministic compliance evaluators."""

from __future__ import annotations

import re
import unittest

from app.compliance.evaluators import (
    forbidden_regex_evaluator,
    maximum_keyword_count_evaluator,
    maximum_length_evaluator,
    required_phrase_evaluator,
    required_url_evaluator,
)
from app.compliance.models import (
    BrandRule,
    ComplianceStatus,
    ReviewSubjectType,
)


class ComplianceEvaluatorTests(unittest.TestCase):
    def setUp(self) -> None:
        self.rule = BrandRule(
            rule_id="test-rule",
            brand_id="test-brand",
            name="Test rule",
            description="Test compliance rule.",
        )

    def evaluate(self, evaluator, content: str):
        return evaluator(
            self.rule,
            "campaign-001",
            ReviewSubjectType.TEXT,
            content,
        )

    def test_required_phrase_accepts_matching_content(self) -> None:
        finding = self.evaluate(
            required_phrase_evaluator("Terms and conditions apply"),
            "Offer valid today. TERMS AND CONDITIONS APPLY.",
        )

        self.assertEqual(finding.status, ComplianceStatus.COMPLIANT)
        self.assertEqual(finding.evidence, ["Terms and conditions apply"])

    def test_required_phrase_rejects_missing_content(self) -> None:
        finding = self.evaluate(
            required_phrase_evaluator("Terms and conditions apply"),
            "Offer valid today.",
        )

        self.assertEqual(
            finding.status,
            ComplianceStatus.NON_COMPLIANT,
        )

    def test_required_phrase_rejects_blank_configuration(self) -> None:
        with self.assertRaisesRegex(ValueError, "required_phrase"):
            required_phrase_evaluator("   ")

    def test_required_url_accepts_matching_content(self) -> None:
        url = "https://example.com/terms"

        finding = self.evaluate(
            required_url_evaluator(url),
            f"Read the full terms at {url}.",
        )

        self.assertEqual(finding.status, ComplianceStatus.COMPLIANT)
        self.assertEqual(finding.evidence, [url])

    def test_required_url_rejects_missing_content(self) -> None:
        finding = self.evaluate(
            required_url_evaluator("https://example.com/terms"),
            "Read the full terms on our website.",
        )

        self.assertEqual(
            finding.status,
            ComplianceStatus.NON_COMPLIANT,
        )

    def test_required_url_rejects_invalid_url(self) -> None:
        with self.assertRaisesRegex(ValueError, "valid HTTP"):
            required_url_evaluator("example.com/terms")

    def test_maximum_character_length_accepts_content_at_limit(self) -> None:
        finding = self.evaluate(
            maximum_length_evaluator(5),
            "12345",
        )

        self.assertEqual(finding.status, ComplianceStatus.COMPLIANT)

    def test_maximum_character_length_rejects_content_over_limit(self) -> None:
        finding = self.evaluate(
            maximum_length_evaluator(5),
            "123456",
        )

        self.assertEqual(
            finding.status,
            ComplianceStatus.NON_COMPLIANT,
        )
        self.assertIn("Actual characters: 6", finding.evidence)

    def test_maximum_word_length_counts_words(self) -> None:
        finding = self.evaluate(
            maximum_length_evaluator(3, measurement="words"),
            "one two three four",
        )

        self.assertEqual(
            finding.status,
            ComplianceStatus.NON_COMPLIANT,
        )
        self.assertIn("Actual words: 4", finding.evidence)

    def test_maximum_length_rejects_invalid_measurement(self) -> None:
        with self.assertRaisesRegex(ValueError, "measurement"):
            maximum_length_evaluator(10, measurement="sentences")

    def test_maximum_length_rejects_negative_limit(self) -> None:
        with self.assertRaisesRegex(ValueError, "negative"):
            maximum_length_evaluator(-1)

    def test_forbidden_regex_rejects_matching_content(self) -> None:
        finding = self.evaluate(
            forbidden_regex_evaluator(r"\bguaranteed?\b"),
            "Guaranteed returns are available.",
        )

        self.assertEqual(
            finding.status,
            ComplianceStatus.NON_COMPLIANT,
        )
        self.assertEqual(finding.evidence, ["Guaranteed"])

    def test_forbidden_regex_accepts_non_matching_content(self) -> None:
        finding = self.evaluate(
            forbidden_regex_evaluator(r"\bguaranteed?\b"),
            "Results will vary.",
        )

        self.assertEqual(finding.status, ComplianceStatus.COMPLIANT)

    def test_forbidden_regex_accepts_compiled_pattern(self) -> None:
        finding = self.evaluate(
            forbidden_regex_evaluator(re.compile(r"\bfree\b", re.IGNORECASE)),
            "This product is free.",
        )

        self.assertEqual(
            finding.status,
            ComplianceStatus.NON_COMPLIANT,
        )

    def test_forbidden_regex_rejects_invalid_pattern(self) -> None:
        with self.assertRaisesRegex(ValueError, "Invalid regular expression"):
            forbidden_regex_evaluator("(")

    def test_keyword_count_accepts_usage_at_limit(self) -> None:
        finding = self.evaluate(
            maximum_keyword_count_evaluator("sale", 2),
            "Sale starts today. Final sale.",
        )

        self.assertEqual(finding.status, ComplianceStatus.COMPLIANT)
        self.assertEqual(finding.evidence, ["Occurrences: 2"])

    def test_keyword_count_rejects_usage_over_limit(self) -> None:
        finding = self.evaluate(
            maximum_keyword_count_evaluator("sale", 1),
            "Sale starts today. Final SALE.",
        )

        self.assertEqual(
            finding.status,
            ComplianceStatus.NON_COMPLIANT,
        )
        self.assertIn("Occurrences: 2", finding.evidence)

    def test_keyword_count_uses_whole_word_matching(self) -> None:
        finding = self.evaluate(
            maximum_keyword_count_evaluator("sale", 0),
            "Wholesale pricing is available.",
        )

        self.assertEqual(finding.status, ComplianceStatus.COMPLIANT)

    def test_keyword_count_rejects_blank_keyword(self) -> None:
        with self.assertRaisesRegex(ValueError, "keyword"):
            maximum_keyword_count_evaluator(" ", 1)

    def test_keyword_count_rejects_negative_limit(self) -> None:
        with self.assertRaisesRegex(ValueError, "negative"):
            maximum_keyword_count_evaluator("sale", -1)


if __name__ == "__main__":
    unittest.main()
