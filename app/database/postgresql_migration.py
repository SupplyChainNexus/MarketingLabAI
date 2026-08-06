"""Transactional synthetic SQLite-to-PostgreSQL migration controls."""

from __future__ import annotations

import hashlib
import re
import sqlite3
from dataclasses import dataclass

from app.database.connection import SQLiteDatabase
from app.database.postgresql import PostgreSQLDatabase


@dataclass(slots=True, frozen=True)
class TableMigrationEvidence:
    table: str
    source_rows: int
    target_rows: int


@dataclass(slots=True, frozen=True)
class PostgreSQLMigrationEvidence:
    source_sha256: str
    tables: tuple[TableMigrationEvidence, ...]
    source_preserved: bool
    committed: bool
    real_data_activation_authorized: bool = False


def _identifier(value: str) -> str:
    if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", value):
        raise ValueError(f"Unsafe SQL identifier: {value}")
    return f'"{value}"'


def _ordered_tables(connection: sqlite3.Connection) -> list[str]:
    tables = [str(row[0]) for row in connection.execute("""
            SELECT name FROM sqlite_master
            WHERE type = 'table' AND name NOT LIKE 'sqlite_%'
            ORDER BY name
            """).fetchall()]
    dependencies = {
        table: {
            str(row[2])
            for row in connection.execute(
                f"PRAGMA foreign_key_list({_identifier(table)})"
            ).fetchall()
            if str(row[2]) in tables and str(row[2]) != table
        }
        for table in tables
    }
    if "brands" in dependencies and "tenants" in tables:
        dependencies["brands"].add("tenants")
    ordered: list[str] = []
    pending = set(tables)
    while pending:
        ready = sorted(
            table for table in pending if dependencies[table].issubset(ordered)
        )
        if not ready:
            raise RuntimeError(
                "SQLite migration contains unresolved dependencies: "
                + ", ".join(sorted(pending))
            )
        ordered.extend(ready)
        pending.difference_update(ready)
    return ordered


class SQLiteToPostgreSQLMigrator:
    """Copy an immutable synthetic SQLite snapshot in one target transaction."""

    def __init__(self, source: SQLiteDatabase, target: PostgreSQLDatabase) -> None:
        if not isinstance(source, SQLiteDatabase) or isinstance(
            source, PostgreSQLDatabase
        ):
            raise TypeError("source must be a SQLiteDatabase.")
        if not isinstance(target, PostgreSQLDatabase):
            raise TypeError("target must be a PostgreSQLDatabase.")
        self.source = source
        self.target = target

    def migrate_synthetic_snapshot(self) -> PostgreSQLMigrationEvidence:
        self.source.initialise()
        self.target.initialise()
        source_path = self.source.database_path
        before_hash = hashlib.sha256(source_path.read_bytes()).hexdigest()
        evidence: list[TableMigrationEvidence] = []

        with self.source.connection() as source_connection:
            tables = _ordered_tables(source_connection)
            with self.target.transaction() as target_connection:
                for table in tables:
                    quoted_table = _identifier(table)
                    columns = [
                        str(row[1])
                        for row in source_connection.execute(
                            f"PRAGMA table_info({quoted_table})"
                        ).fetchall()
                    ]
                    quoted_columns = ", ".join(_identifier(item) for item in columns)
                    source_rows = source_connection.execute(
                        f"SELECT {quoted_columns} FROM {quoted_table}"
                    ).fetchall()
                    placeholders = ", ".join("?" for _ in columns)
                    for row in source_rows:
                        target_connection.execute(
                            f"INSERT INTO {quoted_table} ({quoted_columns}) "
                            f"VALUES ({placeholders}) ON CONFLICT DO NOTHING",
                            tuple(row),
                        )
                    target_row = target_connection.execute(
                        f"SELECT COUNT(*) AS count FROM {quoted_table}"
                    ).fetchone()
                    target_count = 0 if target_row is None else int(target_row["count"])
                    if target_count != len(source_rows):
                        raise RuntimeError(
                            f"Row-count mismatch for {table}: "
                            f"source={len(source_rows)} target={target_count}"
                        )
                    evidence.append(
                        TableMigrationEvidence(table, len(source_rows), target_count)
                    )

        after_hash = hashlib.sha256(source_path.read_bytes()).hexdigest()
        if before_hash != after_hash:
            raise RuntimeError("Source SQLite snapshot changed during migration.")
        return PostgreSQLMigrationEvidence(
            source_sha256=before_hash,
            tables=tuple(evidence),
            source_preserved=True,
            committed=True,
        )
