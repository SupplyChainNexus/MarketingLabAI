"""Privacy-safe database lifecycle telemetry tests."""

from __future__ import annotations

import json
import sqlite3
import tempfile
import threading
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from unittest.mock import patch

from app.database.connection import (
    DatabaseMigrationLockTimeoutError,
    SQLiteDatabase,
)
from app.database.lifecycle_telemetry import DatabaseLifecycleEvent
from app.database.postgresql import PostgreSQLDatabase
from app.operations.observability import (
    DatabaseLifecycleJsonEventSink,
    PrivacySafeJsonLogger,
)


class _Clock:
    def __init__(self) -> None:
        self.value = 10.0

    def __call__(self) -> float:
        value = self.value
        self.value += 0.125
        return value


class _Sink:
    def __init__(self, *, fail: bool = False) -> None:
        self.events: list[DatabaseLifecycleEvent] = []
        self.fail = fail
        self.initialization_waiting = threading.Event()

    def emit(self, event: DatabaseLifecycleEvent) -> None:
        self.events.append(event)
        if event.name == "initialization_waiting":
            self.initialization_waiting.set()
        if self.fail:
            raise RuntimeError("synthetic sink failure")


class _FalseValuedSink(_Sink):
    def __bool__(self) -> bool:
        return False


class _TelemetryDatabase(SQLiteDatabase):
    def __init__(self, path: Path, sink: _Sink, clock: _Clock) -> None:
        super().__init__(path, lifecycle_event_sink=sink, monotonic=clock)
        self.fail_once = False
        self.entered = threading.Event()
        self.release = threading.Event()

    def _apply_schema(self, existing_connection=None) -> None:
        self.entered.set()
        if not self.release.wait(timeout=5):
            raise TimeoutError("schema application release timed out")
        if self.fail_once:
            self.fail_once = False
            raise RuntimeError("synthetic initialization failure")


class _SQLStateError(RuntimeError):
    sqlstate = "55P03"


class _TimeoutConnection:
    def execute(self, sql: str, parameters=()):
        del parameters
        if "pg_advisory_xact_lock" in sql:
            raise _SQLStateError("synthetic lock timeout")
        return self

    def rollback(self) -> None: ...

    def close(self) -> None: ...


class _TimeoutPostgreSQLDatabase(PostgreSQLDatabase):
    def connect(self):
        return _TimeoutConnection()


class DatabaseLifecycleTelemetryTests(unittest.TestCase):
    def test_initialization_order_wait_duration_and_safe_metadata(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            sink = _Sink()
            database = _TelemetryDatabase(
                Path(directory) / "telemetry.sqlite3", sink, _Clock()
            )
            with ThreadPoolExecutor(max_workers=2) as executor:
                holder = executor.submit(database.ensure_initialised)
                self.assertTrue(database.entered.wait(timeout=5))
                waiter = executor.submit(database.ensure_initialised)
                try:
                    self.assertTrue(sink.initialization_waiting.wait(timeout=5))
                finally:
                    database.release.set()
                holder.result(timeout=5)
                waiter.result(timeout=5)

        names = [event.name for event in sink.events]
        self.assertEqual(
            names[0:3],
            [
                "initialization_requested",
                "initialization_started",
                "migration_lock_waiting",
            ],
        )
        self.assertIn("migration_lock_acquired", names)
        self.assertIn("initialization_waiting", names)
        self.assertEqual(names.count("initialization_started"), 1)
        self.assertEqual(names.count("initialization_succeeded"), 2)
        waited = next(
            event
            for event in sink.events
            if event.name == "initialization_succeeded"
            and event.wait_duration_ms is not None
        )
        self.assertGreater(waited.wait_duration_ms, 0)
        for event in sink.events:
            self.assertEqual(event.backend, "sqlite")
            self.assertEqual(event.target_migration_version, 20)
            self.assertRegex(event.target_fingerprint, r"^[0-9a-f]{16}$")
            self.assertNotIn(str(database.database_path), repr(event))

    def test_failure_retry_and_explicit_reconciliation_events(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            sink = _Sink()
            database = _TelemetryDatabase(
                Path(directory) / "retry.sqlite3", sink, _Clock()
            )
            database.release.set()
            database.fail_once = True
            with self.assertRaises(RuntimeError):
                database.ensure_initialised()
            database.ensure_initialised()
            database.initialise()

        names = [event.name for event in sink.events]
        self.assertIn("initialization_failed", names)
        self.assertIn("initialization_retried", names)
        self.assertIn("explicit_reconciliation", names)
        failure = next(
            event for event in sink.events if event.name == "initialization_failed"
        )
        self.assertEqual(failure.failure_category, "runtimeerror")
        self.assertEqual(failure.retry_ordinal, 1)
        self.assertIsNotNone(failure.duration_ms)
        success_ordinals = [
            event.retry_ordinal
            for event in sink.events
            if event.name == "initialization_succeeded"
        ]
        self.assertEqual(success_ordinals, [1, 1])

    def test_postgresql_lock_timeout_is_observed_without_credentials(self) -> None:
        sink = _Sink()
        database = _TimeoutPostgreSQLDatabase(
            "postgresql://private-user:private-password@localhost/private-db",
            lifecycle_event_sink=sink,
            monotonic=_Clock(),
        )
        with self.assertRaises(DatabaseMigrationLockTimeoutError):
            database.ensure_initialised()

        timeout = next(
            event for event in sink.events if event.name == "migration_lock_timeout"
        )
        self.assertEqual(timeout.backend, "postgresql")
        self.assertEqual(timeout.failure_category, "lock_timeout")
        self.assertGreater(timeout.wait_duration_ms, 0)
        rendered = repr(sink.events)
        self.assertNotIn("private-user", rendered)
        self.assertNotIn("private-password", rendered)
        self.assertNotIn("private-db", rendered)

    def test_readiness_and_initialization_ignore_sink_failure(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            database = SQLiteDatabase(
                Path(directory) / "sink-failure.sqlite3",
                lifecycle_event_sink=_Sink(fail=True),
            )
            self.assertFalse(database.schema_readiness().ready)
            database.ensure_initialised()
            self.assertTrue(database.schema_readiness().ready)

    def test_postgresql_sink_failure_does_not_replace_lock_timeout(self) -> None:
        database = _TimeoutPostgreSQLDatabase(
            "postgresql://user:password@localhost/database",
            lifecycle_event_sink=_Sink(fail=True),
        )
        with self.assertRaises(DatabaseMigrationLockTimeoutError):
            database.ensure_initialised()

    def test_false_valued_sink_is_preserved_and_readiness_observes_version(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as directory:
            sink = _FalseValuedSink()
            database = SQLiteDatabase(
                Path(directory) / "version.sqlite3",
                lifecycle_event_sink=sink,
            )
            database.ensure_initialised()
            with database.transaction() as connection:
                connection.execute("DELETE FROM schema_migrations WHERE version = 18")
            self.assertFalse(database.schema_readiness().ready)

        readiness = [
            event for event in sink.events if event.name == "readiness_failure"
        ]
        self.assertEqual(len(readiness), 1)
        self.assertEqual(readiness[0].observed_version, 20)

    def test_inspection_failure_preserves_readable_migration_version(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "inspection-failure.sqlite3"
            SQLiteDatabase(path).ensure_initialised()
            sink = _Sink()
            database = SQLiteDatabase(path, lifecycle_event_sink=sink)
            with patch(
                "app.database.connection.observe_sqlite_schema",
                side_effect=RuntimeError("synthetic inspection failure"),
            ):
                report = database.schema_readiness()

        self.assertFalse(report.ready)
        self.assertEqual(report.failure_categories, ("inspection",))
        readiness = [
            event for event in sink.events if event.name == "readiness_failure"
        ]
        self.assertEqual(len(readiness), 1)
        self.assertEqual(readiness[0].observed_version, 20)
        self.assertEqual(readiness[0].failure_category, "inspection")

    def test_unavailable_migration_metadata_reports_no_observed_version(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "metadata-unavailable.sqlite3"
            connection = sqlite3.connect(path)
            connection.close()
            sink = _Sink()
            database = SQLiteDatabase(path, lifecycle_event_sink=sink)
            with patch(
                "app.database.connection.observe_sqlite_schema",
                side_effect=RuntimeError("synthetic inspection failure"),
            ):
                report = database.schema_readiness()

        self.assertFalse(report.ready)
        readiness = [
            event for event in sink.events if event.name == "readiness_failure"
        ]
        self.assertEqual(len(readiness), 1)
        self.assertIsNone(readiness[0].observed_version)

    def test_successful_ready_schema_recheck_reports_observed_version(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "ready.sqlite3"
            SQLiteDatabase(path).ensure_initialised()
            sink = _Sink()
            database = SQLiteDatabase(path, lifecycle_event_sink=sink)
            database.ensure_initialised()

        succeeded = [
            event for event in sink.events if event.name == "initialization_succeeded"
        ]
        self.assertEqual(len(succeeded), 1)
        self.assertEqual(succeeded[0].observed_version, 20)

    def test_sqlite_target_and_json_log_do_not_disclose_path(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            private_path = Path(directory) / "customer-name-secret.sqlite3"
            events = _Sink()
            database = SQLiteDatabase(private_path, lifecycle_event_sink=events)
            database.ensure_initialised()

        lines: list[str] = []
        json_sink = DatabaseLifecycleJsonEventSink(PrivacySafeJsonLogger(lines.append))
        for event in events.events:
            json_sink.emit(event)
        rendered_events = repr(events.events)
        rendered_logs = "\n".join(lines)
        for sensitive in (str(private_path), private_path.name, directory):
            self.assertNotIn(sensitive, rendered_events)
            self.assertNotIn(sensitive, rendered_logs)

    def test_json_consumer_emits_only_allowlisted_metadata(self) -> None:
        lines: list[str] = []
        sink = DatabaseLifecycleJsonEventSink(PrivacySafeJsonLogger(lines.append))
        sink.emit(
            DatabaseLifecycleEvent(
                name="initialization_succeeded",
                backend="sqlite",
                operation_type="ensure_initialised",
                target_migration_version=18,
                observed_version=18,
                duration_ms=125,
                wait_duration_ms=25,
                failure_category=None,
                retry_ordinal=0,
                target_fingerprint="0123456789abcdef",
            )
        )
        payload = json.loads(lines[0])
        self.assertEqual(
            set(payload),
            {
                "backend",
                "duration_ms",
                "event",
                "observed_version",
                "operation_type",
                "retry_ordinal",
                "target_fingerprint",
                "target_migration_version",
                "timestamp",
                "wait_duration_ms",
            },
        )


if __name__ == "__main__":
    unittest.main()
