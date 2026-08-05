"""Tests for tenant-scoped, versioned Positioning Intelligence persistence."""

import tempfile
import unittest
from pathlib import Path

from app.database.connection import SQLiteDatabase
from app.database.repositories import BrandRepository
from app.positioning_intelligence import (
    PositioningDecision,
    PositioningEvidence,
    PositioningRepository,
    PositioningService,
    PositioningStatus,
    TargetKind,
)


class PositioningRepositoryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.folder = tempfile.TemporaryDirectory()
        self.database = SQLiteDatabase(Path(self.folder.name) / "db.sqlite")
        self.database.initialise()
        self.brands = BrandRepository(self.database)
        self.brands.save(
            {"brand_id": "brand-one", "tenant_id": "default", "name": "Brand One"}
        )
        self.repository = PositioningRepository(self.database)
        self.service = PositioningService(self.repository)

    def tearDown(self) -> None:
        self.folder.cleanup()

    def decision(self, *, tenant_id: str = "default") -> PositioningDecision:
        return PositioningDecision(
            positioning_id="positioning-one",
            version=1,
            tenant_id=tenant_id,
            brand_id="brand-one",
            target_kind=TargetKind.SEGMENT,
            target_id="segment-one",
            product_id="product-one",
            evidence=[
                PositioningEvidence(
                    "Synthetic evidence", "A synthetic need exists", 0.75, True
                )
            ],
        )

    def test_immutable_versions_round_trip_and_latest(self) -> None:
        first = self.service.create(self.decision())
        second = self.service.revise(first, customer_problem="Fragmented marketing")

        self.assertEqual(second.version, 2)
        self.assertEqual(
            self.repository.get(
                tenant_id="default", positioning_id="positioning-one", version=1
            ),
            first,
        )
        self.assertEqual(
            self.repository.latest(
                tenant_id="default", positioning_id="positioning-one"
            ),
            second,
        )
        with self.assertRaisesRegex(ValueError, "immutable"):
            self.repository.save(first)

    def test_approval_creates_new_immutable_version(self) -> None:
        first = self.service.create(self.decision())
        ready = self.service.revise(
            first, value_proposition="Governed marketing decisions"
        )
        approved = self.service.approve(ready)

        self.assertEqual(approved.version, 3)
        self.assertEqual(approved.status, PositioningStatus.APPROVED)
        self.assertTrue(approved.approved_at)

    def test_stale_revision_and_protected_changes_are_rejected(self) -> None:
        first = self.service.create(self.decision())
        self.service.revise(first, customer_problem="New problem")
        with self.assertRaisesRegex(ValueError, "latest"):
            self.service.revise(first, customer_problem="Stale problem")
        latest = self.repository.latest(
            tenant_id="default", positioning_id="positioning-one"
        )
        with self.assertRaisesRegex(ValueError, "protected"):
            self.service.revise(latest, tenant_id="another")

    def test_tenant_ownership_and_cross_tenant_reads_are_enforced(self) -> None:
        with self.assertRaisesRegex(ValueError, "tenant and brand differ"):
            self.repository.save(self.decision(tenant_id="another"))
        self.service.create(self.decision())
        with self.assertRaises(FileNotFoundError):
            self.repository.latest(
                tenant_id="another", positioning_id="positioning-one"
            )

    def test_latest_brand_listing_is_tenant_scoped(self) -> None:
        first = self.service.create(self.decision())
        second = self.service.revise(first, customer_problem="Updated")
        self.assertEqual(
            self.repository.list_latest_for_brand(
                tenant_id="default", brand_id="brand-one"
            ),
            [second],
        )
        self.assertEqual(
            self.repository.list_latest_for_brand(
                tenant_id="another", brand_id="brand-one"
            ),
            [],
        )


if __name__ == "__main__":
    unittest.main()
