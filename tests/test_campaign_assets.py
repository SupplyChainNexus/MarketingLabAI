"""Tests for Campaign Asset planning models."""

import unittest

from app.campaign_planner import (
    CampaignAsset,
    CampaignAssetStatus,
    CampaignAssetType,
    CampaignPriority,
    DefinitionOfDoneItem,
)


class CampaignAssetTests(unittest.TestCase):
    @staticmethod
    def make_asset(**overrides: object) -> CampaignAsset:
        values: dict[str, object] = {
            "campaign_id": "campaign-one",
            "asset_id": "asset-one",
            "name": "Facebook Primary Image",
            "channel": "Facebook",
            "asset_type": CampaignAssetType("Image", "Creative"),
            "owner": "Marketing Team",
            "purpose": "Generate awareness",
            "priority": CampaignPriority.HIGH,
            "definition_of_done": (
                DefinitionOfDoneItem("Dimensions approved"),
                DefinitionOfDoneItem("Brand review passed"),
            ),
        }
        values.update(overrides)
        return CampaignAsset(**values)

    def test_asset_round_trip(self) -> None:
        original = self.make_asset()
        self.assertEqual(
            CampaignAsset.from_dict(original.to_dict()).to_dict(),
            original.to_dict(),
        )

    def test_asset_rejects_self_dependency(self) -> None:
        with self.assertRaisesRegex(ValueError, "itself"):
            self.make_asset(dependency_ids=("asset-one",))

    def test_duplicate_key_is_case_insensitive(self) -> None:
        first = self.make_asset()
        second = self.make_asset(
            asset_id="asset-two",
            name="facebook primary image",
            channel="facebook",
            asset_type=CampaignAssetType("image"),
        )
        self.assertEqual(first.duplicate_key, second.duplicate_key)

    def test_definition_progress_updates(self) -> None:
        asset = self.make_asset()
        asset.mark_definition_item("Dimensions approved")
        self.assertEqual(asset.completion_ratio, 0.5)
        asset.mark_definition_item("Brand review passed")
        self.assertTrue(asset.definition_complete)

    def test_approval_requires_complete_definition(self) -> None:
        asset = self.make_asset(status=CampaignAssetStatus.UNDER_REVIEW)
        with self.assertRaisesRegex(ValueError, "Definition of done"):
            asset.transition_to(CampaignAssetStatus.APPROVED)

    def test_full_asset_lifecycle(self) -> None:
        asset = self.make_asset()
        asset.mark_definition_item("Dimensions approved")
        asset.mark_definition_item("Brand review passed")
        for status in (
            CampaignAssetStatus.READY,
            CampaignAssetStatus.IN_PROGRESS,
            CampaignAssetStatus.UNDER_REVIEW,
            CampaignAssetStatus.APPROVED,
            CampaignAssetStatus.COMPLETED,
        ):
            asset.transition_to(status)
        self.assertEqual(asset.status, CampaignAssetStatus.COMPLETED)

    def test_invalid_asset_transition_is_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "planned to approved"):
            self.make_asset().transition_to(CampaignAssetStatus.APPROVED)


if __name__ == "__main__":
    unittest.main()
