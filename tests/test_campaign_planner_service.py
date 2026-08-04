from __future__ import annotations

import unittest
from datetime import date, datetime, timezone

from app.campaign_planner import (
    CampaignAudience,
    CampaignChannel,
    CampaignMetric,
    CampaignObjective,
    CampaignPlan,
    CampaignPlanningService,
    CampaignStatus,
    CampaignTimeline,
)


class CampaignPlanningServiceTests(unittest.TestCase):
    def setUp(self):
        self.service = CampaignPlanningService()

    @staticmethod
    def values(**overrides):
        values = {
            "campaign_id": "campaign-one",
            "tenant_id": "tenant-one",
            "brand_id": "brand-one",
            "name": "Workshop Acquisition",
            "objective": CampaignObjective(
                "Increase qualified enquiries", "Grow recurring workshop revenue."
            ),
            "audience": CampaignAudience(
                "Independent workshops", "Repair workshops in the Western Cape."
            ),
            "timeline": CampaignTimeline(date(2026, 9, 1), date(2026, 9, 30)),
            "channels": (CampaignChannel("Facebook"),),
            "success_metrics": (
                CampaignMetric("Qualified enquiries", "25", "CRM enquiry source"),
            ),
            "owner": "Delight Mugara",
        }
        values.update(overrides)
        return values

    def make_plan(self, **overrides):
        return CampaignPlan(**self.values(**overrides))

    def test_create_plan_returns_valid_draft(self):
        self.assertEqual(
            self.service.create_plan(**self.values()).status, CampaignStatus.DRAFT
        )

    def test_service_rejects_invalid_validator(self):
        with self.assertRaisesRegex(TypeError, "validator"):
            CampaignPlanningService(validator=object())

    def test_revise_plan_does_not_mutate_source(self):
        original = self.make_plan(status=CampaignStatus.PLANNED)
        revised = self.service.revise_plan(original, name="Revised Campaign")
        self.assertEqual(original.name, "Workshop Acquisition")
        self.assertEqual(revised.name, "Revised Campaign")
        self.assertEqual(revised.status, CampaignStatus.DRAFT)

    def test_revise_plan_rejects_unknown_field(self):
        with self.assertRaisesRegex(ValueError, "Unsupported"):
            self.service.revise_plan(self.make_plan(), unsupported="value")

    def test_revise_plan_rejects_approved_plan(self):
        with self.assertRaisesRegex(ValueError, "draft or planned"):
            self.service.revise_plan(
                self.make_plan(status=CampaignStatus.APPROVED), name="Changed"
            )

    def test_evaluate_readiness_returns_structured_result(self):
        result = self.service.evaluate_readiness(
            self.make_plan(objective=CampaignObjective("Increase qualified enquiries"))
        )
        self.assertFalse(result.is_valid)
        self.assertIn("objective", result.fields)

    def test_mark_planned_advances_draft(self):
        plan = self.make_plan()
        self.service.mark_planned(plan)
        self.assertEqual(plan.status, CampaignStatus.PLANNED)

    def test_approve_requires_planned_status(self):
        with self.assertRaisesRegex(ValueError, "planned"):
            self.service.approve(self.make_plan())

    def test_approve_requires_readiness(self):
        plan = self.make_plan(
            status=CampaignStatus.PLANNED,
            objective=CampaignObjective("Increase qualified enquiries"),
        )
        with self.assertRaisesRegex(ValueError, "rationale"):
            self.service.approve(plan)

    def test_full_lifecycle_operations(self):
        plan = self.make_plan()
        times = [datetime(2026, 8, 4, h, tzinfo=timezone.utc) for h in range(13, 18)]
        self.service.mark_planned(plan, changed_at=times[0])
        self.service.approve(plan, changed_at=times[1])
        self.service.activate(plan, changed_at=times[2])
        self.service.complete(plan, changed_at=times[3])
        self.service.archive(plan, changed_at=times[4])
        self.assertEqual(plan.status, CampaignStatus.ARCHIVED)
        self.assertEqual(plan.updated_at, times[4])

    def test_service_rejects_invalid_plan_type(self):
        with self.assertRaisesRegex(TypeError, "CampaignPlan"):
            self.service.evaluate_readiness(object())


if __name__ == "__main__":
    unittest.main()
