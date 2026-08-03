"Tests for versioned Marketing Brief persistence."

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from app.database.connection import SQLiteDatabase
from app.database.repositories import BrandRepository
from app.marketing_brief import (
    BriefStatus,
    MarketingBrief,
    MarketingBriefRepository,
    MarketingBriefService,
)


class MarketingBriefRepositoryTests(unittest.TestCase):
    "Validate immutable tenant-owned brief persistence."

    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.database = SQLiteDatabase(
            Path(self.temporary_directory.name) / "marketinglabai.db"
        )
        self.database.initialise()

        BrandRepository(self.database).save(
            {
                "brand_id": "brand-one",
                "tenant_id": "default",
                "name": "Brand One",
            }
        )
        self.repository = MarketingBriefRepository(self.database)
        self.service = MarketingBriefService(self.repository)
        self.brief = self.make_brief()

    def tearDown(self) -> None:
        self.temporary_directory.cleanup()

    @staticmethod
    def make_brief(
        **overrides: object,
    ) -> MarketingBrief:
        values: dict[str, object] = {
            "brief_id": "brief-one",
            "tenant_id": "default",
            "brand_id": "brand-one",
            "name": "Workshop Acquisition",
            "objective": "Increase qualified enquiries",
            "audience": "Repair workshops",
            "key_message": "Dependable access to parts",
            "call_to_action": "Request a quote",
            "channels": ["facebook"],
            "deliverables": ["Lead advert"],
            "status": BriefStatus.APPROVED,
        }
        values.update(overrides)

        return MarketingBrief(**values)

    def test_repository_round_trip(self) -> None:
        self.repository.save(self.brief)

        restored = self.repository.get(
            "brief-one",
            tenant_id="default",
        )

        self.assertEqual(
            restored.to_dict(),
            self.brief.to_dict(),
        )

    def test_latest_and_specific_versions(self) -> None:
        self.repository.save(self.brief)
        self.service.save_next_version(
            self.brief,
            name="Updated",
        )

        latest = self.repository.get(
            "brief-one",
            tenant_id="default",
        )
        original = self.repository.get(
            "brief-one",
            tenant_id="default",
            version=1,
        )

        self.assertEqual(latest.version, 2)
        self.assertEqual(original.version, 1)

    def test_duplicate_version_is_rejected(self) -> None:
        self.repository.save(self.brief)

        with self.assertRaisesRegex(
            ValueError,
            "already exists",
        ):
            self.repository.save(self.brief)

    def test_list_versions_preserves_history(self) -> None:
        self.repository.save(self.brief)
        self.service.save_next_version(
            self.brief,
            name="Updated",
        )

        versions = self.repository.list_versions(
            "brief-one",
            tenant_id="default",
        )

        self.assertEqual(
            [brief.version for brief in versions],
            [1, 2],
        )

    def test_list_latest_for_brand_and_status(self) -> None:
        self.repository.save(self.brief)
        self.service.save_next_version(
            self.brief,
            name="Updated",
        )
        self.repository.save(
            self.make_brief(
                brief_id="brief-two",
                name="Draft Brief",
                status=BriefStatus.DRAFT,
            )
        )

        all_briefs = self.repository.list_latest_for_brand(
            tenant_id="default",
            brand_id="brand-one",
        )
        approved = self.repository.list_latest_for_brand(
            tenant_id="default",
            brand_id="brand-one",
            status="approved",
        )

        self.assertEqual(
            [brief.brief_id for brief in all_briefs],
            ["brief-one", "brief-two"],
        )
        self.assertEqual(
            [brief.brief_id for brief in approved],
            ["brief-one"],
        )
        self.assertEqual(all_briefs[0].version, 2)

    def test_repository_enforces_ownership(self) -> None:
        with self.assertRaisesRegex(ValueError, "Tenant"):
            self.repository.save(self.make_brief(tenant_id="missing"))

        with self.assertRaisesRegex(ValueError, "Brand"):
            self.repository.save(self.make_brief(brand_id="missing"))

        with self.database.transaction() as connection:
            connection.execute(
                """
                INSERT OR IGNORE INTO tenants (
                    tenant_id,
                    name,
                    status,
                    created_at,
                    updated_at
                )
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    "tenant-two",
                    "Tenant Two",
                    "active",
                    "2026-08-03T00:00:00+00:00",
                    "2026-08-03T00:00:00+00:00",
                ),
            )

        with self.assertRaisesRegex(
            ValueError,
            "does not belong",
        ):
            self.repository.save(self.make_brief(tenant_id="tenant-two"))

    def test_exists_and_count_include_versions(self) -> None:
        self.repository.save(self.brief)
        self.service.save_next_version(
            self.brief,
            name="Updated",
        )

        self.assertTrue(
            self.repository.exists(
                "brief-one",
                tenant_id="default",
                version=1,
            )
        )
        self.assertEqual(
            self.repository.count(tenant_id="default"),
            2,
        )


if __name__ == "__main__":
    unittest.main()
