"""Tests for compliance requirement translation."""

from __future__ import annotations

import unittest
from dataclasses import FrozenInstanceError
from typing import cast

from app.compliance.models import (
    BrandRule,
    RuleSeverity,
)
from app.compliance.requirements import (
    ComplianceRequirement,
)
from app.compliance.rule_packs import RulePackEntry
from app.compliance.translator import (
    ComplianceRequirementTranslator,
)


class ComplianceRequirementTests(unittest.TestCase):
    def test_requirement_cleans_values(
        self,
    ) -> None:
        requirement = ComplianceRequirement(
            rule_id=" rule-one ",
            requirement_type=" required_phrase ",
            instruction=" Include the phrase. ",
            priority=" warning ",
        )

        self.assertEqual(
            requirement.rule_id,
            "rule-one",
        )
        self.assertEqual(
            requirement.requirement_type,
            "required_phrase",
        )
        self.assertEqual(
            requirement.instruction,
            "Include the phrase.",
        )
        self.assertEqual(
            requirement.priority,
            "warning",
        )

    def test_requirement_is_immutable(
        self,
    ) -> None:
        requirement = ComplianceRequirement(
            rule_id="rule-one",
            requirement_type="required_phrase",
            instruction="Include the phrase.",
            priority="warning",
        )

        with self.assertRaises(FrozenInstanceError):
            requirement.instruction = "Changed"  # type: ignore[misc]

    def test_requirement_copies_metadata(
        self,
    ) -> None:
        metadata = {
            "nested": {
                "value": 1,
            },
        }

        requirement = ComplianceRequirement(
            rule_id="rule-one",
            requirement_type="required_phrase",
            instruction="Include the phrase.",
            priority="warning",
            metadata=metadata,
        )

        metadata["nested"]["value"] = 2

        self.assertEqual(
            requirement.metadata["nested"]["value"],
            1,
        )

    def test_to_dict_returns_mutable_copy(
        self,
    ) -> None:
        requirement = ComplianceRequirement(
            rule_id="rule-one",
            requirement_type="required_phrase",
            instruction="Include the phrase.",
            priority="warning",
            metadata={
                "value": 1,
            },
        )

        payload = requirement.to_dict()
        payload["metadata"]["value"] = 2

        self.assertEqual(
            requirement.metadata["value"],
            1,
        )


class ComplianceRequirementTranslatorTests(unittest.TestCase):
    def setUp(self) -> None:
        self.translator = ComplianceRequirementTranslator()

    @staticmethod
    def create_entry(
        evaluator_type: str,
        evaluator_config: dict,
        *,
        severity: RuleSeverity = (RuleSeverity.WARNING),
    ) -> RulePackEntry:
        return RulePackEntry(
            rule=BrandRule(
                rule_id=(f"rule-{evaluator_type}"),
                brand_id="brand-one",
                name="Test rule",
                description="Test description.",
                severity=severity,
                category="campaign",
            ),
            evaluator_type=evaluator_type,
            evaluator_config=evaluator_config,
        )

    def test_translates_required_phrase(
        self,
    ) -> None:
        requirement = self.translator.translate(
            self.create_entry(
                "required_phrase",
                {
                    "required_phrase": ("Terms apply."),
                },
            )
        )

        self.assertEqual(
            requirement.requirement_type,
            "required_phrase",
        )
        self.assertEqual(
            requirement.instruction,
            'Include the exact phrase "Terms apply.".',
        )

    def test_translates_required_url(
        self,
    ) -> None:
        requirement = self.translator.translate(
            self.create_entry(
                "required_url",
                {
                    "required_url": ("https://example.com/terms"),
                },
            )
        )

        self.assertIn(
            "https://example.com/terms",
            requirement.instruction,
        )

    def test_translates_maximum_length(
        self,
    ) -> None:
        requirement = self.translator.translate(
            self.create_entry(
                "maximum_length",
                {
                    "maximum": 100,
                    "measurement": "characters",
                },
            )
        )

        self.assertEqual(
            requirement.instruction,
            ("Keep the content within " "100 characters."),
        )

    def test_translates_maximum_word_length(
        self,
    ) -> None:
        requirement = self.translator.translate(
            self.create_entry(
                "maximum_length",
                {
                    "maximum": 20,
                    "measurement": "words",
                },
            )
        )

        self.assertIn(
            "20 words",
            requirement.instruction,
        )

    def test_translates_forbidden_regex(
        self,
    ) -> None:
        requirement = self.translator.translate(
            self.create_entry(
                "forbidden_regex",
                {
                    "pattern": (r"\bguaranteed?\b"),
                },
            )
        )

        self.assertIn(
            r"\bguaranteed?\b",
            requirement.instruction,
        )

    def test_translates_keyword_count(
        self,
    ) -> None:
        requirement = self.translator.translate(
            self.create_entry(
                "maximum_keyword_count",
                {
                    "keyword": "sale",
                    "maximum": 2,
                },
            )
        )

        self.assertEqual(
            requirement.instruction,
            ('Use the keyword "sale" ' "no more than 2 times."),
        )

    def test_preserves_rule_metadata(
        self,
    ) -> None:
        requirement = self.translator.translate(
            self.create_entry(
                "required_phrase",
                {
                    "required_phrase": ("Terms apply."),
                },
                severity=RuleSeverity.BLOCKER,
            )
        )

        self.assertEqual(
            requirement.priority,
            "blocker",
        )
        self.assertEqual(
            requirement.metadata["brand_id"],
            "brand-one",
        )
        self.assertEqual(
            requirement.metadata["evaluator_type"],
            "required_phrase",
        )
        self.assertEqual(
            requirement.metadata["evaluator_config"],
            {
                "required_phrase": ("Terms apply."),
            },
        )

    def test_translate_many_preserves_order(
        self,
    ) -> None:
        entries = [
            self.create_entry(
                "required_phrase",
                {
                    "required_phrase": ("Terms apply."),
                },
            ),
            self.create_entry(
                "maximum_length",
                {
                    "maximum": 100,
                },
            ),
        ]

        requirements = self.translator.translate_many(entries)

        self.assertEqual(
            [requirement.requirement_type for requirement in requirements],
            [
                "required_phrase",
                "maximum_length",
            ],
        )

    def test_rejects_unsupported_type(
        self,
    ) -> None:
        entry = RulePackEntry(
            rule=BrandRule(
                rule_id="unsupported-rule",
                brand_id="brand-one",
                name="Unsupported",
                description="Unsupported rule.",
            ),
            evaluator_type="unknown_type",
            evaluator_config={},
        )

        with self.assertRaisesRegex(
            ValueError,
            "Unsupported",
        ):
            self.translator.translate(entry)

    def test_rejects_invalid_entry(
        self,
    ) -> None:
        invalid_entry = cast(
            RulePackEntry,
            object(),
        )

        with self.assertRaisesRegex(
            TypeError,
            "RulePackEntry",
        ):
            self.translator.translate(invalid_entry)

    def test_rejects_missing_configuration(
        self,
    ) -> None:
        entry = self.create_entry(
            "required_phrase",
            {},
        )

        with self.assertRaisesRegex(
            ValueError,
            "required_phrase",
        ):
            self.translator.translate(entry)


if __name__ == "__main__":
    unittest.main()
