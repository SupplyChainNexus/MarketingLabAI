"""Tests for the Campaign Planner foundation."""

from __future__ import annotations

import unittest
from datetime import date, datetime, timezone

from app.campaign_planner import (
    CampaignAudience,
    CampaignChannel,
    CampaignMetric,
    CampaignObjective,
    CampaignPlan,
    CampaignStatus,
    CampaignTimeline,
)


class CampaignPlannerFoundationTests(unittest.TestCase):
    """Verify campaign planning domain behaviour."""

    @staticmethod
    def make_plan(**overrides: object) -> CampaignPlan:
        values: dict[str, object] = {
            "campaign_id": "campaign-one",
            "tenant_id": "tenant-one",
            "brand_id": "brand-one",
            "name": "Workshop Acquisition",
            "objective": CampaignObjective(
                statement="Increase qualified workshop enquiries",
                rationale="Grow the recurring trade-customer base.",
            ),
            "audience": CampaignAudience(
                name="Independent workshops",
                description="Repair workshops in the Western Cape.",
                segment_id="segment-workshops",
            ),
            "timeline": CampaignTimeline(
                start_date=date(2026, 9, 1),
                end_date=date(2026, 9, 30),
            ),
            "channels": (
                CampaignChannel(
                    name="Facebook",
                    purpose="Reach local workshop owners.",
                ),
                CampaignChannel(
                    name="Email",
                    purpose="Nurture known trade customers.",
                ),
            ),
            "success_metrics": (
                CampaignMetric(
                    name="Qualified enquiries",
                    target="25",
                    measurement_method="CRM enquiry source",
                ),
            ),
            "owner": "Delight Mugara",
            "created_at": datetime(2026, 8, 4, 12, 0, tzinfo=timezone.utc),
            "updated_at": datetime(2026, 8, 4, 12, 0, tzinfo=timezone.utc),
        }
        values.update(overrides)
        return CampaignPlan(**values)

    def test_value_objects_clean_text(self) -> None:
        objective = CampaignObjective(
            statement="  Increase enquiries  ",
            rationale="  Support growth  ",
        )
        self.assertEqual(objective.statement, "Increase enquiries")
        self.assertEqual(objective.rationale, "Support growth")

    def test_timeline_is_inclusive(self) -> None:
        timeline = CampaignTimeline(
            start_date=date(2026, 9, 1),
            end_date=date(2026, 9, 30),
        )
        self.assertEqual(timeline.duration_days, 30)
        self.assertTrue(timeline.includes(date(2026, 9, 1)))
        self.assertTrue(timeline.includes(date(2026, 9, 30)))
        self.assertFalse(timeline.includes(date(2026, 10, 1)))

    def test_timeline_rejects_inverted_dates(self) -> None:
        with self.assertRaisesRegex(ValueError, "earlier"):
            CampaignTimeline(
                start_date=date(2026, 9, 30),
                end_date=date(2026, 9, 1),
            )

    def test_plan_requires_channels(self) -> None:
        with self.assertRaisesRegex(ValueError, "channel"):
            self.make_plan(channels=())

    def test_plan_requires_success_metrics(self) -> None:
        with self.assertRaisesRegex(ValueError, "metric"):
            self.make_plan(success_metrics=())

    def test_plan_rejects_duplicate_channels(self) -> None:
        with self.assertRaisesRegex(ValueError, "unique"):
            self.make_plan(
                channels=(
                    CampaignChannel(name="Facebook"),
                    CampaignChannel(name="facebook"),
                )
            )

    def test_plan_rejects_duplicate_metrics(self) -> None:
        with self.assertRaisesRegex(ValueError, "unique"):
            self.make_plan(
                success_metrics=(
                    CampaignMetric(name="Leads", target="10"),
                    CampaignMetric(name="leads", target="20"),
                )
            )

    def test_plan_accepts_list_inputs_and_freezes_collections(self) -> None:
        plan = self.make_plan(
            channels=[CampaignChannel(name="Facebook")],
            success_metrics=[CampaignMetric(name="Leads", target="10")],
        )
        self.assertIsInstance(plan.channels, tuple)
        self.assertIsInstance(plan.success_metrics, tuple)

    def test_plan_serialisation_round_trip(self) -> None:
        original = self.make_plan(notes="Use direct, practical language.")
        restored = CampaignPlan.from_dict(original.to_dict())
        self.assertEqual(restored.to_dict(), original.to_dict())
        self.assertIsNot(restored.channels, original.channels)
        self.assertIsNot(restored.success_metrics, original.success_metrics)

    def test_plan_version_defaults_to_one_and_must_be_positive(self) -> None:
        self.assertEqual(self.make_plan().version, 1)
        with self.assertRaisesRegex(ValueError, "at least 1"):
            self.make_plan(version=0)
        with self.assertRaisesRegex(TypeError, "integer"):
            self.make_plan(version=True)

    def test_serialised_collections_are_detached(self) -> None:
        plan = self.make_plan()
        payload = plan.to_dict()
        payload["channels"][0]["name"] = "Changed"
        payload["success_metrics"][0]["name"] = "Changed"
        self.assertEqual(plan.channels[0].name, "Facebook")
        self.assertEqual(plan.success_metrics[0].name, "Qualified enquiries")

    def test_valid_lifecycle_transitions(self) -> None:
        plan = self.make_plan()
        for status in (
            CampaignStatus.PLANNED,
            CampaignStatus.APPROVED,
            CampaignStatus.ACTIVE,
            CampaignStatus.COMPLETED,
            CampaignStatus.ARCHIVED,
        ):
            plan.transition_to(status)
        self.assertEqual(plan.status, CampaignStatus.ARCHIVED)

    def test_planned_campaign_can_return_to_draft(self) -> None:
        plan = self.make_plan(status=CampaignStatus.PLANNED)
        plan.transition_to(CampaignStatus.DRAFT)
        self.assertEqual(plan.status, CampaignStatus.DRAFT)

    def test_approved_campaign_can_return_to_planned(self) -> None:
        plan = self.make_plan(status=CampaignStatus.APPROVED)
        plan.transition_to(CampaignStatus.PLANNED)
        self.assertEqual(plan.status, CampaignStatus.PLANNED)

    def test_invalid_lifecycle_transition_is_rejected(self) -> None:
        plan = self.make_plan()
        with self.assertRaisesRegex(ValueError, "draft to active"):
            plan.transition_to(CampaignStatus.ACTIVE)

    def test_transition_updates_timestamp(self) -> None:
        plan = self.make_plan()
        changed_at = datetime(2026, 8, 5, 10, 30, tzinfo=timezone.utc)
        plan.transition_to(
            CampaignStatus.PLANNED,
            changed_at=changed_at,
        )
        self.assertEqual(plan.updated_at, changed_at)

    def test_datetimes_must_be_timezone_aware(self) -> None:
        with self.assertRaisesRegex(ValueError, "timezone"):
            self.make_plan(created_at=datetime(2026, 8, 4, 12, 0))


if __name__ == "__main__":
    unittest.main()
