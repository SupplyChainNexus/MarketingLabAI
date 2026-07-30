"""Tests for compliance rule versioning logic."""

import unittest

from app.compliance.models import BrandRule, RuleSeverity
from app.compliance.rules import RuleService


class RuleServiceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.service = RuleService()
        self.rule = BrandRule(
            rule_id="rule-001",
            brand_id="test-brand",
            name="Required disclaimer",
            description="Require the approved disclaimer.",
            severity=RuleSeverity.WARNING,
        )

    def test_create_next_version_increments_version(self) -> None:
        new_rule = self.service.create_next_version(
            self.rule,
            severity=RuleSeverity.BLOCKER,
        )

        self.assertEqual(new_rule.version, 2)
        self.assertEqual(new_rule.severity, RuleSeverity.BLOCKER)

    def test_create_next_version_preserves_identity(self) -> None:
        new_rule = self.service.create_next_version(
            self.rule,
            name="Updated disclaimer",
        )

        self.assertEqual(new_rule.rule_id, self.rule.rule_id)
        self.assertEqual(new_rule.brand_id, self.rule.brand_id)

    def test_create_next_version_does_not_modify_source(self) -> None:
        new_rule = self.service.create_next_version(
            self.rule,
            name="Updated disclaimer",
        )

        self.assertEqual(self.rule.version, 1)
        self.assertEqual(self.rule.name, "Required disclaimer")
        self.assertEqual(new_rule.name, "Updated disclaimer")

    def test_protected_fields_cannot_be_changed_directly(self) -> None:
        with self.assertRaisesRegex(ValueError, "protected fields"):
            self.service.create_next_version(
                self.rule,
                rule_id="different-rule",
            )

    def test_retire_creates_disabled_version(self) -> None:
        retired_rule = self.service.retire(self.rule)

        self.assertFalse(retired_rule.enabled)
        self.assertEqual(retired_rule.version, 2)

    def test_activate_creates_enabled_version(self) -> None:
        disabled_rule = BrandRule(
            rule_id="rule-001",
            brand_id="test-brand",
            name="Required disclaimer",
            description="Require the approved disclaimer.",
            enabled=False,
            version=2,
        )

        activated_rule = self.service.activate(disabled_rule)

        self.assertTrue(activated_rule.enabled)
        self.assertEqual(activated_rule.version, 3)


if __name__ == "__main__":
    unittest.main()
