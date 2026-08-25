"""PostgreSQL compatibility boundary for the canonical pilot repositories."""

from __future__ import annotations

import hashlib
import re
import tempfile
from collections.abc import Iterator, Mapping, Sequence
from contextlib import contextmanager, nullcontext
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

from app.database.connection import (
    DatabaseMigrationLockTimeoutError,
    DatabaseSchemaNotReadyError,
    SQLiteDatabase,
)
from app.database.lifecycle_telemetry import (
    DatabaseLifecycleEventSink,
    MonotonicClock,
    monotonic_clock,
    target_fingerprint,
)
from app.database.schema_readiness import (
    SchemaReadinessReport,
    observe_postgresql_schema,
    unavailable_schema_report,
)

POSTGRESQL_MIGRATION_LOCK_NAMESPACE = "earthonox.marketinglabai.schema-migration.v1"
POSTGRESQL_MIGRATION_LOCK_TIMEOUT_SECONDS = 5

POSTGRESQL_IMMUTABILITY_STATEMENTS = (
    """
    CREATE OR REPLACE FUNCTION prevent_campaign_asset_revision_mutation()
    RETURNS trigger
    LANGUAGE plpgsql
    AS $$
    BEGIN
        RAISE EXCEPTION 'campaign_asset_revisions are immutable';
    END;
    $$
    """,
    "DROP TRIGGER IF EXISTS prevent_campaign_asset_revision_update ON campaign_asset_revisions",
    """
    CREATE TRIGGER prevent_campaign_asset_revision_update
    BEFORE UPDATE ON campaign_asset_revisions
    FOR EACH ROW EXECUTE FUNCTION prevent_campaign_asset_revision_mutation()
    """,
    "DROP TRIGGER IF EXISTS prevent_campaign_asset_revision_delete ON campaign_asset_revisions",
    """
    CREATE TRIGGER prevent_campaign_asset_revision_delete
    BEFORE DELETE ON campaign_asset_revisions
    FOR EACH ROW EXECUTE FUNCTION prevent_campaign_asset_revision_mutation()
    """,
)


def postgresql_migration_advisory_key() -> int:
    """Return the stable signed 64-bit lock key for the governed namespace."""

    digest = hashlib.sha256(
        POSTGRESQL_MIGRATION_LOCK_NAMESPACE.encode("utf-8")
    ).digest()
    return int.from_bytes(digest[:8], byteorder="big", signed=True)


def _error_has_sqlstate(error: BaseException, sqlstate: str) -> bool:
    current: BaseException | None = error
    while current is not None:
        if getattr(current, "sqlstate", None) == sqlstate:
            return True
        current = current.__cause__
    return False


class PostgreSQLConfigurationError(ValueError):
    """Raised when a PostgreSQL connection value is unsafe or incomplete."""


class HybridRow(Mapping[str, Any]):
    """Expose PostgreSQL rows through SQLite-compatible key and index access."""

    def __init__(self, columns: Sequence[str], values: Sequence[Any]) -> None:
        self._columns = tuple(columns)
        self._values = tuple(values)
        self._mapping = dict(zip(self._columns, self._values, strict=True))

    def __getitem__(self, key: str | int) -> Any:
        if isinstance(key, int):
            return self._values[key]
        return self._mapping[key]

    def __iter__(self):
        return iter(self._columns)

    def __len__(self) -> int:
        return len(self._columns)


def _replace_qmark_placeholders(sql: str) -> str:
    output: list[str] = []
    quoted = False
    index = 0
    while index < len(sql):
        character = sql[index]
        if character == "'":
            output.append(character)
            if quoted and index + 1 < len(sql) and sql[index + 1] == "'":
                output.append("'")
                index += 2
                continue
            quoted = not quoted
        elif character == "?" and not quoted:
            output.append("%s")
        else:
            output.append(character)
        index += 1
    if quoted:
        raise ValueError("SQL contains an unterminated string literal.")
    return "".join(output)


def compile_postgresql_sql(sql: str) -> str:
    """Translate the repository's bounded SQLite SQL subset to PostgreSQL."""

    compiled = re.sub(
        r"strftime\('%Y-%m-%dT%H:%M:%fZ',\s*'now'\)",
        "to_char(clock_timestamp() at time zone 'UTC', "
        '\'YYYY-MM-DD"T"HH24:MI:SS.US"Z"\')',
        sql,
        flags=re.IGNORECASE,
    )
    ignore_insert = bool(re.search(r"\bINSERT\s+OR\s+IGNORE\s+INTO\b", compiled, re.I))
    compiled = re.sub(
        r"\bINSERT\s+OR\s+IGNORE\s+INTO\b",
        "INSERT INTO",
        compiled,
        flags=re.IGNORECASE,
    )
    compiled = _replace_qmark_placeholders(compiled)
    if ignore_insert:
        stripped = compiled.rstrip()
        terminator = ";" if stripped.endswith(";") else ""
        if terminator:
            stripped = stripped[:-1].rstrip()
        compiled = f"{stripped} ON CONFLICT DO NOTHING{terminator}"
    return compiled


class PostgreSQLCursorAdapter:
    def __init__(self, cursor) -> None:
        self._cursor = cursor

    @property
    def rowcount(self) -> int:
        return int(self._cursor.rowcount)

    def _columns(self) -> tuple[str, ...]:
        if self._cursor.description is None:
            return ()
        columns = []
        for item in self._cursor.description:
            name = getattr(item, "name", None)
            columns.append(str(name if name is not None else item[0]))
        return tuple(columns)

    def fetchone(self) -> HybridRow | None:
        row = self._cursor.fetchone()
        return None if row is None else HybridRow(self._columns(), row)

    def fetchall(self) -> list[HybridRow]:
        columns = self._columns()
        return [HybridRow(columns, row) for row in self._cursor.fetchall()]

    def __iter__(self):
        columns = self._columns()
        for row in self._cursor:
            yield HybridRow(columns, row)


class PostgreSQLConnectionAdapter:
    def __init__(self, connection) -> None:
        self._connection = connection

    def execute(
        self, sql: str, parameters: Sequence[Any] = ()
    ) -> PostgreSQLCursorAdapter:
        try:
            cursor = self._connection.execute(
                compile_postgresql_sql(sql), tuple(parameters)
            )
        except Exception as error:
            try:
                import psycopg
            except ImportError:
                raise
            if isinstance(error, psycopg.IntegrityError):
                import sqlite3

                raise sqlite3.IntegrityError(str(error)) from error
            raise
        return PostgreSQLCursorAdapter(cursor)

    def executescript(self, script: str) -> None:
        for statement in (part.strip() for part in script.split(";")):
            if statement:
                self.execute(statement)

    def commit(self) -> None:
        self._connection.commit()

    def rollback(self) -> None:
        self._connection.rollback()

    def close(self) -> None:
        self._connection.close()


def _postgresql_table_sql(name: str, sql: str) -> str:
    translated = re.sub(
        r"INTEGER\s+PRIMARY\s+KEY\s+AUTOINCREMENT",
        "BIGINT GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY",
        sql,
        flags=re.IGNORECASE,
    )
    translated = re.sub(
        r"^CREATE\s+TABLE\s+",
        "CREATE TABLE IF NOT EXISTS ",
        translated,
        count=1,
        flags=re.IGNORECASE,
    )
    if (
        name == "brands"
        and "tenant_id" in translated
        and not re.search(r"REFERENCES\s+tenants\b", translated, re.I)
    ):
        closing = translated.rfind(")")
        translated = (
            translated[:closing]
            + ", FOREIGN KEY (tenant_id) REFERENCES tenants(tenant_id)"
            + translated[closing:]
        )
    return translated


def _postgresql_index_sql(sql: str) -> str:
    """Make canonical index creation safe across repeated initialisation."""

    return re.sub(
        r"^CREATE\s+(UNIQUE\s+)?INDEX\s+",
        lambda match: f"CREATE {match.group(1) or ''}INDEX IF NOT EXISTS ",
        sql,
        count=1,
        flags=re.IGNORECASE,
    )


def build_postgresql_schema() -> tuple[str, ...]:
    """Derive a deterministic PostgreSQL schema from the canonical SQLite schema."""

    with tempfile.TemporaryDirectory() as directory:
        database = SQLiteDatabase(Path(directory) / "schema.sqlite3")
        database.initialise()
        with database.connection() as connection:
            rows = connection.execute("""
                SELECT type, name, sql
                FROM sqlite_master
                WHERE type IN ('table', 'index')
                  AND sql IS NOT NULL
                  AND name NOT LIKE 'sqlite_%'
                ORDER BY CASE type WHEN 'table' THEN 0 ELSE 1 END, name
                """).fetchall()

    tables = {
        str(row["name"]): _postgresql_table_sql(str(row["name"]), str(row["sql"]))
        for row in rows
        if row["type"] == "table"
    }
    indexes = [
        _postgresql_index_sql(str(row["sql"])) for row in rows if row["type"] == "index"
    ]
    dependencies = {
        name: {
            dependency
            for dependency in re.findall(r"REFERENCES\s+([A-Za-z_][\w]*)", sql, re.I)
            if dependency in tables and dependency != name
        }
        for name, sql in tables.items()
    }
    ordered: list[str] = []
    pending = set(tables)
    while pending:
        ready = sorted(name for name in pending if dependencies[name].issubset(ordered))
        if not ready:
            raise RuntimeError(
                "PostgreSQL schema contains unresolved dependencies: "
                + ", ".join(sorted(pending))
            )
        ordered.extend(ready)
        pending.difference_update(ready)

    statements = [tables[name] for name in ordered]
    statements.extend(indexes)
    statements.extend(POSTGRESQL_IMMUTABILITY_STATEMENTS)
    return tuple(statements)


def build_postgresql_seed_rows() -> dict[str, tuple[tuple[Any, ...], ...]]:
    """Return canonical non-secret migration and default-tenant seed rows."""

    with tempfile.TemporaryDirectory() as directory:
        database = SQLiteDatabase(Path(directory) / "seed.sqlite3")
        database.initialise()
        with database.connection() as connection:
            migrations = connection.execute("""
                SELECT version, description, applied_at
                FROM schema_migrations ORDER BY version
                """).fetchall()
            tenants = connection.execute("""
                SELECT tenant_id, name, status, created_at, updated_at
                FROM tenants WHERE tenant_id = 'default'
                """).fetchall()
    return {
        "schema_migrations": tuple(tuple(row) for row in migrations),
        "tenants": tuple(tuple(row) for row in tenants),
    }


class PostgreSQLDatabase(SQLiteDatabase):
    """Run existing canonical repositories over PostgreSQL via psycopg."""

    def __init__(
        self,
        database_url: str,
        *,
        lifecycle_event_sink: DatabaseLifecycleEventSink | None = None,
        monotonic: MonotonicClock = monotonic_clock,
    ) -> None:
        selected = str(database_url).strip()
        if not selected.startswith(("postgresql://", "postgresql+psycopg://")):
            raise PostgreSQLConfigurationError(
                "MLAI_DATABASE_URL must be a PostgreSQL URL."
            )
        self.database_url = selected.replace(
            "postgresql+psycopg://", "postgresql://", 1
        )
        super().__init__(
            Path("postgresql-managed"),
            lifecycle_event_sink=lifecycle_event_sink,
            monotonic=monotonic,
        )
        parsed = urlsplit(self.database_url)
        safe_target = (
            f"{parsed.hostname or ''}:{parsed.port or 5432}/{parsed.path.lstrip('/')}"
        )
        self._backend_name = "postgresql"
        self._target_fingerprint = target_fingerprint(safe_target)

    def connect(self) -> PostgreSQLConnectionAdapter:
        try:
            import psycopg
        except ImportError as error:
            raise RuntimeError(
                "psycopg is required for PostgreSQL persistence."
            ) from error
        connection = psycopg.connect(self.database_url)
        return PostgreSQLConnectionAdapter(connection)

    @contextmanager
    def connection(self) -> Iterator[PostgreSQLConnectionAdapter]:
        connection = self.connect()
        try:
            yield connection
        except Exception as error:
            if _error_has_sqlstate(error, "42P01"):
                raise DatabaseSchemaNotReadyError(
                    "The database schema is not ready; run the explicit bootstrap."
                ) from error
            raise
        finally:
            connection.close()

    @contextmanager
    def transaction(self) -> Iterator[PostgreSQLConnectionAdapter]:
        connection = self.connect()
        try:
            yield connection
            connection.commit()
        except Exception as error:
            connection.rollback()
            if _error_has_sqlstate(error, "42P01"):
                raise DatabaseSchemaNotReadyError(
                    "The database schema is not ready; run the explicit bootstrap."
                ) from error
            raise
        finally:
            connection.close()

    @contextmanager
    def migration_transaction(self) -> Iterator[PostgreSQLConnectionAdapter]:
        """Hold the governed advisory lock through migration commit or rollback."""

        connection = self.connect()
        wait_started_at = self._monotonic()
        self._emit_lifecycle_event(
            "migration_lock_waiting", "migration_lock", wait_started_at=wait_started_at
        )
        try:
            connection.execute(
                "SELECT set_config('lock_timeout', ?, true)",
                (f"{POSTGRESQL_MIGRATION_LOCK_TIMEOUT_SECONDS}s",),
            )
            connection.execute(
                "SELECT pg_advisory_xact_lock(?)",
                (postgresql_migration_advisory_key(),),
            )
            self._emit_lifecycle_event(
                "migration_lock_acquired",
                "migration_lock",
                wait_started_at=wait_started_at,
            )
            connection.execute("SELECT set_config('lock_timeout', '0', true)")
            yield connection
            connection.commit()
        except Exception as error:
            connection.rollback()
            if _error_has_sqlstate(error, "55P03"):
                self._emit_lifecycle_event(
                    "migration_lock_timeout",
                    "migration_lock",
                    wait_started_at=wait_started_at,
                    failure_category="lock_timeout",
                )
                raise DatabaseMigrationLockTimeoutError(
                    "Timed out acquiring the PostgreSQL migration advisory lock."
                ) from error
            raise
        finally:
            connection.close()

    def _apply_schema(self, existing_connection=None) -> None:
        selected = (
            nullcontext(existing_connection)
            if existing_connection is not None
            else self.migration_transaction()
        )
        with selected as connection:
            for statement in build_postgresql_schema():
                connection.execute(statement)
            seeds = build_postgresql_seed_rows()
            for row in seeds["schema_migrations"]:
                connection.execute(
                    """
                    INSERT INTO schema_migrations (version, description, applied_at)
                    VALUES (?, ?, ?) ON CONFLICT (version) DO NOTHING
                    """,
                    row,
                )
            for row in seeds["tenants"]:
                connection.execute(
                    """
                    INSERT INTO tenants
                        (tenant_id, name, status, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?) ON CONFLICT (tenant_id) DO NOTHING
                    """,
                    row,
                )

    def _schema_is_ready(self, connection) -> bool:
        return observe_postgresql_schema(connection).ready

    def schema_readiness(self) -> SchemaReadinessReport:
        """Observe complete PostgreSQL schema readiness without applying DDL."""

        observed_version = None
        try:
            with self.connection() as connection:
                observed_version = self._observed_migration_version(connection)
                report = observe_postgresql_schema(connection)
        except Exception as error:
            report = unavailable_schema_report(
                "inspection", type(error).__name__.lower()
            )
        if not report.ready:
            category = (
                report.failure_categories[0] if report.failure_categories else "unknown"
            )
            self._emit_lifecycle_event(
                "readiness_failure",
                "schema_readiness",
                observed_version=observed_version,
                failure_category=category,
            )
        return report

    def table_names(self) -> list[str]:
        with self.connection() as connection:
            return self._table_names(connection)

    def _table_names(self, connection) -> list[str]:
        rows = connection.execute("""
                SELECT table_name AS name
                FROM information_schema.tables
                WHERE table_schema = 'public'
                ORDER BY table_name
                """).fetchall()
        return [str(row["name"]) for row in rows]

    def integrity_check(self) -> str:
        with self.connection() as connection:
            row = connection.execute("SELECT 1 AS healthy").fetchone()
        return "ok" if row is not None and int(row["healthy"]) == 1 else "failed"

    def checkpoint(self) -> None:
        return None
