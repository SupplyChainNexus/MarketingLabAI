"""Contract tests for PostgreSQL compatibility without claiming a live rehearsal."""

import unittest
from contextlib import contextmanager
from pathlib import Path
from tempfile import TemporaryDirectory

from app.database.connection import SQLiteDatabase
from app.database.factory import create_database
from app.database.postgresql import (
    HybridRow,
    PostgreSQLConfigurationError,
    PostgreSQLDatabase,
    build_postgresql_schema,
    build_postgresql_seed_rows,
    compile_postgresql_sql,
)
from app.database.postgresql_migration import SQLiteToPostgreSQLMigrator
from app.identity.repository import MEMBERSHIP_SESSION_INVALIDATION_SQL
from app.operations.configuration import PilotConfiguration
from app.operations.sessions import SESSION_RENEW_CAS_SQL


class PostgreSQLCompatibilityTests(unittest.TestCase):
    def test_qmark_translation_preserves_literal_question_marks(self):
        compiled = compile_postgresql_sql(
            "SELECT * FROM brands WHERE brand_id = ? AND name = 'Why?'"
        )

        self.assertIn("brand_id = %s", compiled)
        self.assertIn("name = 'Why?'", compiled)

    def test_sqlite_timestamps_and_ignore_inserts_are_portable(self):
        compiled = compile_postgresql_sql("""
            INSERT OR IGNORE INTO schema_migrations
                (version, description, applied_at)
            VALUES (?, ?, strftime('%Y-%m-%dT%H:%M:%fZ', 'now'));
            """)

        self.assertNotIn("INSERT OR IGNORE", compiled)
        self.assertNotIn("strftime", compiled)
        self.assertIn("ON CONFLICT DO NOTHING;", compiled)
        self.assertEqual(compiled.count("%s"), 2)

    def test_session_lifecycle_sql_compiles_for_postgresql(self):
        renewal = compile_postgresql_sql(SESSION_RENEW_CAS_SQL)
        invalidation = compile_postgresql_sql(MEMBERSHIP_SESSION_INVALIDATION_SQL)

        self.assertEqual(renewal.count("%s"), 6)
        self.assertIn("revoked_at IS NULL", renewal)
        self.assertIn("expires_at > %s", renewal)
        self.assertIn("created_at > %s", renewal)
        self.assertEqual(invalidation.count("%s"), 3)
        self.assertNotIn("strftime", invalidation)
        self.assertIn("clock_timestamp()", invalidation)

    def test_hybrid_rows_support_sqlite_key_and_index_access(self):
        row = HybridRow(("tenant_id", "status"), ("velani", "active"))

        self.assertEqual(row[0], "velani")
        self.assertEqual(row["status"], "active")
        self.assertEqual(dict(row), {"tenant_id": "velani", "status": "active"})

    def test_generated_schema_is_ordered_and_contains_every_table(self):
        statements = build_postgresql_schema()
        combined = "\n".join(statements)

        self.assertNotIn("AUTOINCREMENT", combined)
        self.assertNotIn("PRAGMA", combined)
        self.assertIn("CREATE TABLE IF NOT EXISTS tenants", combined)
        self.assertIn("CREATE TABLE IF NOT EXISTS pilot_activation_events", combined)
        self.assertLess(
            combined.index("CREATE TABLE IF NOT EXISTS tenants"),
            combined.index("CREATE TABLE IF NOT EXISTS brands"),
        )
        self.assertEqual(
            sum("CREATE TABLE IF NOT EXISTS" in item for item in statements), 21
        )
        index_statements = [
            item for item in statements if item.lstrip().startswith("CREATE INDEX")
        ]
        self.assertTrue(index_statements)
        self.assertTrue(
            all("CREATE INDEX IF NOT EXISTS" in item for item in index_statements)
        )

    def test_seed_rows_include_migrations_and_only_default_tenant(self):
        seeds = build_postgresql_seed_rows()

        self.assertEqual(
            {int(row[0]) for row in seeds["schema_migrations"]}, set(range(1, 18))
        )
        self.assertEqual(len(seeds["tenants"]), 1)
        self.assertEqual(seeds["tenants"][0][0], "default")

    def test_factory_preserves_sqlite_and_selects_postgresql(self):
        sqlite_database = create_database(
            backend="sqlite", database_path=Path("database/test.db"), database_url=""
        )
        postgres_database = create_database(
            backend="postgresql",
            database_path=Path("unused"),
            database_url="postgresql://user:password@example.test/database",
        )

        self.assertEqual(sqlite_database.database_path, Path("database/test.db"))
        self.assertIsInstance(postgres_database, PostgreSQLDatabase)

    def test_postgresql_rejects_non_postgresql_urls(self):
        with self.assertRaises(PostgreSQLConfigurationError):
            PostgreSQLDatabase("sqlite:///database.db")

    def test_pilot_configuration_requires_url_for_postgresql(self):
        values = self._pilot_values()
        values["MLAI_PERSISTENCE_BACKEND"] = "postgresql"

        with self.assertRaises(ValueError):
            PilotConfiguration.from_environment(values)

        values["MLAI_DATABASE_URL"] = "postgresql://user:test@example.test/db"
        config = PilotConfiguration.from_environment(values)
        self.assertEqual(config.persistence_backend, "postgresql")

    def test_synthetic_migration_preserves_source_and_all_row_counts(self):
        with TemporaryDirectory() as directory:
            source = SQLiteDatabase(Path(directory) / "source.sqlite3")
            target_store = SQLiteDatabase(Path(directory) / "target.sqlite3")
            target = _SyntheticPostgreSQLTarget(target_store)
            source.initialise()
            with source.transaction() as connection:
                connection.execute(
                    "INSERT INTO brands (brand_id, name, payload_json, created_at, "
                    "updated_at, tenant_id) VALUES (?, ?, ?, ?, ?, ?)",
                    ("brand-1", "Synthetic", "{}", "now", "now", "default"),
                )

            evidence = SQLiteToPostgreSQLMigrator(
                source, target
            ).migrate_synthetic_snapshot()

            self.assertTrue(evidence.source_preserved)
            self.assertTrue(evidence.committed)
            self.assertFalse(evidence.real_data_activation_authorized)
            self.assertTrue(
                all(item.source_rows == item.target_rows for item in evidence.tables)
            )
            with target_store.connection() as connection:
                self.assertEqual(
                    connection.execute("SELECT COUNT(*) FROM brands").fetchone()[0], 1
                )

    @staticmethod
    def _pilot_values() -> dict[str, str]:
        return {
            "MLAI_ENVIRONMENT": "synthetic-pilot",
            "MLAI_DATABASE_PATH": "database/test.db",
            "MLAI_BACKUP_DIRECTORY": "backups",
            "MLAI_PUBLIC_ORIGIN": "http://127.0.0.1:8080",
            "MLAI_TRUST_PROXY_TLS": "false",
            "MLAI_SESSION_SECRET": "a" * 32,
            "MLAI_IDENTITY_PROVIDER": "synthetic",
            "MLAI_IDENTITY_ADAPTER_FACTORY": "tests.fake:create",
            "MLAI_PROVIDER_REGISTRY_FACTORY": "tests.fake:create",
            "MLAI_FOUNDER_INVITATION_HASHES_JSON": "{}",
            "MLAI_ALLOW_REAL_CUSTOMER_DATA": "false",
        }


if __name__ == "__main__":
    unittest.main()


class _SyntheticPostgreSQLTarget(PostgreSQLDatabase):
    """Exercise migration control flow without claiming a live PostgreSQL run."""

    def __init__(self, store: SQLiteDatabase) -> None:
        self.store = store
        self.database_url = "postgresql://synthetic.invalid/test"
        self.database_path = Path("synthetic-postgresql")

    def initialise(self) -> None:
        self.store.initialise()

    @contextmanager
    def transaction(self):
        with self.store.transaction() as connection:
            yield connection
