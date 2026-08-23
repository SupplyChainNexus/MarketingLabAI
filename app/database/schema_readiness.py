"""Deterministic, observational database-schema readiness contracts."""

from __future__ import annotations

from copy import deepcopy
import hashlib
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Sequence


SCHEMA_MANIFEST_ID = "earthonox.marketinglabai.schema-manifest.v1"
_MANIFEST_PATH = Path(__file__).with_name("schema_manifest.json")


@dataclass(frozen=True, slots=True)
class SchemaReadinessFinding:
    """One privacy-safe category of canonical schema drift."""

    category: str
    object_name: str
    expected: str
    observed: str


@dataclass(frozen=True, slots=True)
class SchemaReadinessReport:
    """Structured result of a side-effect-free schema observation."""

    ready: bool
    manifest_id: str
    manifest_sha256: str
    findings: tuple[SchemaReadinessFinding, ...]

    @property
    def failure_categories(self) -> tuple[str, ...]:
        return tuple(sorted({finding.category for finding in self.findings}))


def _canonical_json(value: Any) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")


def load_schema_manifest() -> dict[str, Any]:
    """Load and authenticate the committed canonical schema manifest."""

    document = json.loads(_MANIFEST_PATH.read_text(encoding="utf-8"))
    if document.get("manifest_id") != SCHEMA_MANIFEST_ID:
        raise ValueError("The canonical schema manifest identity is invalid.")
    expected_digest = str(document.get("schema_sha256", ""))
    payload = {key: value for key, value in document.items() if key != "schema_sha256"}
    observed_digest = hashlib.sha256(_canonical_json(payload)).hexdigest()
    if observed_digest != expected_digest:
        raise ValueError("The canonical schema manifest checksum is invalid.")
    return document


def _normalize_sql(value: Any) -> str:
    return " ".join(str(value or "").split()).lower()


def _extract_checks(sql: Any) -> list[str]:
    """Extract balanced CHECK expressions from the repository's bounded DDL."""

    source = str(sql or "")
    expressions: list[str] = []
    for match in re.finditer(r"\bCHECK\s*\(", source, re.IGNORECASE):
        start = match.end()
        depth = 1
        quoted = False
        index = start
        while index < len(source) and depth:
            character = source[index]
            if character == "'":
                if quoted and index + 1 < len(source) and source[index + 1] == "'":
                    index += 2
                    continue
                quoted = not quoted
            elif not quoted:
                if character == "(":
                    depth += 1
                elif character == ")":
                    depth -= 1
            index += 1
        if depth:
            expressions.append("<invalid-unbalanced-check>")
        else:
            expressions.append(_normalize_sql(source[start : index - 1]))
    return sorted(expressions)


def _sqlite_snapshot(connection) -> dict[str, Any]:
    table_rows = connection.execute("""
        SELECT name, sql
        FROM sqlite_master
        WHERE type = 'table' AND name NOT LIKE 'sqlite_%'
        ORDER BY name
        """).fetchall()
    tables = [str(row["name"]) for row in table_rows]
    table_sql = {str(row["name"]): row["sql"] for row in table_rows}
    snapshot: dict[str, Any] = {
        "tables": tables,
        "columns": {},
        "column_types": {},
        "nullability": {},
        "column_defaults": {},
        "indexes": {},
        "unique_constraints": {},
        "foreign_keys": {},
        "check_constraints": {},
        "triggers": [],
        "migrations": [],
    }
    for table in tables:
        columns = list(connection.execute(f'PRAGMA table_xinfo("{table}")'))
        snapshot["columns"][table] = [str(row["name"]) for row in columns]
        snapshot["column_types"][table] = [
            [str(row["name"]), str(row["type"]).upper()] for row in columns
        ]
        snapshot["nullability"][table] = [
            [
                str(row["name"]),
                not bool(row["notnull"]) and not bool(row["pk"]),
            ]
            for row in columns
        ]
        snapshot["column_defaults"][table] = [
            [str(row["name"]), row["dflt_value"]] for row in columns
        ]
        primary_key = [
            str(row["name"])
            for row in sorted(columns, key=lambda item: int(item["pk"]) or 999)
            if int(row["pk"])
        ]
        unique_constraints = [primary_key] if primary_key else []
        indexes: list[list[Any]] = []
        for index in connection.execute(f'PRAGMA index_list("{table}")'):
            name = str(index["name"])
            index_columns = [
                str(row["name"])
                for row in connection.execute(f'PRAGMA index_info("{name}")')
            ]
            if str(index["origin"]) == "u":
                unique_constraints.append(index_columns)
            elif str(index["origin"]) == "c":
                row = connection.execute(
                    "SELECT sql FROM sqlite_master WHERE type = 'index' AND name = ?",
                    (name,),
                ).fetchone()
                sql = "" if row is None else str(row["sql"] or "")
                predicate_match = re.search(r"\bWHERE\b(.+)$", sql, re.I | re.S)
                predicate = (
                    "" if predicate_match is None else _normalize_sql(predicate_match[1])
                )
                indexes.append(
                    [
                        name,
                        bool(index["unique"]),
                        bool(index["partial"]),
                        index_columns,
                        predicate,
                    ]
                )
        snapshot["indexes"][table] = sorted(indexes)
        snapshot["unique_constraints"][table] = sorted(unique_constraints)
        foreign_key_groups: dict[int, list[Any]] = {}
        for foreign_key in connection.execute(f'PRAGMA foreign_key_list("{table}")'):
            group = foreign_key_groups.setdefault(
                int(foreign_key["id"]),
                [
                    [],
                    str(foreign_key["table"]),
                    [],
                    str(foreign_key["on_update"]).upper(),
                    str(foreign_key["on_delete"]).upper(),
                ],
            )
            group[0].append(str(foreign_key["from"]))
            group[2].append(str(foreign_key["to"]))
        snapshot["foreign_keys"][table] = sorted(foreign_key_groups.values())
        snapshot["check_constraints"][table] = _extract_checks(table_sql[table])
    snapshot["triggers"] = [
        [str(row["name"]), str(row["tbl_name"]), _normalize_sql(row["sql"])]
        for row in connection.execute("""
            SELECT name, tbl_name, sql
            FROM sqlite_master WHERE type = 'trigger' ORDER BY name
            """)
    ]
    if "schema_migrations" in tables:
        snapshot["migrations"] = [
            [int(row["version"]), str(row["description"])]
            for row in connection.execute("""
                SELECT version, description
                FROM schema_migrations ORDER BY version
                """)
        ]
    return snapshot


_CATEGORY_KEYS = (
    "tables",
    "columns",
    "column_types",
    "nullability",
    "column_defaults",
    "indexes",
    "unique_constraints",
    "foreign_keys",
    "check_constraints",
    "triggers",
    "migrations",
)


def compare_schema_snapshot(
    observed: Mapping[str, Any],
    *,
    provider: str,
) -> SchemaReadinessReport:
    """Compare an observed provider snapshot with the authenticated manifest."""

    manifest = load_schema_manifest()
    expected = deepcopy(manifest["schema"])
    for category, value in manifest.get(f"{provider}_overrides", {}).items():
        if isinstance(value, dict) and isinstance(expected.get(category), dict):
            expected[category].update(value)
        else:
            expected[category] = value
    findings: list[SchemaReadinessFinding] = []

    def add_finding(category: str, object_name: str, expected_value, observed_value):
        findings.append(
            SchemaReadinessFinding(
                category=category,
                object_name=object_name,
                expected=hashlib.sha256(_canonical_json(expected_value)).hexdigest(),
                observed=hashlib.sha256(_canonical_json(observed_value)).hexdigest(),
            )
        )

    for category in _CATEGORY_KEYS:
        expected_value = expected[category]
        observed_value = observed.get(category)
        if observed_value == expected_value:
            continue
        if isinstance(expected_value, dict) and isinstance(observed_value, Mapping):
            for object_name in sorted(set(expected_value) | set(observed_value)):
                if expected_value.get(object_name) != observed_value.get(object_name):
                    add_finding(
                        category,
                        str(object_name),
                        expected_value.get(object_name),
                        observed_value.get(object_name),
                    )
            continue
        if category == "tables" and isinstance(observed_value, list):
            for object_name in sorted(set(expected_value) ^ set(observed_value)):
                add_finding(
                    category,
                    str(object_name),
                    object_name in expected_value,
                    object_name in observed_value,
                )
            continue
        if category in {"migrations", "triggers"} and isinstance(
            observed_value, list
        ):
            key_index = 0
            expected_items = {str(item[key_index]): item for item in expected_value}
            observed_items = {str(item[key_index]): item for item in observed_value}
            for object_name in sorted(set(expected_items) | set(observed_items)):
                if expected_items.get(object_name) != observed_items.get(object_name):
                    add_finding(
                        category,
                        object_name,
                        expected_items.get(object_name),
                        observed_items.get(object_name),
                    )
            continue
        add_finding(category, "canonical_schema", expected_value, observed_value)
    return SchemaReadinessReport(
        ready=not findings,
        manifest_id=str(manifest["manifest_id"]),
        manifest_sha256=str(manifest["schema_sha256"]),
        findings=tuple(findings),
    )


def observe_sqlite_schema(connection) -> SchemaReadinessReport:
    """Inspect SQLite schema metadata without applying or repairing DDL."""

    return compare_schema_snapshot(_sqlite_snapshot(connection), provider="sqlite")


def _postgresql_type(value: Any) -> str:
    selected = str(value or "").lower()
    return {
        "int4": "INTEGER",
        "integer": "INTEGER",
        "int8": "INTEGER",
        "bigint": "INTEGER",
        "float4": "REAL",
        "real": "REAL",
        "text": "TEXT",
        "varchar": "TEXT",
    }.get(selected, selected.upper())


def _postgresql_default(value: Any) -> Any:
    if value is None:
        return None
    selected = re.sub(r"::(?:text|character varying)\b", "", str(value))
    selected = selected.strip()
    while selected.startswith("(") and selected.endswith(")"):
        selected = selected[1:-1].strip()
    return selected


def _group_constraint_columns(rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    grouped: dict[tuple[str, str, str], list[tuple[int, str]]] = {}
    for row in rows:
        key = (
            str(row["table_name"]),
            str(row["constraint_name"]),
            str(row["constraint_type"]),
        )
        grouped.setdefault(key, []).append(
            (int(row["ordinal_position"]), str(row["column_name"]))
        )
    output: dict[str, list[list[str]]] = {}
    for (table, _name, _kind), columns in grouped.items():
        output.setdefault(table, []).append(
            [column for _position, column in sorted(columns)]
        )
    return {table: sorted(values) for table, values in output.items()}


def _postgresql_snapshot(connection) -> dict[str, Any]:
    table_rows = connection.execute("""
        SELECT table_name AS name
        FROM information_schema.tables
        WHERE table_schema = current_schema() AND table_type = 'BASE TABLE'
        ORDER BY table_name
        """).fetchall()
    tables = [str(row["name"]) for row in table_rows]
    snapshot: dict[str, Any] = {
        "tables": tables,
        "columns": {table: [] for table in tables},
        "column_types": {table: [] for table in tables},
        "nullability": {table: [] for table in tables},
        "column_defaults": {table: [] for table in tables},
        "indexes": {table: [] for table in tables},
        "unique_constraints": {table: [] for table in tables},
        "foreign_keys": {table: [] for table in tables},
        "check_constraints": {table: [] for table in tables},
        "triggers": [],
        "migrations": [],
    }
    constraint_rows = connection.execute("""
        SELECT tc.table_name, tc.constraint_name, tc.constraint_type,
               kcu.column_name, kcu.ordinal_position
        FROM information_schema.table_constraints AS tc
        JOIN information_schema.key_column_usage AS kcu
          ON tc.constraint_schema = kcu.constraint_schema
         AND tc.constraint_name = kcu.constraint_name
        WHERE tc.constraint_schema = current_schema()
          AND tc.constraint_type IN ('PRIMARY KEY', 'UNIQUE')
        ORDER BY tc.table_name, tc.constraint_name, kcu.ordinal_position
        """).fetchall()
    grouped_unique = _group_constraint_columns(constraint_rows)
    for table in tables:
        snapshot["unique_constraints"][table] = grouped_unique.get(table, [])
    for row in connection.execute("""
        SELECT table_name, column_name, udt_name, is_nullable,
               column_default, ordinal_position
        FROM information_schema.columns
        WHERE table_schema = current_schema()
        ORDER BY table_name, ordinal_position
        """):
        table = str(row["table_name"])
        name = str(row["column_name"])
        snapshot["columns"].setdefault(table, []).append(name)
        snapshot["column_types"].setdefault(table, []).append(
            [name, _postgresql_type(row["udt_name"])]
        )
        snapshot["nullability"].setdefault(table, []).append(
            [name, str(row["is_nullable"]).upper() == "YES"]
        )
        snapshot["column_defaults"].setdefault(table, []).append(
            [name, _postgresql_default(row["column_default"])]
        )
    constraint_names = {
        str(row["constraint_name"])
        for row in constraint_rows
    }
    for row in connection.execute("""
        SELECT tablename AS table_name, indexname AS index_name,
               indexdef AS index_definition
        FROM pg_indexes
        WHERE schemaname = current_schema()
        ORDER BY tablename, indexname
        """):
        name = str(row["index_name"])
        if name in constraint_names:
            continue
        definition = str(row["index_definition"])
        columns_match = re.search(r"\(([^()]*)\)", definition)
        columns = [] if columns_match is None else [
            item.strip().strip('"') for item in columns_match.group(1).split(",")
        ]
        predicate_match = re.search(r"\bWHERE\b(.+)$", definition, re.I | re.S)
        predicate = "" if predicate_match is None else _normalize_sql(
            predicate_match[1].strip().strip("()")
        )
        table = str(row["table_name"])
        snapshot["indexes"].setdefault(table, []).append(
            [
                name,
                bool(re.search(r"\bUNIQUE\s+INDEX\b", definition, re.I)),
                predicate_match is not None,
                columns,
                predicate,
            ]
        )
    for table in snapshot["indexes"]:
        snapshot["indexes"][table].sort()
    foreign_key_rows = connection.execute("""
        SELECT tc.table_name, tc.constraint_name, kcu.ordinal_position,
               kcu.column_name, ccu.table_name AS foreign_table_name,
               ccu.column_name AS foreign_column_name,
               rc.update_rule, rc.delete_rule
        FROM information_schema.table_constraints AS tc
        JOIN information_schema.key_column_usage AS kcu
          ON tc.constraint_schema = kcu.constraint_schema
         AND tc.constraint_name = kcu.constraint_name
        JOIN information_schema.referential_constraints AS rc
          ON tc.constraint_schema = rc.constraint_schema
         AND tc.constraint_name = rc.constraint_name
        JOIN information_schema.key_column_usage AS ccu
          ON rc.unique_constraint_schema = ccu.constraint_schema
         AND rc.unique_constraint_name = ccu.constraint_name
         AND kcu.position_in_unique_constraint = ccu.ordinal_position
        WHERE tc.constraint_schema = current_schema()
          AND tc.constraint_type = 'FOREIGN KEY'
        ORDER BY tc.table_name, tc.constraint_name, kcu.ordinal_position
        """).fetchall()
    foreign_groups: dict[tuple[str, str], list[Any]] = {}
    for row in foreign_key_rows:
        key = (str(row["table_name"]), str(row["constraint_name"]))
        group = foreign_groups.setdefault(
            key,
            [
                [],
                str(row["foreign_table_name"]),
                [],
                str(row["update_rule"]).upper(),
                str(row["delete_rule"]).upper(),
            ],
        )
        group[0].append(str(row["column_name"]))
        group[2].append(str(row["foreign_column_name"]))
    for (table, _name), value in foreign_groups.items():
        snapshot["foreign_keys"].setdefault(table, []).append(value)
    for table in snapshot["foreign_keys"]:
        snapshot["foreign_keys"][table].sort()
    for row in connection.execute("""
        SELECT tc.table_name, cc.check_clause
        FROM information_schema.table_constraints AS tc
        JOIN information_schema.check_constraints AS cc
          ON tc.constraint_schema = cc.constraint_schema
         AND tc.constraint_name = cc.constraint_name
        WHERE tc.constraint_schema = current_schema()
          AND tc.constraint_type = 'CHECK'
        ORDER BY tc.table_name, tc.constraint_name
        """):
        snapshot["check_constraints"].setdefault(
            str(row["table_name"]), []
        ).append(_normalize_sql(row["check_clause"]))
    for row in connection.execute("""
        SELECT event_object_table AS table_name, trigger_name,
               action_timing, event_manipulation, action_statement
        FROM information_schema.triggers
        WHERE trigger_schema = current_schema()
        ORDER BY event_object_table, trigger_name, event_manipulation
        """):
        snapshot["triggers"].append(
            [
                str(row["trigger_name"]),
                str(row["table_name"]),
                _normalize_sql(
                    f"{row['action_timing']} {row['event_manipulation']} "
                    f"{row['action_statement']}"
                ),
            ]
        )
    if "schema_migrations" in tables:
        snapshot["migrations"] = [
            [int(row["version"]), str(row["description"])]
            for row in connection.execute("""
                SELECT version, description
                FROM schema_migrations ORDER BY version
                """)
        ]
    return snapshot


def observe_postgresql_schema(connection) -> SchemaReadinessReport:
    """Inspect PostgreSQL catalogs without applying or repairing DDL."""

    return compare_schema_snapshot(
        _postgresql_snapshot(connection), provider="postgresql"
    )


def unavailable_schema_report(category: str, observed: str) -> SchemaReadinessReport:
    """Return a structured fail-closed report when inspection cannot begin."""

    manifest = load_schema_manifest()
    return SchemaReadinessReport(
        ready=False,
        manifest_id=str(manifest["manifest_id"]),
        manifest_sha256=str(manifest["schema_sha256"]),
        findings=(
            SchemaReadinessFinding(
                category=category,
                object_name="canonical_schema",
                expected="available",
                observed=observed,
            ),
        ),
    )


def rows_as_dicts(rows: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    """Materialize adapter rows for provider-specific observers."""

    return [{str(key): row[key] for key in row} for row in rows]
