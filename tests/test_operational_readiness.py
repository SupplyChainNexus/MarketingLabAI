"""Recovery, monitoring, support, and evidence tests for MLAI-030.5."""

from __future__ import annotations

import json
import tempfile
import unittest
from datetime import UTC, datetime, timedelta
from pathlib import Path

from app.database.connection import SQLiteDatabase
from app.database.factory import bootstrap_database
from app.operations import (
    OperationalReadinessEvaluator,
    PilotConfiguration,
    ReadinessEvidence,
    ReadinessEvidenceRepository,
)


class OperationalReadinessTests(unittest.TestCase):
    commit_sha = "54cb7c908e5dc628ff29f1c63ed1ccdc9abdf332"

    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.database = SQLiteDatabase(Path(self.temp.name) / "readiness.sqlite3")
        bootstrap_database(self.database)
        self.repository = ReadinessEvidenceRepository(self.database)
        self.config = PilotConfiguration.from_environment(
            {
                "MLAI_ENVIRONMENT": "controlled-production-readiness",
                "MLAI_DATABASE_PATH": str(self.database.database_path),
                "MLAI_BACKUP_DIRECTORY": str(Path(self.temp.name) / "backups"),
                "MLAI_PUBLIC_ORIGIN": "https://pilot.example.test",
                "MLAI_TRUST_PROXY_TLS": "false",
                "MLAI_SESSION_SECRET": "s" * 48,
                "MLAI_IDENTITY_PROVIDER": "google-cloud-identity-platform",
                "MLAI_IDENTITY_ADAPTER_FACTORY": (
                    "app.identity.google_cloud:create_google_cloud_adapter"
                ),
                "MLAI_PROVIDER_REGISTRY_FACTORY": "deployment.providers:create_registry",
                "MLAI_GOOGLE_CLOUD_PROJECT_ID": "marketinglabai-identity-dev",
                "MLAI_GOOGLE_WEB_API_KEY": "restricted-browser-key",
                "MLAI_GOOGLE_OAUTH_CLIENT_ID": "test.apps.googleusercontent.com",
                "MLAI_GOOGLE_AUTH_DOMAIN": (
                    "marketinglabai-identity-dev.firebaseapp.com"
                ),
                "MLAI_FOUNDER_INVITATION_HASHES_JSON": json.dumps(
                    {
                        "strand-auto-parts-pilot": "a" * 64,
                        "velani-wholesale-pilot": "b" * 64,
                    }
                ),
                "MLAI_ALLOW_REAL_CUSTOMER_DATA": "false",
                "MLAI_DEPLOYMENT_COMMIT": self.commit_sha,
            }
        )

    def tearDown(self) -> None:
        self.temp.cleanup()

    def evidence(self, name: str, **changes) -> ReadinessEvidence:
        observed = datetime(2026, 8, 6, 12, tzinfo=UTC)
        values = {
            "check_name": name,
            "environment": self.config.environment,
            "commit_sha": self.commit_sha,
            "operator_id": "founder-operator",
            "passed": True,
            "evidence_reference": f"ToolkitTemp/evidence/{name}.json",
            "observed_at": observed.isoformat(),
            "expires_at": (observed + timedelta(days=30)).isoformat(),
        }
        values.update(changes)
        return ReadinessEvidence(**values)

    def test_migration_seventeen_is_idempotent(self) -> None:
        self.database.initialise()
        self.database.initialise()
        with self.database.connection() as connection:
            rows = connection.execute(
                "SELECT description FROM schema_migrations WHERE version = 17"
            ).fetchall()
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0][0], "Add immutable pilot readiness evidence")

    def test_failed_evidence_requires_classification_and_remediation(self) -> None:
        with self.assertRaisesRegex(ValueError, "classification and remediation"):
            self.evidence("restore_rehearsed", passed=False)
        failure = self.evidence(
            "restore_rehearsed",
            passed=False,
            failure_classification="story defect",
            remediation="Correct restore path and rerun the unchanged check.",
        )
        self.repository.add(failure)
        self.assertFalse(self.repository.latest("restore_rehearsed").passed)

    def test_evidence_is_immutable_and_rejects_credential_references(self) -> None:
        item = self.evidence("backup_created_and_verified")
        self.repository.add(item)
        with self.assertRaises(Exception):
            self.repository.add(item)
        with self.assertRaisesRegex(ValueError, "credentials"):
            self.evidence("restore_rehearsed", evidence_reference="token=exposed")

    def test_wrong_commit_environment_and_expired_evidence_do_not_pass(self) -> None:
        now = datetime(2026, 8, 10, tzinfo=UTC)
        for name, changes in (
            ("wrong_commit", {"commit_sha": "abcdef1"}),
            ("wrong_environment", {"environment": "other"}),
            (
                "expired",
                {
                    "observed_at": datetime(2026, 7, 1, tzinfo=UTC).isoformat(),
                    "expires_at": datetime(2026, 7, 2, tzinfo=UTC).isoformat(),
                },
            ),
        ):
            self.repository.add(self.evidence(name, **changes))
        result = self.repository.current_passes(
            ("wrong_commit", "wrong_environment", "expired"),
            environment=self.config.environment,
            commit_sha=self.commit_sha,
            now=now,
        )
        self.assertEqual(result, {name: False for name in result})

    def test_complete_current_evidence_never_activates_real_data(self) -> None:
        for name in OperationalReadinessEvaluator.REQUIRED_EVIDENCE:
            self.repository.add(self.evidence(name))
        report = (
            OperationalReadinessEvaluator(self.config, self.database, self.repository)
            .evaluate()
            .to_dict()
        )
        self.assertTrue(report["recovery_monitoring_support_ready"])
        self.assertTrue(report["ready_for_founder_activation_assessment"])
        self.assertFalse(report["real_data_activation_authorized"])
        self.assertEqual(report["pilot_status"], "real_data_activation_frozen")

    def test_missing_evidence_reports_exact_blockers(self) -> None:
        report = (
            OperationalReadinessEvaluator(self.config, self.database, self.repository)
            .evaluate()
            .to_dict()
        )
        for name in OperationalReadinessEvaluator.REQUIRED_EVIDENCE:
            self.assertIn(name, report["blockers"])
        self.assertFalse(report["recovery_monitoring_support_ready"])

    def test_release_gate_blocks_founder_assessment_until_all_gates_pass(self) -> None:
        from app.operations import PilotReleaseGate

        report = PilotReleaseGate(self.config, self.database).evaluate().to_dict()
        self.assertFalse(report["ready_for_founder_activation_assessment"])
        self.assertFalse(report["real_data_activation_authorized"])


if __name__ == "__main__":
    unittest.main()
