"""Tests for tenant-scoped, immutable Strategy Intelligence persistence."""

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
    TargetKind,
)
from app.strategy_intelligence import (
    StrategyDecision,
    StrategyEvidence,
    StrategyRepository,
    StrategyService,
    StrategyStatus,
)


class StrategyRepositoryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.folder = tempfile.TemporaryDirectory()
        self.database = SQLiteDatabase(Path(self.folder.name) / "db.sqlite")
        self.database.initialise()
        BrandRepository(self.database).save(
            {"brand_id": "brand-one", "tenant_id": "default", "name": "Brand One"}
        )
        self.positioning_repository = PositioningRepository(self.database)
        positioning_service = PositioningService(self.positioning_repository)
        draft = positioning_service.create(
            PositioningDecision(
                positioning_id="positioning-one",
                version=1,
                tenant_id="default",
                brand_id="brand-one",
                target_kind=TargetKind.SEGMENT,
                target_id="segment-one",
                product_id="product-one",
                value_proposition="A supported synthetic value proposition",
                evidence=[
                    PositioningEvidence("Synthetic", "Synthetic proof", 0.8, True)
                ],
            )
        )
        self.positioning = positioning_service.approve(draft)
        self.repository = StrategyRepository(self.database)
        self.service = StrategyService(self.repository, self.positioning_repository)

    def tearDown(self) -> None:
        self.folder.cleanup()

    def decision(self, *, tenant_id: str = "default") -> StrategyDecision:
        return StrategyDecision(
            strategy_id="strategy-one",
            version=1,
            tenant_id=tenant_id,
            brand_id="brand-one",
            positioning_id=self.positioning.positioning_id,
            positioning_version=self.positioning.version,
            business_objectives=["Increase qualified synthetic enquiries"],
            evidence=[
                StrategyEvidence("Synthetic", "Synthetic objective evidence", 0.8, True)
            ],
        )

    def test_immutable_versions_round_trip_and_latest(self) -> None:
        first = self.service.create(self.decision())
        second = self.service.revise(first, planning_horizon="Next 90 days")
        self.assertEqual(second.version, 2)
        self.assertEqual(
            self.repository.get(
                tenant_id="default", strategy_id="strategy-one", version=1
            ),
            first,
        )
        self.assertEqual(
            self.repository.latest(tenant_id="default", strategy_id="strategy-one"),
            second,
        )
        with self.assertRaisesRegex(ValueError, "immutable"):
            self.repository.save(first)

    def test_approval_requires_matching_approved_positioning(self) -> None:
        first = self.service.create(self.decision())
        approved = self.service.approve(first)
        self.assertEqual(approved.status, StrategyStatus.APPROVED)
        self.assertTrue(approved.approved_at)

        other = self.decision()
        other.strategy_id = "strategy-two"
        other.positioning_version = 1
        self.service.create(other)
        with self.assertRaisesRegex(ValueError, "approved positioning"):
            self.service.approve(other)

    def test_stale_revision_and_protected_changes_are_rejected(self) -> None:
        first = self.service.create(self.decision())
        self.service.revise(first, planning_horizon="Quarter")
        with self.assertRaisesRegex(ValueError, "latest"):
            self.service.revise(first, planning_horizon="Year")
        latest = self.repository.latest(tenant_id="default", strategy_id="strategy-one")
        with self.assertRaisesRegex(ValueError, "protected"):
            self.service.revise(latest, tenant_id="another")

    def test_tenant_ownership_and_cross_tenant_reads_are_enforced(self) -> None:
        with self.assertRaisesRegex(ValueError, "tenant and brand differ"):
            self.repository.save(self.decision(tenant_id="another"))
        self.service.create(self.decision())
        with self.assertRaises(FileNotFoundError):
            self.repository.latest(tenant_id="another", strategy_id="strategy-one")

    def test_latest_brand_listing_is_tenant_scoped(self) -> None:
        first = self.service.create(self.decision())
        second = self.service.revise(first, planning_horizon="Quarter")
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
