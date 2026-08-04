"""Tests for MarketingLabAI SQLite persistence and migration."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from app.database.connection import SQLiteDatabase
from app.database.migration import JsonToSQLiteMigrator
from app.database.repositories import (
    BrandRepository,
    BusinessIntelligenceRepository,
)
from app.intelligence.models import BusinessIntelligenceProfile


class SQLiteDatabaseTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.database_path = Path(self.temporary_directory.name) / "marketinglabai.db"
        self.database = SQLiteDatabase(self.database_path)

    def tearDown(self) -> None:
        self.temporary_directory.cleanup()

    def test_initialise_creates_required_tables(self) -> None:
        self.database.initialise()

        self.assertEqual(
            self.database.table_names(),
            [
                "brands",
                "business_intelligence_profiles",
                "campaign_plans",
                "compliance_rules",
                "customer_intelligence_profiles",
                "data_migration_log",
                "marketing_briefs",
                "memory_events",
                "prompt_packs",
                "schema_migrations",
                "tenants",
            ],
        )

    def test_integrity_check_returns_ok(self) -> None:
        self.database.initialise()

        self.assertEqual(self.database.integrity_check(), "ok")

    def test_read_connection_is_closed_after_context(self) -> None:
        self.database.initialise()

        with self.database.connection() as connection:
            connection.execute("SELECT 1").fetchone()

        with self.assertRaises(Exception):
            connection.execute("SELECT 1")

    def test_transaction_rolls_back_after_error(self) -> None:
        self.database.initialise()

        with self.assertRaises(RuntimeError):
            with self.database.transaction() as connection:
                connection.execute(
                    """
                    INSERT INTO brands (
                        brand_id,
                        name,
                        payload_json,
                        created_at,
                        updated_at
                    )
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (
                        "rollback-brand",
                        "Rollback Brand",
                        "{}",
                        "timestamp",
                        "timestamp",
                    ),
                )
                raise RuntimeError("Force rollback")

        repository = BrandRepository(self.database)

        self.assertFalse(repository.exists("rollback-brand"))


class RepositoryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.database = SQLiteDatabase(
            Path(self.temporary_directory.name) / "marketinglabai.db"
        )
        self.database.initialise()
        self.brand_repository = BrandRepository(self.database)
        self.intelligence_repository = BusinessIntelligenceRepository(self.database)

    def tearDown(self) -> None:
        self.temporary_directory.cleanup()

    def test_brand_repository_round_trip(self) -> None:
        payload = {
            "brand_id": "test-brand",
            "name": "Test Brand",
            "industry": "Software",
            "description": "An AI platform.",
            "target_audience": ["Small businesses"],
            "products": ["AI platform"],
            "values": ["Trust"],
            "website": "https://example.test",
        }

        self.brand_repository.save(payload)

        self.assertTrue(self.brand_repository.exists("test-brand"))
        self.assertEqual(
            self.brand_repository.get("test-brand"),
            payload,
        )
        self.assertEqual(
            self.brand_repository.list_ids(),
            ["test-brand"],
        )

    def test_brand_repository_updates_existing_record(self) -> None:
        payload = {
            "brand_id": "test-brand",
            "name": "Original Name",
        }
        self.brand_repository.save(payload)

        payload["name"] = "Updated Name"
        self.brand_repository.save(payload)

        stored_payload = self.brand_repository.get("test-brand")

        self.assertEqual(stored_payload["name"], "Updated Name")
        self.assertEqual(self.brand_repository.count(), 1)

    def test_business_intelligence_round_trip(self) -> None:
        self.brand_repository.save(
            {
                "brand_id": "test-brand",
                "name": "Test Brand",
            }
        )

        profile = BusinessIntelligenceProfile(
            brand_id="test-brand",
            revenue_model="Subscriptions",
            gross_margin_percent=80,
            sales_channels=["Website"],
            business_goals=["Acquire customers"],
        )

        self.intelligence_repository.save(profile)
        restored_profile = self.intelligence_repository.get("test-brand")

        self.assertTrue(self.intelligence_repository.exists("test-brand"))
        self.assertEqual(
            restored_profile.revenue_model,
            "Subscriptions",
        )
        self.assertEqual(
            restored_profile.business_goals,
            ["Acquire customers"],
        )


class JsonToSQLiteMigrationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory()
        root = Path(self.temporary_directory.name)

        self.brands_directory = root / "brands"
        self.intelligence_directory = root / "business_intelligence"
        self.backup_root = root / "backups"
        self.database = SQLiteDatabase(root / "marketinglabai.db")

        self.brands_directory.mkdir()
        self.intelligence_directory.mkdir()

        brand_payload = {
            "brand_id": "marketinglabai-demo",
            "name": "MarketingLabAI Demo",
            "industry": "Artificial Intelligence Software",
            "description": "AI marketing operating system.",
            "target_audience": ["Small businesses"],
            "products": ["AI Marketing Platform"],
            "values": ["Innovation", "Trust"],
            "website": "https://marketinglabai.local",
        }

        intelligence_payload = {
            "brand_id": "marketinglabai-demo",
            "revenue_model": "Monthly SaaS subscriptions",
            "average_order_value": 999,
            "gross_margin_percent": 80,
            "customer_lifetime_value": 5000,
            "customer_acquisition_cost": 250,
            "sales_cycle_days": 14,
            "monthly_marketing_budget": 10000,
            "team_size": 4,
            "sales_channels": ["Website", "Direct sales"],
            "geographic_markets": ["South Africa"],
            "capacity_constraints": ["Development capacity"],
            "seasonality": ["Annual planning season"],
            "competitors": ["Jasper", "HubSpot"],
            "business_goals": ["Acquire paying customers"],
            "updated_at": "2026-01-01T00:00:00+00:00",
        }

        self._write_json(
            self.brands_directory / "marketinglabai-demo.json",
            brand_payload,
        )
        self._write_json(
            self.intelligence_directory / "marketinglabai-demo.json",
            intelligence_payload,
        )

    def tearDown(self) -> None:
        self.temporary_directory.cleanup()

    def test_migration_imports_brand_and_company_brain(self) -> None:
        migrator = self._build_migrator()

        result = migrator.migrate()

        brand_repository = BrandRepository(self.database)
        intelligence_repository = BusinessIntelligenceRepository(self.database)

        self.assertEqual(result.brands_imported, 1)
        self.assertEqual(result.intelligence_profiles_imported, 1)
        self.assertEqual(result.records_failed, 0)
        self.assertTrue(brand_repository.exists("marketinglabai-demo"))
        self.assertTrue(intelligence_repository.exists("marketinglabai-demo"))
        self.assertIsNotNone(result.backup_directory)
        self.assertTrue(result.backup_directory.exists())

    def test_second_migration_skips_existing_records(self) -> None:
        migrator = self._build_migrator()

        first_result = migrator.migrate()
        second_result = migrator.migrate()

        self.assertEqual(first_result.brands_imported, 1)
        self.assertEqual(second_result.brands_imported, 0)
        self.assertEqual(
            second_result.intelligence_profiles_imported,
            0,
        )
        self.assertEqual(second_result.records_skipped, 2)

    def test_migration_preserves_source_files(self) -> None:
        migrator = self._build_migrator()

        migrator.migrate()

        self.assertTrue((self.brands_directory / "marketinglabai-demo.json").exists())
        self.assertTrue(
            (self.intelligence_directory / "marketinglabai-demo.json").exists()
        )

    def _build_migrator(self) -> JsonToSQLiteMigrator:
        return JsonToSQLiteMigrator(
            database=self.database,
            brands_directory=self.brands_directory,
            intelligence_directory=self.intelligence_directory,
            backup_root=self.backup_root,
        )

    @staticmethod
    def _write_json(
        path: Path,
        payload: dict[str, object],
    ) -> None:
        path.write_text(
            json.dumps(payload, indent=2),
            encoding="utf-8",
        )


if __name__ == "__main__":
    unittest.main()
