"""Tests for configurable compliance rule packs."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from app.compliance.engine import ComplianceEngine
from app.compliance.models import ComplianceStatus
from app.compliance.repository import BrandRuleRepository
from app.compliance.rule_packs import (
    RulePackInstaller,
    RulePackLoader,
)
from app.database.connection import SQLiteDatabase
from app.database.repositories import BrandRepository


class RulePackTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary_directory.name)
        self.database = SQLiteDatabase(self.root / "marketinglabai.db")
        self.database.initialise()

        BrandRepository(self.database).save(
            {
                "brand_id": "test-brand",
                "name": "Test Brand",
            }
        )

        self.repository = BrandRuleRepository(self.database)
        self.loader = RulePackLoader()

        self.payload = {
            "pack_id": "retail-default",
            "name": "Retail defaults",
            "description": "Baseline retail rules.",
            "version": 1,
            "rules": [
                {
                    "rule": {
                        "rule_id": "required-disclaimer",
                        "name": "Required disclaimer",
                        "description": ("Require the approved disclaimer."),
                        "severity": "error",
                        "evaluation_method": "deterministic",
                        "subject_types": ["text"],
                        "category": "disclosure",
                    },
                    "evaluator_type": "required_phrase",
                    "evaluator_config": {"required_phrase": "Terms apply."},
                },
                {
                    "rule": {
                        "rule_id": "maximum-post-length",
                        "name": "Maximum post length",
                        "description": ("Keep campaign posts concise."),
                        "severity": "warning",
                        "evaluation_method": "deterministic",
                        "subject_types": ["text"],
                        "category": "platform",
                    },
                    "evaluator_type": "maximum_length",
                    "evaluator_config": {
                        "maximum": 100,
                        "measurement": "characters",
                    },
                },
            ],
        }

    def tearDown(self) -> None:
        self.temporary_directory.cleanup()

    def test_loads_rule_pack_for_supplied_brand(self) -> None:
        rule_pack = self.loader.load_dict(
            self.payload,
            brand_id="test-brand",
        )

        self.assertEqual(rule_pack.pack_id, "retail-default")
        self.assertEqual(len(rule_pack.rules), 2)
        self.assertTrue(
            all(entry.rule.brand_id == "test-brand" for entry in rule_pack.rules)
        )

    def test_loads_rule_pack_from_json_file(self) -> None:
        path = self.root / "rule-pack.json"
        path.write_text(
            json.dumps(self.payload),
            encoding="utf-8",
        )

        rule_pack = self.loader.load_file(
            path,
            brand_id="test-brand",
        )

        self.assertEqual(rule_pack.name, "Retail defaults")

    def test_rejects_unknown_evaluator_type(self) -> None:
        self.payload["rules"][0]["evaluator_type"] = "execute_python"

        with self.assertRaisesRegex(
            ValueError,
            "Unsupported evaluator_type",
        ):
            self.loader.load_dict(
                self.payload,
                brand_id="test-brand",
            )

    def test_rejects_brand_override(self) -> None:
        self.payload["rules"][0]["rule"]["brand_id"] = "another-brand"

        with self.assertRaisesRegex(
            ValueError,
            "cannot override brand_id",
        ):
            self.loader.load_dict(
                self.payload,
                brand_id="test-brand",
            )

    def test_rejects_invalid_evaluator_configuration(
        self,
    ) -> None:
        self.payload["rules"][0]["evaluator_config"] = {}

        with self.assertRaisesRegex(
            ValueError,
            "Invalid evaluator configuration",
        ):
            self.loader.load_dict(
                self.payload,
                brand_id="test-brand",
            )

    def test_installer_creates_new_rules(self) -> None:
        rule_pack = self.loader.load_dict(
            self.payload,
            brand_id="test-brand",
        )

        result = RulePackInstaller(self.repository).install(rule_pack)

        self.assertEqual(len(result.created), 2)
        self.assertEqual(self.repository.count(), 2)

    def test_reinstalling_unchanged_pack_is_idempotent(
        self,
    ) -> None:
        rule_pack = self.loader.load_dict(
            self.payload,
            brand_id="test-brand",
        )
        installer = RulePackInstaller(self.repository)

        installer.install(rule_pack)
        result = installer.install(rule_pack)

        self.assertEqual(len(result.unchanged), 2)
        self.assertEqual(self.repository.count(), 2)

    def test_changed_rule_creates_new_version(self) -> None:
        installer = RulePackInstaller(self.repository)

        installer.install(
            self.loader.load_dict(
                self.payload,
                brand_id="test-brand",
            )
        )

        self.payload["rules"][0]["rule"]["severity"] = "blocker"

        result = installer.install(
            self.loader.load_dict(
                self.payload,
                brand_id="test-brand",
            )
        )

        versions = self.repository.list_versions("required-disclaimer")

        self.assertEqual(len(result.updated), 1)
        self.assertEqual(
            [rule.version for rule in versions],
            [1, 2],
        )
        self.assertEqual(
            versions[-1].severity.value,
            "blocker",
        )

    def test_registers_evaluators_with_engine(self) -> None:
        rule_pack = self.loader.load_dict(
            self.payload,
            brand_id="test-brand",
        )
        RulePackInstaller(self.repository).install(rule_pack)

        engine = ComplianceEngine(self.repository)
        self.loader.register_evaluators(
            rule_pack,
            engine,
        )

        report = engine.evaluate(
            brand_id="test-brand",
            subject_id="campaign-1",
            subject_type="text",
            content="Our offer is available. Terms apply.",
        )

        self.assertEqual(
            report.status,
            ComplianceStatus.COMPLIANT,
        )
        self.assertEqual(len(report.findings), 2)


if __name__ == "__main__":
    unittest.main()
