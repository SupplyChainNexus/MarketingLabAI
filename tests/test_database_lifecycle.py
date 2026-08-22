"""Database initialization lifecycle and observational readiness tests."""

from __future__ import annotations

import json
import tempfile
import threading
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from unittest.mock import patch

from app.application import CanonicalApplication
from app.database.connection import SQLiteDatabase
from app.database.postgresql import PostgreSQLDatabase
from app.operations.configuration import PilotConfiguration
from app.operations.operational_readiness import OperationalReadinessEvaluator
from app.operations.release_gate import PilotReleaseGate


class _ControlledDatabase(SQLiteDatabase):
    def __init__(self, path: Path, *, fail_once: bool = False) -> None:
        super().__init__(path)
        self.apply_count = 0
        self.fail_once = fail_once
        self.apply_entered = threading.Event()
        self.release_apply = threading.Event()

    def _apply_schema(self) -> None:
        self.apply_count += 1
        self.apply_entered.set()
        if not self.release_apply.wait(timeout=5):
            raise TimeoutError("test schema application was not released")
        if self.fail_once:
            self.fail_once = False
            raise RuntimeError("synthetic initialization failure")


class DatabaseLifecycleTests(unittest.TestCase):
    @staticmethod
    def _configuration(database: SQLiteDatabase) -> PilotConfiguration:
        return PilotConfiguration.from_environment(
            {
                "MLAI_ENVIRONMENT": "lifecycle-test",
                "MLAI_DATABASE_PATH": str(database.database_path),
                "MLAI_BACKUP_DIRECTORY": str(database.database_path.parent / "backup"),
                "MLAI_PUBLIC_ORIGIN": "https://pilot.example.test",
                "MLAI_TRUST_PROXY_TLS": "false",
                "MLAI_SESSION_SECRET": "s" * 48,
                "MLAI_IDENTITY_PROVIDER": "google-cloud-identity-platform",
                "MLAI_IDENTITY_ADAPTER_FACTORY": (
                    "app.identity.google_cloud:create_google_cloud_adapter"
                ),
                "MLAI_PROVIDER_REGISTRY_FACTORY": (
                    "deployment.providers:create_registry"
                ),
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
                "MLAI_DEPLOYMENT_COMMIT": "a" * 40,
            }
        )

    def test_concurrent_ensure_initialised_is_single_flight(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            database = _ControlledDatabase(Path(directory) / "single-flight.sqlite3")
            with ThreadPoolExecutor(max_workers=8) as executor:
                futures = [
                    executor.submit(database.ensure_initialised) for _ in range(8)
                ]
                self.assertTrue(database.apply_entered.wait(timeout=5))
                database.release_apply.set()
                for future in futures:
                    future.result(timeout=5)

        self.assertEqual(database.apply_count, 1)

    def test_failed_initialization_is_retryable_and_only_success_is_cached(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as directory:
            database = _ControlledDatabase(
                Path(directory) / "retry.sqlite3", fail_once=True
            )
            database.release_apply.set()
            with self.assertRaisesRegex(RuntimeError, "synthetic initialization"):
                database.ensure_initialised()
            database.ensure_initialised()
            database.ensure_initialised()

        self.assertEqual(database.apply_count, 2)

    def test_explicit_initialise_remains_schema_reconciliation(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            database = _ControlledDatabase(Path(directory) / "reconcile.sqlite3")
            database.release_apply.set()
            database.ensure_initialised()
            database.initialise()

        self.assertEqual(database.apply_count, 2)

    def test_failed_explicit_reconciliation_invalidates_cached_success(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            database = _ControlledDatabase(Path(directory) / "reconcile-retry.sqlite3")
            database.release_apply.set()
            database.ensure_initialised()
            database.fail_once = True
            with self.assertRaisesRegex(RuntimeError, "synthetic initialization"):
                database.initialise()
            database.ensure_initialised()

        self.assertEqual(database.apply_count, 3)

    def test_application_composition_applies_schema_once(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            database = SQLiteDatabase(Path(directory) / "composition.sqlite3")
            with patch.object(
                database, "_apply_schema", wraps=database._apply_schema
            ) as apply_schema:
                CanonicalApplication.build(database)

        self.assertEqual(apply_schema.call_count, 1)

    def test_postgresql_uses_the_same_cached_and_explicit_lifecycle(self) -> None:
        database = PostgreSQLDatabase("postgresql://test:test@localhost/test")
        with patch.object(database, "_apply_schema") as apply_schema:
            database.ensure_initialised()
            database.ensure_initialised()
            database.initialise()

        self.assertEqual(apply_schema.call_count, 2)

    def test_repeated_readiness_is_observational(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            database = SQLiteDatabase(Path(directory) / "readiness.sqlite3")
            database.initialise()
            config = self._configuration(database)
            with patch.object(
                database,
                "_apply_schema",
                wraps=database._apply_schema,
            ) as apply_schema:
                evaluator = OperationalReadinessEvaluator(config, database)
                evaluator.evaluate()
                evaluator.evaluate()
                PilotReleaseGate(config, database).evaluate()
                PilotReleaseGate(config, database).evaluate()
            self.assertEqual(apply_schema.call_count, 0)

    def test_missing_schema_fails_readiness_without_applying_ddl(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            missing = SQLiteDatabase(Path(directory) / "missing-readiness.sqlite3")
            config = self._configuration(missing)
            with patch.object(
                missing, "_apply_schema", wraps=missing._apply_schema
            ) as apply_schema:
                report = OperationalReadinessEvaluator(config, missing).evaluate()
                release = PilotReleaseGate(config, missing).evaluate()
            self.assertFalse(report.recovery_monitoring_support_ready)
            self.assertIn(
                "readiness_evidence_schema",
                [item.name for item in report.checks if not item.passed],
            )
            self.assertEqual(apply_schema.call_count, 0)
            self.assertNotIn("schema_migrations", missing.table_names())
            self.assertIn(
                "database_schema_ready",
                [item.name for item in release.checks if not item.passed],
            )


if __name__ == "__main__":
    unittest.main()
