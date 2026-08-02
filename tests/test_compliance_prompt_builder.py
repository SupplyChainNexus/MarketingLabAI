"""Tests for compliance prompt-section building."""

from __future__ import annotations

import unittest
from typing import cast

from app.ai.prompt import PromptSection
from app.compliance.prompt_builder import (
    CompliancePromptBuilder,
)
from app.compliance.requirements import (
    ComplianceRequirement,
)


class CompliancePromptBuilderTests(unittest.TestCase):
    def setUp(self) -> None:
        self.builder = CompliancePromptBuilder()

    @staticmethod
    def create_requirement(
        instruction: str,
        *,
        mandatory: bool = True,
        rule_id: str = "rule-one",
    ) -> ComplianceRequirement:
        return ComplianceRequirement(
            rule_id=rule_id,
            requirement_type="test",
            instruction=instruction,
            priority="warning",
            mandatory=mandatory,
            metadata={
                "brand_id": "brand-one",
                "secret_value": "internal-only",
            },
        )

    def test_empty_requirements_return_empty_list(
        self,
    ) -> None:
        self.assertEqual(
            self.builder.build_sections([]),
            [],
        )

    def test_builds_one_stable_prompt_section(
        self,
    ) -> None:
        sections = self.builder.build_sections(
            [
                self.create_requirement("Include Terms apply."),
            ]
        )

        self.assertEqual(
            len(sections),
            1,
        )
        self.assertIsInstance(
            sections[0],
            PromptSection,
        )
        self.assertEqual(
            sections[0].title,
            "Compliance Requirements",
        )

    def test_renders_mandatory_requirement(
        self,
    ) -> None:
        section = self.builder.build_sections(
            [
                self.create_requirement("Include the exact phrase Terms apply."),
            ]
        )[0]

        self.assertIn(
            "Mandatory Requirements",
            section.content,
        )
        self.assertIn(
            "- Include the exact phrase Terms apply.",
            section.content,
        )
        self.assertNotIn(
            "Recommended Requirements",
            section.content,
        )

    def test_renders_recommended_requirement(
        self,
    ) -> None:
        section = self.builder.build_sections(
            [
                self.create_requirement(
                    "Prefer concise wording.",
                    mandatory=False,
                ),
            ]
        )[0]

        self.assertIn(
            "Recommended Requirements",
            section.content,
        )
        self.assertIn(
            "- Prefer concise wording.",
            section.content,
        )
        self.assertNotIn(
            "Mandatory Requirements",
            section.content,
        )

    def test_mandatory_requirements_appear_first(
        self,
    ) -> None:
        section = self.builder.build_sections(
            [
                self.create_requirement(
                    "Optional instruction.",
                    mandatory=False,
                    rule_id="optional",
                ),
                self.create_requirement(
                    "Mandatory instruction.",
                    mandatory=True,
                    rule_id="mandatory",
                ),
            ]
        )[0]

        self.assertLess(
            section.content.index("Mandatory Requirements"),
            section.content.index("Recommended Requirements"),
        )
        self.assertLess(
            section.content.index("Mandatory instruction."),
            section.content.index("Optional instruction."),
        )

    def test_preserves_order_within_each_group(
        self,
    ) -> None:
        section = self.builder.build_sections(
            [
                self.create_requirement(
                    "First mandatory.",
                    rule_id="first",
                ),
                self.create_requirement(
                    "Second mandatory.",
                    rule_id="second",
                ),
                self.create_requirement(
                    "First optional.",
                    mandatory=False,
                    rule_id="third",
                ),
                self.create_requirement(
                    "Second optional.",
                    mandatory=False,
                    rule_id="fourth",
                ),
            ]
        )[0]

        self.assertLess(
            section.content.index("First mandatory."),
            section.content.index("Second mandatory."),
        )
        self.assertLess(
            section.content.index("First optional."),
            section.content.index("Second optional."),
        )

    def test_prompt_contains_only_public_instructions(
        self,
    ) -> None:
        requirement = self.create_requirement(
            "Include the approved disclaimer.",
            rule_id="rule-sensitive",
        )

        section = self.builder.build_sections([requirement])[0]

        self.assertIn(
            "Include the approved disclaimer.",
            section.content,
        )
        self.assertNotIn(
            "rule-sensitive",
            section.content,
        )
        self.assertNotIn(
            "brand-one",
            section.content,
        )
        self.assertNotIn(
            "internal-only",
            section.content,
        )
        self.assertNotIn(
            "warning",
            section.content,
        )

    def test_does_not_mutate_input_sequence(
        self,
    ) -> None:
        requirements = [
            self.create_requirement(
                "Optional instruction.",
                mandatory=False,
                rule_id="optional",
            ),
            self.create_requirement(
                "Mandatory instruction.",
                mandatory=True,
                rule_id="mandatory",
            ),
        ]

        original_order = [requirement.rule_id for requirement in requirements]

        self.builder.build_sections(requirements)

        self.assertEqual(
            [requirement.rule_id for requirement in requirements],
            original_order,
        )

    def test_rejects_invalid_collection(
        self,
    ) -> None:
        invalid_requirements = cast(
            list[ComplianceRequirement],
            "invalid",
        )

        with self.assertRaisesRegex(
            TypeError,
            "sequence",
        ):
            self.builder.build_sections(invalid_requirements)

    def test_rejects_invalid_requirement_entry(
        self,
    ) -> None:
        invalid_requirements = cast(
            list[ComplianceRequirement],
            [object()],
        )

        with self.assertRaisesRegex(
            TypeError,
            "ComplianceRequirement",
        ):
            self.builder.build_sections(invalid_requirements)


if __name__ == "__main__":
    unittest.main()
