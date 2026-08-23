"""Database initialization lifecycle and observational readiness tests."""

from __future__ import annotations

import json
import sqlite3
import tempfile
import threading
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from unittest.mock import patch

from app.application import CanonicalApplication
from app.campaign_planner.repository import CampaignPlanRepository
from app.compliance.repository import BrandRuleRepository
from app.database.connection import (
    DatabaseMigrationLockTimeoutError,
    DatabaseSchemaNotReadyError,
    SQLiteDatabase,
)
from app.database.factory import bootstrap_database
from app.database.postgresql import (
    POSTGRESQL_MIGRATION_LOCK_NAMESPACE,
    POSTGRESQL_MIGRATION_LOCK_TIMEOUT_SECONDS,
    PostgreSQLDatabase,
    postgresql_migration_advisory_key,
)
from app.database.repositories import (
    BrandRepository,
    BusinessIntelligenceRepository,
    CustomerIntelligenceRepository,
    MemoryRepository,
)
from app.identity.repository import IdentityRepository
from app.marketing_brief.repository import MarketingBriefRepository
from app.marketing_workflow.repository import MarketingWorkflowRepository
from app.operations.configuration import PilotConfiguration
from app.operations.operational_readiness import OperationalReadinessEvaluator
from app.operations.readiness_evidence import ReadinessEvidenceRepository
from app.operations.release_gate import PilotReleaseGate
from app.pilot_api.idempotency import IdempotencyRepository
from app.positioning_intelligence.repository import PositioningRepository
from app.product_intelligence.repository import ProductIntelligenceRepository
from app.prompts.repository import PromptPackRepository
from app.strategy_intelligence.repository import StrategyRepository
from app.tenants.repository import TenantRepository


class _ControlledDatabase(SQLiteDatabase):
    def __init__(self, path: Path, *, fail_once: bool = False) -> None:
        super().__init__(path)
        self.apply_count = 0
        self.fail_once = fail_once
        self.apply_entered = threading.Event()
        self.release_apply = threading.Event()

    def _apply_schema(self, existing_connection=None) -> None:
        self.apply_count += 1
        self.apply_entered.set()
        if not self.release_apply.wait(timeout=5):
            raise TimeoutError("test schema application was not released")
        if self.fail_once:
            self.fail_once = False
            raise RuntimeError("synthetic initialization failure")


class _SQLStateError(RuntimeError):
    def __init__(self, sqlstate: str) -> None:
        super().__init__("synthetic database failure")
        self.sqlstate = sqlstate


class _PostgreSQLLockState:
    def __init__(self) -> None:
        self.lock = threading.Lock()
        self.counter_lock = threading.Lock()
        self.lock_attempts = 0
        self.second_attempted = threading.Event()
        self.ready = False
        self.apply_count = 0


class _PostgreSQLLifecycleConnection:
    def __init__(
        self,
        state: _PostgreSQLLockState,
        *,
        lock_error: BaseException | None = None,
    ) -> None:
        self.state = state
        self.lock_error = lock_error
        self.events: list[str] = []
        self.closed = False
        self.owns_lock = False

    def execute(self, sql: str, parameters=()):
        self.events.append(sql.strip())
        if "pg_advisory_xact_lock" in sql:
            if self.lock_error is not None:
                raise self.lock_error
            with self.state.counter_lock:
                self.state.lock_attempts += 1
                if self.state.lock_attempts == 2:
                    self.state.second_attempted.set()
            if not self.state.lock.acquire(timeout=5):
                raise TimeoutError("synthetic advisory lock timeout")
            self.owns_lock = True
        return self

    def commit(self) -> None:
        self.events.append("commit")
        self._release()

    def rollback(self) -> None:
        self.events.append("rollback")
        self._release()

    def close(self) -> None:
        self.events.append("close")
        self.closed = True

    def _release(self) -> None:
        if self.owns_lock:
            self.owns_lock = False
            self.state.lock.release()


class _PostgreSQLLifecycleDatabase(PostgreSQLDatabase):
    def __init__(
        self,
        state: _PostgreSQLLockState,
        *,
        lock_error: BaseException | None = None,
        fail_schema: bool = False,
    ) -> None:
        super().__init__("postgresql://synthetic:synthetic@localhost/synthetic")
        self.state = state
        self.lock_error = lock_error
        self.fail_schema = fail_schema
        self.connections: list[_PostgreSQLLifecycleConnection] = []

    def connect(self) -> _PostgreSQLLifecycleConnection:
        connection = _PostgreSQLLifecycleConnection(
            self.state, lock_error=self.lock_error
        )
        self.connections.append(connection)
        return connection

    def _schema_is_ready(self, connection) -> bool:
        return self.state.ready

    def _apply_schema(self, existing_connection=None) -> None:
        if existing_connection is None or not existing_connection.owns_lock:
            raise AssertionError("schema application must hold the advisory lock")
        self.state.apply_count += 1
        if self.fail_schema:
            raise RuntimeError("synthetic schema failure")
        self.state.ready = True


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
            with patch.object(database, "migration_transaction") as migration:
                connection = migration.return_value.__enter__.return_value
                with patch.object(database, "_schema_is_ready", return_value=False):
                    database.ensure_initialised()
                    database.ensure_initialised()
                    database.initialise()

        self.assertEqual(apply_schema.call_count, 2)
        self.assertEqual(apply_schema.call_args.args, (connection,))

    def test_postgresql_advisory_key_is_stable_golden_vector(self) -> None:
        self.assertEqual(
            POSTGRESQL_MIGRATION_LOCK_NAMESPACE,
            "earthonox.marketinglabai.schema-migration.v1",
        )
        self.assertEqual(POSTGRESQL_MIGRATION_LOCK_TIMEOUT_SECONDS, 5)
        self.assertEqual(postgresql_migration_advisory_key(), -1708253074467796067)

    def test_postgresql_lock_is_held_through_commit_and_rollback(self) -> None:
        success_state = _PostgreSQLLockState()
        success = _PostgreSQLLifecycleDatabase(success_state)
        success.ensure_initialised()
        self.assertFalse(success_state.lock.locked())
        self.assertEqual(success.connections[0].events[-2:], ["commit", "close"])

        failure_state = _PostgreSQLLockState()
        failure = _PostgreSQLLifecycleDatabase(failure_state, fail_schema=True)
        with self.assertRaisesRegex(RuntimeError, "synthetic schema failure"):
            failure.ensure_initialised()
        self.assertFalse(failure_state.lock.locked())
        self.assertEqual(failure.connections[0].events[-2:], ["rollback", "close"])

    def test_postgresql_lock_timeout_is_classified_and_closed(self) -> None:
        state = _PostgreSQLLockState()
        database = _PostgreSQLLifecycleDatabase(
            state, lock_error=_SQLStateError("55P03")
        )

        with self.assertRaises(DatabaseMigrationLockTimeoutError):
            database.ensure_initialised()

        self.assertEqual(state.apply_count, 0)
        self.assertTrue(database.connections[0].closed)
        self.assertIn(
            "SELECT set_config('lock_timeout', ?, true)",
            database.connections[0].events,
        )

    def test_independent_postgresql_instances_serialize_and_skip_duplicate_ddl(
        self,
    ) -> None:
        state = _PostgreSQLLockState()
        first = _PostgreSQLLifecycleDatabase(state)
        second = _PostgreSQLLifecycleDatabase(state)
        entered = threading.Event()
        release = threading.Event()
        original_apply = first._apply_schema

        def held_apply(existing_connection=None) -> None:
            entered.set()
            if not release.wait(timeout=5):
                raise TimeoutError("test did not release PostgreSQL migration")
            original_apply(existing_connection)

        with patch.object(first, "_apply_schema", side_effect=held_apply):
            with ThreadPoolExecutor(max_workers=2) as executor:
                first_result = executor.submit(first.ensure_initialised)
                self.assertTrue(entered.wait(timeout=5))
                second_result = executor.submit(second.ensure_initialised)
                self.assertTrue(state.second_attempted.wait(timeout=5))
                release.set()
                first_result.result(timeout=5)
                second_result.result(timeout=5)

        self.assertEqual(state.apply_count, 1)
        self.assertTrue(state.ready)

    def test_runtime_composition_requires_ready_schema_without_initializing(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "runtime.sqlite3"
            database = SQLiteDatabase(path)
            with patch.object(database, "ensure_initialised") as ensure:
                with self.assertRaises(DatabaseSchemaNotReadyError):
                    CanonicalApplication.build(database, initialise_schema=False)
            ensure.assert_not_called()

            bootstrap_database(database)
            with patch.object(database, "ensure_initialised") as ensure:
                application = CanonicalApplication.build(
                    database, initialise_schema=False
                )
            self.assertIs(application.database, database)
            ensure.assert_not_called()

    def test_sqlite_independent_instances_use_begin_immediate_and_skip_ddl(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "coordinated.sqlite3"
            first = SQLiteDatabase(path)
            second = SQLiteDatabase(path)
            with (
                patch.object(
                    first, "_apply_schema", wraps=first._apply_schema
                ) as first_apply,
                patch.object(
                    second, "_apply_schema", wraps=second._apply_schema
                ) as second_apply,
            ):
                with ThreadPoolExecutor(max_workers=2) as executor:
                    futures = [
                        executor.submit(first.ensure_initialised),
                        executor.submit(second.ensure_initialised),
                    ]
                    for future in futures:
                        future.result(timeout=10)

            self.assertEqual(first_apply.call_count + second_apply.call_count, 1)
            self.assertTrue(first.schema_is_ready())

    def test_sqlite_locked_migration_is_classified(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            database = SQLiteDatabase(Path(directory) / "locked.sqlite3")
            connection = database.connect()
            connection.execute("BEGIN IMMEDIATE")
            locked = sqlite3.OperationalError("database is locked")
            try:
                with patch.object(database, "connect") as connect:
                    contender = connect.return_value
                    contender.execute.side_effect = locked
                    with self.assertRaises(DatabaseMigrationLockTimeoutError):
                        database.ensure_initialised()
                    contender.rollback.assert_called_once()
                    contender.close.assert_called_once()
            finally:
                connection.rollback()
                connection.close()

    def test_repository_constructors_do_not_initialize(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            database = SQLiteDatabase(Path(directory) / "constructors.sqlite3")
            repositories = (
                TenantRepository,
                IdentityRepository,
                BrandRepository,
                BusinessIntelligenceRepository,
                CustomerIntelligenceRepository,
                MemoryRepository,
                ProductIntelligenceRepository,
                PositioningRepository,
                StrategyRepository,
                CampaignPlanRepository,
                MarketingBriefRepository,
                MarketingWorkflowRepository,
                PromptPackRepository,
                BrandRuleRepository,
                IdempotencyRepository,
                ReadinessEvidenceRepository,
            )
            with patch.object(database, "ensure_initialised") as ensure:
                for repository in repositories:
                    repository(database)

            ensure.assert_not_called()
            self.assertFalse(database.database_path.exists())

    def test_explicit_standalone_bootstrap_and_uninitialised_failure(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            missing = SQLiteDatabase(Path(directory) / "standalone.sqlite3")
            repository = BrandRepository(missing)
            with self.assertRaises(DatabaseSchemaNotReadyError):
                repository.exists("missing-brand")

            self.assertIs(bootstrap_database(missing), missing)
            self.assertFalse(repository.exists("missing-brand"))

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
            self.assertFalse(missing.database_path.exists())
            self.assertIn(
                "database_schema_ready",
                [item.name for item in release.checks if not item.passed],
            )


if __name__ == "__main__":
    unittest.main()
