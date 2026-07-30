"""Tests for versioned compliance rule persistence."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from app.compliance.models import BrandRule, RuleSeverity
from app.compliance.repository import BrandRuleRepository
from app.compliance.rules import RuleService
from app.database.connection import SQLiteDatabase
from app.database.repositories import BrandRepository


class BrandRuleRepositoryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.database = SQLiteDatabase(
            Path(self.temporary_directory.name) / "marketinglabai.db"
        )
        self.database.initialise()

        BrandRepository(self.database).save(
            {
                "brand_id": "test-brand",
                "name": "Test Brand",
            }
        )

        self.repository = BrandRuleRepository(self.database)
        self.service = RuleService()
        self.rule = BrandRule(
            rule_id="rule-001",
            brand_id="test-brand",
            name="Required disclaimer",
            description="Require the approved disclaimer.",
        )

    def tearDown(self) -> None:
        self.temporary_directory.cleanup()

    def test_rule_round_trip(self) -> None:
        self.repository.save(self.rule)

        restored = self.repository.get("rule-001")

        self.assertEqual(restored, self.rule)
        self.assertTrue(self.repository.exists("rule-001", 1))

    def test_latest_version_is_returned_by_default(self) -> None:
        self.repository.save(self.rule)

        version_two = self.service.create_next_version(
            self.rule,
            severity=RuleSeverity.BLOCKER,
        )
        self.repository.save(version_two)

        restored = self.repository.get("rule-001")

        self.assertEqual(restored.version, 2)
        self.assertEqual(restored.severity, RuleSeverity.BLOCKER)

    def test_specific_version_can_be_retrieved(self) -> None:
        self.repository.save(self.rule)
        self.repository.save(
            self.service.create_next_version(
                self.rule,
                name="Updated disclaimer",
            )
        )

        restored = self.repository.get("rule-001", version=1)

        self.assertEqual(restored.version, 1)
        self.assertEqual(restored.name, "Required disclaimer")

    def test_duplicate_version_is_rejected(self) -> None:
        self.repository.save(self.rule)

        with self.assertRaisesRegex(ValueError, "already exists"):
            self.repository.save(self.rule)

    def test_list_versions_preserves_history(self) -> None:
        self.repository.save(self.rule)

        version_two = self.service.create_next_version(
            self.rule,
            name="Updated disclaimer",
        )
        self.repository.save(version_two)

        versions = self.repository.list_versions("rule-001")

        self.assertEqual([rule.version for rule in versions], [1, 2])

    def test_list_for_brand_returns_latest_enabled_rules(self) -> None:
        second_rule = BrandRule(
            rule_id="rule-002",
            brand_id="test-brand",
            name="Prohibited guarantee",
            description="Prevent unsupported guarantees.",
        )

        self.repository.save(self.rule)
        self.repository.save(second_rule)
        self.repository.save(self.service.retire(second_rule))

        rules = self.repository.list_for_brand("test-brand")

        self.assertEqual([rule.rule_id for rule in rules], ["rule-001"])

    def test_list_for_brand_can_include_retired_rules(self) -> None:
        self.repository.save(self.rule)
        self.repository.save(self.service.retire(self.rule))

        rules = self.repository.list_for_brand(
            "test-brand",
            enabled_only=False,
        )

        self.assertEqual(len(rules), 1)
        self.assertFalse(rules[0].enabled)
        self.assertEqual(rules[0].version, 2)

    def test_count_includes_all_versions(self) -> None:
        self.repository.save(self.rule)
        self.repository.save(self.service.create_next_version(self.rule))

        self.assertEqual(self.repository.count(), 2)


if __name__ == "__main__":
    unittest.main()
