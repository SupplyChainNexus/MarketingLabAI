"""Disposable local PostgreSQL rehearsal for security-sensitive session contracts."""

from __future__ import annotations

import io
import ipaddress
import json
import os
import re
import socket
import sys
import tempfile
import unittest
from pathlib import Path
from urllib.parse import parse_qsl, quote, urlencode, urlsplit, urlunsplit

import psycopg
from psycopg import sql
from psycopg.conninfo import conninfo_to_dict, make_conninfo

from app.application import CanonicalApplication
from app.database.postgresql import (
    PostgreSQLDatabase,
    build_postgresql_schema,
    build_postgresql_seed_rows,
)
from app.identity import TenantMembership, TenantRole
from app.operations import PilotConfiguration, PilotSessionProvider
from app.tenants.models import Tenant
from tests.test_pilot_operations import PilotOperationsTests, TrustedTestIdentity

LOCAL_HOSTS = frozenset({"127.0.0.1", "localhost", "::1"})
TARGET_PATTERN = re.compile(r"^mlai_rehearsal(?:_[a-z0-9_]+)?$")
CONNECT_TIMEOUT_SECONDS = 5
STATEMENT_TIMEOUT_MS = 10_000
LOCK_TIMEOUT_MS = 5_000
TIMEOUT_PROBE_MS = 250

SESSION_TESTS = (
    "test_session_is_hashed_revocable_tenant_bound_and_csrf_protected",
    "test_renewal_rotates_identifier_and_csrf_and_preserves_anchor",
    "test_idle_expiry_blocks_use_and_renewal_at_fifteen_minutes",
    "test_failed_csrf_renewal_does_not_replace_authoritative_session",
    "test_tenant_mismatched_session_cannot_renew",
    "test_explicitly_revoked_session_cannot_renew",
    "test_successor_insert_failure_rolls_back_predecessor_revocation",
    "test_renewal_caps_idle_deadline_at_original_absolute_expiry",
    "test_competing_renewals_allow_at_most_one_success",
    "test_membership_role_or_active_change_invalidates_sessions",
    "test_membership_change_invalidates_successor_when_renewal_commits_first",
    "test_membership_invalidation_audit_contains_only_safe_metadata",
    "test_renewal_audit_contains_no_session_or_csrf_material",
    "test_creation_audit_failure_leaves_no_active_session",
    "test_renewal_audit_failure_rolls_back_to_active_predecessor",
    "test_session_rechecks_tenant_and_active_membership",
)


def validate_target(database_url: str) -> dict[str, str]:
    """Return safe connection fields or refuse a non-local/non-disposable target."""

    selected = str(database_url).strip()
    if not selected:
        raise ValueError("MLAI_DATABASE_URL is required.")
    parts = urlsplit(selected)
    database_name = parts.path.lstrip("/")
    if parts.scheme not in {"postgres", "postgresql"}:
        raise ValueError("The rehearsal target must use PostgreSQL.")
    if parts.hostname not in LOCAL_HOSTS:
        raise ValueError("The rehearsal target must be loopback-local.")
    resolved = {
        str(ipaddress.ip_address(item[4][0]))
        for item in socket.getaddrinfo(
            parts.hostname,
            parts.port or 5432,
            type=socket.SOCK_STREAM,
        )
    }
    if not resolved or not all(
        ipaddress.ip_address(address).is_loopback for address in resolved
    ):
        raise ValueError("Every resolved rehearsal address must be loopback-local.")
    if not TARGET_PATTERN.fullmatch(database_name):
        raise ValueError("The rehearsal database name is not allowlisted.")
    return {"host": str(parts.hostname), "database": database_name}


def timeout_url(
    database_url: str,
    *,
    statement_timeout_ms: int = STATEMENT_TIMEOUT_MS,
    lock_timeout_ms: int = LOCK_TIMEOUT_MS,
) -> str:
    """Add bounded client/session settings without changing the PostgreSQL server."""

    parts = urlsplit(database_url)
    query = dict(parse_qsl(parts.query, keep_blank_values=True))
    query["connect_timeout"] = str(CONNECT_TIMEOUT_SECONDS)
    query["options"] = (
        f"-c statement_timeout={int(statement_timeout_ms)} "
        f"-c lock_timeout={int(lock_timeout_ms)}"
    )
    return urlunsplit(parts._replace(query=urlencode(query, quote_via=quote)))


def canonical_expectations() -> tuple[set[str], set[int]]:
    """Derive expectations from the same canonical builders used by production."""

    tables = {
        match.group(1)
        for statement in build_postgresql_schema()
        if (
            match := re.match(
                r"\s*CREATE TABLE IF NOT EXISTS\s+([A-Za-z_][\w]*)", statement
            )
        )
    }
    migrations = {
        int(row[0]) for row in build_postgresql_seed_rows()["schema_migrations"]
    }
    return tables, migrations


class LocalDatabaseController:
    """Create and remove only the exact allowlisted disposable local database."""

    def __init__(self, database_url: str) -> None:
        safe = validate_target(database_url)
        self.database_url = timeout_url(database_url)
        self.database_name = safe["database"]
        parameters = conninfo_to_dict(self.database_url)
        parameters["dbname"] = "postgres"
        self.maintenance_url = make_conninfo(**parameters)

    def exists(self) -> bool:
        with psycopg.connect(self.maintenance_url) as connection:
            return (
                connection.execute(
                    "SELECT 1 FROM pg_database WHERE datname = %s",
                    (self.database_name,),
                ).fetchone()
                is not None
            )

    def non_system_objects(self) -> list[tuple[str, str, str]]:
        """Return every catalog object that makes the target non-empty."""

        with psycopg.connect(self.database_url) as connection:
            return connection.execute("""
                WITH disallowed_schemas AS (
                    SELECT 'schema'::text AS object_kind,
                           nspname::text AS schema_name,
                           nspname::text AS object_name
                    FROM pg_namespace
                    WHERE nspname <> 'public'
                      AND nspname NOT IN ('pg_catalog', 'information_schema')
                      AND nspname NOT LIKE 'pg_toast%'
                      AND nspname NOT LIKE 'pg_temp_%'
                ), relations AS (
                    SELECT CASE c.relkind
                               WHEN 'v' THEN 'view'
                               WHEN 'm' THEN 'materialized_view'
                               WHEN 'S' THEN 'sequence'
                               ELSE 'table'
                           END::text AS object_kind,
                           n.nspname::text AS schema_name,
                           c.relname::text AS object_name
                    FROM pg_class c
                    JOIN pg_namespace n ON n.oid = c.relnamespace
                    WHERE n.nspname = 'public'
                      AND c.relkind IN ('r', 'p', 'v', 'm', 'S', 'f')
                ), routines AS (
                    SELECT 'routine'::text AS object_kind,
                           n.nspname::text AS schema_name,
                           p.proname::text AS object_name
                    FROM pg_proc p
                    JOIN pg_namespace n ON n.oid = p.pronamespace
                    WHERE n.nspname = 'public'
                ), user_types AS (
                    SELECT 'type'::text AS object_kind,
                           n.nspname::text AS schema_name,
                           t.typname::text AS object_name
                    FROM pg_type t
                    JOIN pg_namespace n ON n.oid = t.typnamespace
                    WHERE n.nspname = 'public'
                )
                SELECT object_kind, schema_name, object_name FROM disallowed_schemas
                UNION ALL
                SELECT object_kind, schema_name, object_name FROM relations
                UNION ALL
                SELECT object_kind, schema_name, object_name FROM routines
                UNION ALL
                SELECT object_kind, schema_name, object_name FROM user_types
                ORDER BY object_kind, schema_name, object_name
                """).fetchall()

    def reset_public_schema(self) -> None:
        """Reset state inside the disposable target without CREATEDB authority."""

        with psycopg.connect(self.database_url, autocommit=True) as connection:
            connection.execute("DROP SCHEMA IF EXISTS public CASCADE")
            connection.execute("CREATE SCHEMA public")

    def drop(self, database_name: str | None = None) -> None:
        selected = self.database_name if database_name is None else database_name
        if selected != self.database_name:
            raise ValueError("Refusing to delete an unrelated database.")
        with psycopg.connect(self.maintenance_url, autocommit=True) as connection:
            connection.execute(
                """SELECT pg_terminate_backend(pid)
                   FROM pg_stat_activity
                   WHERE datname = %s AND pid <> pg_backend_pid()""",
                (self.database_name,),
            )
            connection.execute(
                sql.SQL("DROP DATABASE IF EXISTS {}").format(
                    sql.Identifier(self.database_name)
                )
            )

    def drop_and_verify(self) -> bool:
        self.drop(self.database_name)
        return not self.exists()


class RedactingStream(io.TextIOBase):
    """Stream test output while removing the URL and embedded password."""

    def __init__(self, stream, database_url: str) -> None:
        self.stream = stream
        parts = urlsplit(database_url)
        self.prohibited = tuple(item for item in (database_url, parts.password) if item)

    def write(self, value: str) -> int:
        safe = str(value)
        for prohibited in self.prohibited:
            safe = safe.replace(prohibited, "[REDACTED]")
        self.stream.write(safe)
        self.stream.flush()
        return len(value)

    def flush(self) -> None:
        self.stream.flush()


def isolated_session_case(controller: LocalDatabaseController):
    class IsolatedPostgreSQLSessionTests(PilotOperationsTests):
        def setUp(self) -> None:
            controller.reset_public_schema()
            self.addCleanup(controller.reset_public_schema)
            self.temp = tempfile.TemporaryDirectory()
            self.addCleanup(self.temp.cleanup)
            root = Path(self.temp.name)
            self.database = PostgreSQLDatabase(controller.database_url)
            self.application = CanonicalApplication.build(self.database)
            self.application.tenants.save(Tenant(tenant_id="tenant-one", name="Pilot"))
            self.application.identities.save_membership(
                TenantMembership(
                    subject_id="operator-one",
                    provider="oidc-test",
                    tenant_id="tenant-one",
                    role=TenantRole.ADMIN,
                )
            )
            self.config = PilotConfiguration.from_environment(
                {
                    "MLAI_ENVIRONMENT": "synthetic-pilot",
                    "MLAI_DATABASE_PATH": str(root / "unused.sqlite3"),
                    "MLAI_BACKUP_DIRECTORY": str(root / "backups"),
                    "MLAI_PUBLIC_ORIGIN": "https://pilot.example.test",
                    "MLAI_TRUST_PROXY_TLS": "false",
                    "MLAI_SESSION_SECRET": "s" * 48,
                    "MLAI_IDENTITY_PROVIDER": "oidc-test",
                    "MLAI_IDENTITY_ADAPTER_FACTORY": (
                        "deployment.identity:create_adapter"
                    ),
                    "MLAI_PROVIDER_REGISTRY_FACTORY": (
                        "deployment.providers:create_registry"
                    ),
                    "MLAI_FOUNDER_INVITATION_HASHES_JSON": json.dumps(
                        {
                            "strand-auto-parts-pilot": "a" * 64,
                            "velani-wholesale-pilot": "b" * 64,
                        }
                    ),
                    "MLAI_ALLOW_REAL_CUSTOMER_DATA": "false",
                }
            )
            self.sessions = PilotSessionProvider(
                self.application, TrustedTestIdentity(), "s" * 48
            )

    IsolatedPostgreSQLSessionTests.__name__ = "IsolatedPostgreSQLSessionTests"
    return IsolatedPostgreSQLSessionTests


def build_live_suite(controller: LocalDatabaseController) -> unittest.TestSuite:
    IsolatedPostgreSQLSessionTests = isolated_session_case(controller)

    class PostgreSQLHarnessContracts(unittest.TestCase):
        def setUp(self) -> None:
            controller.reset_public_schema()
            self.addCleanup(controller.reset_public_schema)

        def test_canonical_schema_and_migration_parity(self) -> None:
            expected_tables, expected_migrations = canonical_expectations()
            database = PostgreSQLDatabase(controller.database_url)
            database.initialise()
            with database.connection() as connection:
                rows = connection.execute(
                    "SELECT version FROM schema_migrations ORDER BY version"
                ).fetchall()
            self.assertEqual(set(database.table_names()), expected_tables)
            self.assertEqual({int(row["version"]) for row in rows}, expected_migrations)
            self.assertEqual(database.integrity_check(), "ok")

        def test_statement_timeout_is_enforced(self) -> None:
            probe_url = timeout_url(
                controller.database_url,
                statement_timeout_ms=TIMEOUT_PROBE_MS,
                lock_timeout_ms=TIMEOUT_PROBE_MS,
            )
            with psycopg.connect(probe_url) as connection:
                with self.assertRaises(psycopg.errors.QueryCanceled):
                    connection.execute("SELECT pg_sleep(2)")

    suite = unittest.TestSuite()
    suite.addTests(
        PostgreSQLHarnessContracts(name)
        for name in (
            "test_canonical_schema_and_migration_parity",
            "test_statement_timeout_is_enforced",
        )
    )
    suite.addTests(IsolatedPostgreSQLSessionTests(name) for name in SESSION_TESTS)
    return suite


def run_rehearsal(
    controller: LocalDatabaseController,
    stream: RedactingStream,
    *,
    suite_factory=build_live_suite,
) -> int:
    if not controller.exists():
        raise RuntimeError(
            "The allowlisted empty rehearsal database must be provisioned first."
        )
    if controller.non_system_objects():
        raise RuntimeError("Refusing to overwrite a non-empty rehearsal database.")
    cleanup_verified = False
    try:
        result = unittest.TextTestRunner(stream=stream, verbosity=2).run(
            suite_factory(controller)
        )
    finally:
        cleanup_verified = controller.drop_and_verify()
        stream.write(
            f"CLEANUP database={controller.database_name} "
            f"exists={not cleanup_verified}\n"
        )
    return 0 if result.wasSuccessful() and cleanup_verified else 1


def main() -> int:
    database_url = os.environ.get("MLAI_DATABASE_URL", "")
    controller = LocalDatabaseController(database_url)
    safe = validate_target(database_url)
    stream = RedactingStream(sys.stdout, database_url)
    stream.write(
        f"LOCAL_POSTGRESQL_REHEARSAL database={safe['database']} "
        f"host={safe['host']} credentials=protected\n"
    )
    return run_rehearsal(controller, stream)


if __name__ == "__main__":
    selected_url = os.environ.get("MLAI_DATABASE_URL", "")
    try:
        raise SystemExit(main())
    except Exception as error:
        RedactingStream(sys.stderr, selected_url).write(
            f"REHEARSAL_STARTUP_FAILED type={type(error).__name__}: {error}\n"
        )
        raise SystemExit(1) from None
