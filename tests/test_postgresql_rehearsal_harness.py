"""Static safety contracts for the disposable PostgreSQL rehearsal harness."""

import socket
import unittest
from unittest.mock import Mock, patch
from urllib.parse import parse_qs, urlsplit

import psycopg

from tools.postgresql_rehearsal import (
    LOCK_TIMEOUT_MS,
    STATEMENT_TIMEOUT_MS,
    LocalDatabaseController,
    RedactingStream,
    canonical_expectations,
    isolated_session_case,
    run_rehearsal,
    timeout_url,
    validate_target,
)


class CaptureStream:
    def __init__(self) -> None:
        self.value = ""

    def write(self, value: str) -> None:
        self.value += value

    def flush(self) -> None:
        return None


class PostgreSQLRehearsalHarnessTests(unittest.TestCase):
    def test_target_must_be_allowlisted_and_loopback_local(self) -> None:
        safe = validate_target(
            "postgresql://operator:secret@127.0.0.1:5432/mlai_rehearsal"
        )
        self.assertEqual(safe, {"host": "127.0.0.1", "database": "mlai_rehearsal"})

        refused = (
            "postgresql://operator:secret@example.test/mlai_rehearsal",
            "postgresql://operator:secret@127.0.0.1/customer_data",
            "sqlite:///mlai_rehearsal",
        )
        for value in refused:
            with self.subTest(value=value), self.assertRaises(ValueError):
                validate_target(value)

    def test_every_resolved_localhost_address_must_be_loopback(self) -> None:
        addresses = [
            (socket.AF_INET, socket.SOCK_STREAM, 6, "", ("127.0.0.1", 5432)),
            (socket.AF_INET, socket.SOCK_STREAM, 6, "", ("192.0.2.10", 5432)),
        ]
        with patch(
            "tools.postgresql_rehearsal.socket.getaddrinfo", return_value=addresses
        ):
            with self.assertRaisesRegex(ValueError, "Every resolved"):
                validate_target("postgresql://operator:secret@localhost/mlai_rehearsal")

    def test_timeout_url_adds_bounded_session_settings(self) -> None:
        selected = timeout_url("postgresql://operator:secret@localhost/mlai_rehearsal")
        query = parse_qs(urlsplit(selected).query)
        self.assertEqual(query["connect_timeout"], ["5"])
        self.assertIn(f"statement_timeout={STATEMENT_TIMEOUT_MS}", query["options"][0])
        self.assertIn(f"lock_timeout={LOCK_TIMEOUT_MS}", query["options"][0])
        self.assertNotIn("+", urlsplit(selected).query)

    def test_output_redacts_url_and_password(self) -> None:
        url = "postgresql://operator:highly-secret@localhost/mlai_rehearsal"
        capture = CaptureStream()
        stream = RedactingStream(capture, url)
        stream.write(f"failed for {url}; password=highly-secret")
        self.assertNotIn(url, capture.value)
        self.assertNotIn("highly-secret", capture.value)

    def test_expectations_come_from_canonical_builders(self) -> None:
        tables, migrations = canonical_expectations()
        self.assertIn("tenant_memberships", tables)
        self.assertIn("pilot_sessions", tables)
        self.assertIn("marketing_workflows", tables)
        self.assertEqual(migrations, set(range(1, 20)))

    def test_catalog_guard_covers_all_non_system_object_classes(self) -> None:
        rows = [
            ("schema", "unexpected", "unexpected"),
            ("table", "public", "table_one"),
            ("view", "public", "view_one"),
            ("materialized_view", "public", "materialized_one"),
            ("sequence", "public", "sequence_one"),
            ("routine", "public", "function_one"),
            ("type", "public", "type_one"),
        ]
        connection = _FakeConnection(rows)
        controller = _controller()
        with patch(
            "tools.postgresql_rehearsal.psycopg.connect",
            return_value=_FakeContext(connection),
        ):
            self.assertEqual(controller.non_system_objects(), rows)
        query = str(connection.executions[0][0])
        for required in (
            "pg_namespace",
            "pg_class",
            "pg_proc",
            "pg_type",
            "materialized_view",
            "sequence",
        ):
            self.assertIn(required, query)

    def test_non_empty_target_is_refused_for_every_user_object_class(self) -> None:
        for object_kind in (
            "table",
            "view",
            "materialized_view",
            "sequence",
            "routine",
            "type",
            "schema",
        ):
            controller = _RunController(
                objects=[(object_kind, "public", f"synthetic_{object_kind}")]
            )
            suite_factory = Mock()
            with (
                self.subTest(object_kind=object_kind),
                self.assertRaisesRegex(RuntimeError, "non-empty"),
            ):
                run_rehearsal(
                    controller,
                    RedactingStream(CaptureStream(), ""),
                    suite_factory=suite_factory,
                )
            suite_factory.assert_not_called()
            self.assertEqual(controller.cleanup_calls, 0)

    def test_cleanup_is_registered_before_application_composition(self) -> None:
        controller = _ResetController()
        case_type = isolated_session_case(controller)
        case = case_type(
            "test_session_is_hashed_revocable_tenant_bound_and_csrf_protected"
        )
        result = unittest.TestResult()
        with patch(
            "tools.postgresql_rehearsal.CanonicalApplication.build",
            side_effect=RuntimeError("synthetic composition failure"),
        ):
            case.run(result)
        self.assertEqual(len(result.errors), 1)
        self.assertEqual(controller.reset_calls, 2)

    def test_drop_targets_exact_database_and_refuses_unrelated_name(self) -> None:
        controller = _controller()
        connection = _FakeConnection([])
        with patch(
            "tools.postgresql_rehearsal.psycopg.connect",
            return_value=_FakeContext(connection),
        ):
            controller.drop()
        self.assertEqual(connection.executions[0][1], (controller.database_name,))
        self.assertIn("mlai_rehearsal", str(connection.executions[1][0]))
        with self.assertRaisesRegex(ValueError, "unrelated"):
            controller.drop("customer_database")

    def test_drop_and_verify_checks_post_deletion_absence(self) -> None:
        controller = _controller()
        controller.drop = Mock()
        controller.exists = Mock(return_value=False)
        self.assertTrue(controller.drop_and_verify())
        controller.drop.assert_called_once_with("mlai_rehearsal")
        controller.exists.assert_called_once_with()

    def test_cleanup_runs_after_suite_failure(self) -> None:
        controller = _RunController()
        with (
            patch(
                "tools.postgresql_rehearsal.unittest.TextTestRunner.run",
                side_effect=RuntimeError("synthetic suite failure"),
            ),
            self.assertRaisesRegex(RuntimeError, "synthetic suite failure"),
        ):
            run_rehearsal(
                controller,
                RedactingStream(CaptureStream(), ""),
                suite_factory=lambda _controller: unittest.TestSuite(),
            )
        self.assertEqual(controller.cleanup_calls, 1)

    def test_cleanup_runs_after_statement_timeout(self) -> None:
        controller = _RunController()
        with (
            patch(
                "tools.postgresql_rehearsal.unittest.TextTestRunner.run",
                side_effect=psycopg.errors.QueryCanceled("synthetic timeout"),
            ),
            self.assertRaises(psycopg.errors.QueryCanceled),
        ):
            run_rehearsal(
                controller,
                RedactingStream(CaptureStream(), ""),
                suite_factory=lambda _controller: unittest.TestSuite(),
            )
        self.assertEqual(controller.cleanup_calls, 1)


class _FakeConnection:
    def __init__(self, rows) -> None:
        self.rows = rows
        self.executions = []

    def execute(self, statement, parameters=()):
        self.executions.append((statement, parameters))
        return self

    def fetchall(self):
        return self.rows


class _FakeContext:
    def __init__(self, connection) -> None:
        self.connection = connection

    def __enter__(self):
        return self.connection

    def __exit__(self, *_args):
        return False


class _RunController:
    database_name = "mlai_rehearsal"

    def __init__(self, *, objects=None) -> None:
        self.objects = [] if objects is None else objects
        self.cleanup_calls = 0

    def exists(self) -> bool:
        return True

    def non_system_objects(self):
        return self.objects

    def drop_and_verify(self) -> bool:
        self.cleanup_calls += 1
        return True


class _ResetController:
    database_url = "postgresql://operator:secret@127.0.0.1/mlai_rehearsal"

    def __init__(self) -> None:
        self.reset_calls = 0

    def reset_public_schema(self) -> None:
        self.reset_calls += 1


def _controller() -> LocalDatabaseController:
    controller = object.__new__(LocalDatabaseController)
    controller.database_url = "postgresql://operator:secret@127.0.0.1/mlai_rehearsal"
    controller.database_name = "mlai_rehearsal"
    controller.maintenance_url = "host=127.0.0.1 dbname=postgres"
    return controller


if __name__ == "__main__":
    unittest.main()
