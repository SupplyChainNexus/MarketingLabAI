"""Tests for Campaign Planning Service asset operations."""

import unittest

from app.campaign_planner import (
    CampaignAsset,
    CampaignAssetType,
    CampaignPlanningService,
)


class CampaignAssetServiceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.service = CampaignPlanningService()

    @staticmethod
    def asset(asset_id: str, *, name=None, dependencies=(), campaign_id="campaign-one"):
        return CampaignAsset(
            campaign_id=campaign_id,
            asset_id=asset_id,
            name=name or asset_id.title(),
            channel="Facebook",
            asset_type=CampaignAssetType("Image"),
            owner="Marketing Team",
            dependency_ids=dependencies,
        )

    def test_add_asset_returns_new_collection(self) -> None:
        existing = (self.asset("first"),)
        updated = self.service.add_asset(
            existing,
            self.asset("second"),
            campaign_id="campaign-one",
        )
        self.assertEqual(len(existing), 1)
        self.assertEqual(len(updated), 2)

    def test_add_asset_rejects_other_campaign(self) -> None:
        with self.assertRaisesRegex(ValueError, "different campaign"):
            self.service.add_asset(
                (),
                self.asset("asset", campaign_id="other"),
                campaign_id="campaign-one",
            )

    def test_add_asset_rejects_duplicate_deliverable(self) -> None:
        first = self.asset("first", name="Primary Image")
        duplicate = self.asset("second", name="primary image")
        with self.assertRaisesRegex(ValueError, "matching"):
            self.service.add_asset(
                (first,),
                duplicate,
                campaign_id="campaign-one",
            )

    def test_remove_asset_rejects_existing_dependant(self) -> None:
        first = self.asset("first")
        second = self.asset("second", dependencies=("first",))
        with self.assertRaisesRegex(ValueError, "dependants"):
            self.service.remove_asset((first, second), "first")

    def test_remove_leaf_asset(self) -> None:
        first = self.asset("first")
        second = self.asset("second")
        remaining = self.service.remove_asset((first, second), "second")
        self.assertEqual(tuple(asset.asset_id for asset in remaining), ("first",))


if __name__ == "__main__":
    unittest.main()
