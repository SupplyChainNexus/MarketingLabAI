"""Tests for immutable, versioned Campaign Plan persistence."""

from __future__ import annotations

import tempfile
import unittest
from datetime import date
from pathlib import Path

from app.campaign_planner import (
    CampaignAudience, CampaignChannel, CampaignMetric, CampaignObjective,
    CampaignPlan, CampaignPlanRepository, CampaignPlanningService,
    CampaignStatus, CampaignTimeline,
)
from app.database.connection import SQLiteDatabase


class CampaignPlanRepositoryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.database = SQLiteDatabase(
            Path(self.temporary_directory.name) / "marketinglabai.db"
        )
        self.database.initialise()
        with self.database.transaction() as connection:
            connection.execute(
                """
                INSERT INTO brands (
                    brand_id, tenant_id, name, payload_json, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                ("brand-one", "default", "Brand One", "{}", "timestamp", "timestamp"),
            )
        self.repository = CampaignPlanRepository(self.database)
        self.service = CampaignPlanningService()
        self.plan = self.make_plan()

    def tearDown(self) -> None:
        self.temporary_directory.cleanup()

    @staticmethod
    def make_plan(**overrides: object) -> CampaignPlan:
        values: dict[str, object] = {
            "campaign_id": "campaign-one", "tenant_id": "default",
            "brand_id": "brand-one", "name": "Workshop Acquisition",
            "objective": CampaignObjective("Increase enquiries", "Support growth"),
            "audience": CampaignAudience("Workshops", "Independent workshops"),
            "timeline": CampaignTimeline(date(2026, 9, 1), date(2026, 9, 30)),
            "channels": (CampaignChannel("Facebook"),),
            "success_metrics": (CampaignMetric("Leads", "25"),),
            "owner": "Campaign Team", "status": CampaignStatus.APPROVED,
        }
        values.update(overrides)
        return CampaignPlan(**values)

    def test_round_trip_latest_and_specific_versions(self) -> None:
        self.repository.save(self.plan)
        second = self.service.create_next_version(self.plan, name="Updated")
        self.repository.save(second)
        self.assertEqual(
            self.repository.get("campaign-one", tenant_id="default").version, 2
        )
        self.assertEqual(
            self.repository.get("campaign-one", tenant_id="default", version=1).version,
            1,
        )

    def test_duplicate_version_is_rejected(self) -> None:
        self.repository.save(self.plan)
        with self.assertRaisesRegex(ValueError, "already exists"):
            self.repository.save(self.plan)

    def test_history_and_latest_brand_listing(self) -> None:
        self.repository.save(self.plan)
        self.repository.save(self.service.create_next_version(self.plan, name="Updated"))
        self.repository.save(
            self.make_plan(
                campaign_id="campaign-two", name="Draft Campaign",
                status=CampaignStatus.DRAFT,
            )
        )
        self.assertEqual(
            [plan.version for plan in self.repository.list_versions(
                "campaign-one", tenant_id="default"
            )],
            [1, 2],
        )
        latest = self.repository.list_latest_for_brand(
            tenant_id="default", brand_id="brand-one"
        )
        approved = self.repository.list_latest_for_brand(
            tenant_id="default", brand_id="brand-one", status="approved"
        )
        self.assertEqual([plan.campaign_id for plan in latest], ["campaign-one", "campaign-two"])
        self.assertEqual([plan.campaign_id for plan in approved], ["campaign-one"])
        self.assertEqual(latest[0].version, 2)

    def test_repository_enforces_tenant_and_brand_ownership(self) -> None:
        with self.assertRaisesRegex(ValueError, "Tenant"):
            self.repository.save(self.make_plan(tenant_id="missing"))
        with self.assertRaisesRegex(ValueError, "Brand"):
            self.repository.save(self.make_plan(brand_id="missing"))
        with self.database.transaction() as connection:
            connection.execute(
                """
                INSERT INTO tenants (tenant_id, name, status, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                ("tenant-two", "Tenant Two", "active", "timestamp", "timestamp"),
            )
        with self.assertRaisesRegex(ValueError, "does not belong"):
            self.repository.save(self.make_plan(tenant_id="tenant-two"))

    def test_exists_and_count_include_immutable_versions(self) -> None:
        self.repository.save(self.plan)
        self.repository.save(self.service.create_next_version(self.plan, name="Updated"))
        self.assertTrue(self.repository.exists(
            "campaign-one", tenant_id="default", version=1
        ))
        self.assertEqual(self.repository.count(tenant_id="default"), 2)


if __name__ == "__main__":
    unittest.main()
