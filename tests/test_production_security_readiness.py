"""Production identity and security readiness tests for MLAI-030.4."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from app.database.connection import SQLiteDatabase
from app.operations import PilotConfiguration, ProductionSecurityEvaluator


class ProductionSecurityReadinessTests(unittest.TestCase):
    @staticmethod
    def external_evidence() -> dict[str, bool]:
        return {name: True for name in ProductionSecurityEvaluator.EXTERNAL_EVIDENCE}

    def configuration(self, **changes) -> PilotConfiguration:
        values = {
            "MLAI_ENVIRONMENT": "controlled-production-readiness",
            "MLAI_DATABASE_PATH": "security.sqlite3",
            "MLAI_BACKUP_DIRECTORY": "backups",
            "MLAI_PUBLIC_ORIGIN": "https://pilot.example.test",
            "MLAI_TRUST_PROXY_TLS": "false",
            "MLAI_SESSION_SECRET": "s" * 48,
            "MLAI_SESSION_TTL_SECONDS": "3600",
            "MLAI_RATE_LIMIT_REQUESTS": "60",
            "MLAI_RATE_LIMIT_WINDOW_SECONDS": "60",
            "MLAI_MAX_REQUEST_BYTES": "1048576",
            "MLAI_IDENTITY_PROVIDER": "google-cloud-identity-platform",
            "MLAI_IDENTITY_ADAPTER_FACTORY": (
                "app.identity.google_cloud:create_google_cloud_adapter"
            ),
            "MLAI_PROVIDER_REGISTRY_FACTORY": "deployment.providers:create_registry",
            "MLAI_GOOGLE_CLOUD_PROJECT_ID": "marketinglabai-identity-dev",
            "MLAI_GOOGLE_WEB_API_KEY": "restricted-public-browser-key",
            "MLAI_GOOGLE_OAUTH_CLIENT_ID": "public.apps.googleusercontent.com",
            "MLAI_GOOGLE_AUTH_DOMAIN": "marketinglabai-identity-dev.firebaseapp.com",
            "MLAI_GOOGLE_MAX_AUTH_AGE_SECONDS": "3600",
            "MLAI_FOUNDER_INVITATION_HASHES_JSON": json.dumps(
                {
                    "strand-auto-parts-pilot": "a" * 64,
                    "velani-wholesale-pilot": "b" * 64,
                }
            ),
            "MLAI_ALLOW_REAL_CUSTOMER_DATA": "false",
            "MLAI_SECURITY_EVIDENCE_JSON": json.dumps(self.external_evidence()),
        }
        values.update(changes)
        return PilotConfiguration.from_environment(values)

    def test_complete_security_evidence_never_activates_real_data(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            database = SQLiteDatabase(Path(directory) / "security.sqlite3")
            report = (
                ProductionSecurityEvaluator(
                    self.configuration(MLAI_SECURITY_EVIDENCE_JSON="{}"),
                    database,
                    external_evidence=self.external_evidence(),
                )
                .evaluate()
                .to_dict()
            )
        self.assertTrue(report["production_identity_security_ready"])
        self.assertTrue(report["ready_for_founder_activation_assessment"])
        self.assertFalse(report["real_data_activation_authorized"])
        self.assertEqual(report["pilot_status"], "real_data_activation_frozen")
        self.assertEqual(report["blockers"], [])

    def test_wrong_provider_and_loopback_are_explicit_blockers(self) -> None:
        config = self.configuration(
            MLAI_ENVIRONMENT="synthetic-pilot",
            MLAI_PUBLIC_ORIGIN="http://127.0.0.1:8080",
            MLAI_IDENTITY_PROVIDER="synthetic-test",
        )
        with tempfile.TemporaryDirectory() as directory:
            report = (
                ProductionSecurityEvaluator(
                    config,
                    SQLiteDatabase(Path(directory) / "security.sqlite3"),
                    external_evidence=self.external_evidence(),
                )
                .evaluate()
                .to_dict()
            )
        self.assertIn("google_identity_selected", report["blockers"])
        self.assertIn("production_tls", report["blockers"])
        self.assertFalse(report["production_identity_security_ready"])

    def test_missing_external_rehearsal_evidence_remains_a_blocker(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            report = (
                ProductionSecurityEvaluator(
                    self.configuration(),
                    SQLiteDatabase(Path(directory) / "security.sqlite3"),
                )
                .evaluate()
                .to_dict()
            )
        self.assertEqual(
            report["blockers"], list(ProductionSecurityEvaluator.EXTERNAL_EVIDENCE)
        )
        self.assertFalse(report["ready_for_founder_activation_assessment"])

    def test_release_gate_exposes_security_without_authorizing_activation(self) -> None:
        from app.operations import PilotReleaseGate

        with tempfile.TemporaryDirectory() as directory:
            database = SQLiteDatabase(Path(directory) / "security.sqlite3")
            payload = (
                PilotReleaseGate(self.configuration(), database).evaluate().to_dict()
            )
        self.assertTrue(
            payload["production_security"]["production_identity_security_ready"]
        )
        self.assertFalse(payload["real_data_activation_authorized"])

    def test_configuration_rejects_unbounded_security_values(self) -> None:
        for name, value in (
            ("MLAI_GOOGLE_MAX_AUTH_AGE_SECONDS", "7200"),
            ("MLAI_MAX_REQUEST_BYTES", "999999999"),
        ):
            with self.subTest(name=name), self.assertRaises(ValueError):
                self.configuration(**{name: value})


if __name__ == "__main__":
    unittest.main()
