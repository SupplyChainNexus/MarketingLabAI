"""Tests for deterministic Campaign Asset dependency planning."""

import unittest

from app.campaign_planner import (
    CampaignAsset,
    CampaignAssetStatus,
    CampaignAssetType,
    CampaignDependencyPlanner,
    CampaignPriority,
)


class CampaignDependencyPlannerTests(unittest.TestCase):
    @staticmethod
    def asset(
        asset_id: str,
        *,
        dependencies=(),
        priority=CampaignPriority.NORMAL,
        status=CampaignAssetStatus.PLANNED,
    ):
        return CampaignAsset(
            campaign_id="campaign-one",
            asset_id=asset_id,
            name=asset_id.replace("-", " ").title(),
            channel="Website",
            asset_type=CampaignAssetType("Deliverable"),
            owner="Marketing Team",
            dependency_ids=dependencies,
            priority=priority,
            status=status,
        )

    def setUp(self) -> None:
        self.planner = CampaignDependencyPlanner()

    def test_execution_order_respects_dependencies(self) -> None:
        brief = self.asset("brief", priority=CampaignPriority.HIGH)
        copy = self.asset("copy", dependencies=("brief",))
        image = self.asset("image", dependencies=("brief",))
        landing = self.asset("landing", dependencies=("copy", "image"))
        order = self.planner.execution_order((landing, image, copy, brief))
        positions = {asset.asset_id: index for index, asset in enumerate(order)}
        self.assertLess(positions["brief"], positions["copy"])
        self.assertLess(positions["brief"], positions["image"])
        self.assertLess(positions["copy"], positions["landing"])
        self.assertLess(positions["image"], positions["landing"])

    def test_priority_breaks_dependency_free_ties(self) -> None:
        low = self.asset("low", priority=CampaignPriority.LOW)
        critical = self.asset("critical", priority=CampaignPriority.CRITICAL)
        self.assertEqual(
            tuple(
                asset.asset_id
                for asset in self.planner.execution_order((low, critical))
            ),
            ("critical", "low"),
        )

    def test_missing_dependency_is_reported(self) -> None:
        issues = self.planner.validate((self.asset("copy", dependencies=("brief",)),))
        self.assertEqual(issues[0].code, "missing_dependency")

    def test_cycle_is_rejected(self) -> None:
        first = self.asset("first", dependencies=("second",))
        second = self.asset("second", dependencies=("first",))
        with self.assertRaisesRegex(ValueError, "cycle"):
            self.planner.execution_order((first, second))

    def test_blocked_assets_require_completed_dependencies(self) -> None:
        brief = self.asset("brief", status=CampaignAssetStatus.COMPLETED)
        copy = self.asset("copy", dependencies=("brief",))
        landing = self.asset("landing", dependencies=("copy",))
        self.assertEqual(
            tuple(
                asset.asset_id
                for asset in self.planner.blocked_assets((brief, copy, landing))
            ),
            ("landing",),
        )


if __name__ == "__main__":
    unittest.main()
