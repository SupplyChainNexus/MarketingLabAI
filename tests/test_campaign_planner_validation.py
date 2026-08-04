from __future__ import annotations

import unittest
from datetime import date

from app.campaign_planner import (
    CampaignAudience,
    CampaignChannel,
    CampaignMetric,
    CampaignObjective,
    CampaignPlan,
    CampaignPlanValidator,
    CampaignTimeline,
    CampaignValidationIssue,
    CampaignValidationResult,
)


class CampaignPlannerValidationTests(unittest.TestCase):
    @staticmethod
    def make_plan(**overrides: object) -> CampaignPlan:
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
        return CampaignPlan(**values)

    def test_issue_round_trip(self):
        issue = CampaignValidationIssue("example", "objective", "Example issue.")
        self.assertEqual(CampaignValidationIssue.from_dict(issue.to_dict()), issue)

    def test_result_reports_valid_state(self):
        result = CampaignValidationResult()
        self.assertTrue(result.is_valid)
        self.assertEqual(result.fields, ())

    def test_result_filters_by_field(self):
        result = CampaignValidationResult(
            (
                CampaignValidationIssue("a", "objective", "A"),
                CampaignValidationIssue("b", "owner", "B"),
            )
        )
        self.assertEqual(tuple(i.code for i in result.for_field("objective")), ("a",))

    def test_result_round_trip(self):
        original = CampaignValidationResult(
            (CampaignValidationIssue("a", "objective", "A"),)
        )
        self.assertEqual(
            CampaignValidationResult.from_dict(original.to_dict()), original
        )

    def test_planning_validation_accepts_complete_plan(self):
        self.assertTrue(
            CampaignPlanValidator().validate_for_planning(self.make_plan()).is_valid
        )

    def test_approval_validation_requires_rationale(self):
        result = CampaignPlanValidator().validate_for_approval(
            self.make_plan(objective=CampaignObjective("Increase qualified enquiries"))
        )
        self.assertEqual(result.for_field("objective")[0].code, "rationale_required")

    def test_approval_validation_requires_measurement_method(self):
        result = CampaignPlanValidator().validate_for_approval(
            self.make_plan(
                success_metrics=(CampaignMetric("Qualified enquiries", "25"),)
            )
        )
        self.assertEqual(
            result.for_field("success_metrics")[0].code, "measurement_method_required"
        )

    def test_validator_rejects_invalid_plan_type(self):
        with self.assertRaisesRegex(TypeError, "CampaignPlan"):
            CampaignPlanValidator().validate_for_planning(object())


if __name__ == "__main__":
    unittest.main()
