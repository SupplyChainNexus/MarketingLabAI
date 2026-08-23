"""Comprehensive observational schema-readiness tests for Increment B2."""

from __future__ import annotations

import tempfile
import unittest
from copy import deepcopy
from pathlib import Path

from app.database.connection import SQLiteDatabase
from app.database.schema_readiness import (
    SCHEMA_MANIFEST_ID,
    _postgresql_snapshot,
    compare_schema_snapshot,
    load_schema_manifest,
    observe_postgresql_schema,
)


class _Rows(list):
    def fetchall(self):
        return self


class _PostgreSQLCatalog:
    def __init__(self, *, changed_type: bool = False) -> None:
        manifest = load_schema_manifest()
        self.expected = deepcopy(manifest["schema"])
        for category, value in manifest["postgresql_overrides"].items():
            if isinstance(value, dict):
                self.expected[category].update(value)
            else:
                self.expected[category] = value
        self.changed_type = changed_type
        self.statements: list[str] = []

    def execute(self, sql: str):
        self.statements.append(sql)
        normalized = " ".join(sql.split()).lower()
        if "from information_schema.tables" in normalized:
            return _Rows({"name": table} for table in self.expected["tables"])
        if (
            "from information_schema.table_constraints as tc" in normalized
            and "primary key" in normalized
            and "unique" in normalized
        ):
            rows = []
            for table, constraints in self.expected["unique_constraints"].items():
                for constraint_number, columns in enumerate(constraints):
                    for position, column in enumerate(columns, start=1):
                        rows.append(
                            {
                                "table_name": table,
                                "constraint_name": f"{table}_constraint_{constraint_number}",
                                "constraint_type": "UNIQUE",
                                "column_name": column,
                                "ordinal_position": position,
                            }
                        )
            return _Rows(rows)
        if "from information_schema.columns" in normalized:
            rows = []
            for table in self.expected["tables"]:
                types = dict(self.expected["column_types"][table])
                nullable = dict(self.expected["nullability"][table])
                defaults = dict(self.expected["column_defaults"][table])
                for position, column in enumerate(
                    self.expected["columns"][table], start=1
                ):
                    column_type = types[column]
                    if self.changed_type and table == "tenants" and column == "name":
                        column_type = "INTEGER"
                    rows.append(
                        {
                            "table_name": table,
                            "column_name": column,
                            "udt_name": column_type,
                            "is_nullable": "YES" if nullable[column] else "NO",
                            "column_default": defaults[column],
                            "ordinal_position": position,
                        }
                    )
            return _Rows(rows)
        if "from pg_indexes" in normalized:
            rows = []
            for table, indexes in self.expected["indexes"].items():
                for name, unique, _partial, columns, predicate in indexes:
                    definition = (
                        f"CREATE {'UNIQUE ' if unique else ''}INDEX {name} "
                        f"ON public.{table} ({', '.join(columns)})"
                    )
                    if predicate:
                        definition += f" WHERE ({predicate})"
                    rows.append(
                        {
                            "table_name": table,
                            "index_name": name,
                            "index_definition": definition,
                        }
                    )
            return _Rows(rows)
        if "foreign key" in normalized:
            rows = []
            for table, constraints in self.expected["foreign_keys"].items():
                for number, constraint in enumerate(constraints):
                    local, foreign_table, remote, update, delete = constraint
                    for position, (column, foreign_column) in enumerate(
                        zip(local, remote, strict=True), start=1
                    ):
                        rows.append(
                            {
                                "table_name": table,
                                "constraint_name": f"{table}_fk_{number}",
                                "ordinal_position": position,
                                "column_name": column,
                                "foreign_table_name": foreign_table,
                                "foreign_column_name": foreign_column,
                                "update_rule": update,
                                "delete_rule": delete,
                            }
                        )
            return _Rows(rows)
        if "check_constraints" in normalized:
            return _Rows()
        if "information_schema.triggers" in normalized:
            return _Rows()
        if "from schema_migrations" in normalized:
            return _Rows(
                {"version": version, "description": description}
                for version, description in self.expected["migrations"]
            )
        raise AssertionError(f"Unexpected catalog query: {normalized}")


class SchemaReadinessTests(unittest.TestCase):
    def test_missing_sqlite_file_and_parent_remain_absent(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            parent = Path(directory) / "not-created"
            database_path = parent / "missing.sqlite3"
            database = SQLiteDatabase(database_path)

            report = database.schema_readiness()

            self.assertFalse(report.ready)
            self.assertEqual(report.failure_categories, ("database_file",))
            self.assertFalse(database_path.exists())
            self.assertFalse(parent.exists())

    def test_canonical_sqlite_schema_matches_authenticated_manifest(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "ready.sqlite3"
            database = SQLiteDatabase(path)
            database.initialise()
            before = path.read_bytes()

            first = database.schema_readiness()
            second = database.schema_readiness()
            tables = database.table_names()
            integrity = database.integrity_check()

            self.assertTrue(first.ready)
            self.assertEqual(first, second)
            self.assertEqual(first.manifest_id, SCHEMA_MANIFEST_ID)
            self.assertIn("schema_migrations", tables)
            self.assertEqual(integrity, "ok")
            self.assertEqual(path.read_bytes(), before)

    def test_every_structural_category_fails_closed_on_drift(self) -> None:
        expected = load_schema_manifest()["schema"]

        def replace_first(mapping, table, value):
            mapping[table][0] = value

        changes = {
            "tables": lambda value: value["tables"].append("unexpected"),
            "columns": lambda value: value["columns"]["tenants"].append("extra"),
            "column_types": lambda value: replace_first(
                value["column_types"], "tenants", ["tenant_id", "INTEGER"]
            ),
            "nullability": lambda value: replace_first(
                value["nullability"], "tenants", ["tenant_id", True]
            ),
            "column_defaults": lambda value: replace_first(
                value["column_defaults"], "tenants", ["tenant_id", "'unsafe'"]
            ),
            "indexes": lambda value: value["indexes"]["brands"].clear(),
            "unique_constraints": lambda value: value["unique_constraints"][
                "tenants"
            ].clear(),
            "foreign_keys": lambda value: value["foreign_keys"][
                "campaign_plans"
            ].clear(),
            "check_constraints": lambda value: value["check_constraints"][
                "tenants"
            ].append("status <> ''"),
            "triggers": lambda value: value["triggers"].clear(),
            "migrations": lambda value: value["migrations"].pop(),
        }
        for category, change in changes.items():
            with self.subTest(category=category):
                observed = deepcopy(expected)
                change(observed)
                report = compare_schema_snapshot(observed, provider="sqlite")
                self.assertFalse(report.ready)
                self.assertIn(category, report.failure_categories)

    def test_sqlite_detects_real_index_trigger_and_migration_drift(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            database = SQLiteDatabase(Path(directory) / "drift.sqlite3")
            database.initialise()
            with database.transaction() as connection:
                connection.execute("DROP INDEX idx_brands_name")
                connection.execute("DROP TRIGGER validate_brand_tenant_insert")
                connection.execute(
                    "UPDATE schema_migrations SET description = ? WHERE version = 18",
                    ("changed",),
                )

            report = database.schema_readiness()

            self.assertFalse(report.ready)
            self.assertEqual(
                set(report.failure_categories),
                {"indexes", "migrations", "triggers"},
            )
            self.assertEqual(
                {
                    (finding.category, finding.object_name)
                    for finding in report.findings
                },
                {
                    ("indexes", "brands"),
                    ("migrations", "18"),
                    ("triggers", "validate_brand_tenant_insert"),
                },
            )

    def test_postgresql_catalog_inspection_matches_equivalent_manifest(self) -> None:
        catalog = _PostgreSQLCatalog()

        report = observe_postgresql_schema(catalog)

        self.assertTrue(report.ready, report.findings)
        self.assertTrue(catalog.statements)
        self.assertTrue(
            all(
                statement.lstrip().upper().startswith("SELECT")
                for statement in catalog.statements
            )
        )

    def test_postgresql_type_drift_has_structured_category(self) -> None:
        report = observe_postgresql_schema(_PostgreSQLCatalog(changed_type=True))

        self.assertFalse(report.ready)
        self.assertIn("column_types", report.failure_categories)

    def test_postgresql_snapshot_contains_every_governed_category(self) -> None:
        snapshot = _postgresql_snapshot(_PostgreSQLCatalog())

        self.assertEqual(
            set(snapshot),
            {
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
            },
        )


if __name__ == "__main__":
    unittest.main()
