"""Tests for integrated Company Brain onboarding."""

from __future__ import annotations

import unittest
from unittest.mock import Mock, patch

from app.intelligence.models import BusinessIntelligenceProfile
from app.workflows.company_brain_onboarding import (
    collect_business_intelligence_profile,
    parse_comma_separated,
    request_optional_float,
    request_optional_integer,
    request_yes_no,
    run_onboarding,
)


class CompanyBrainInputTests(unittest.TestCase):
    def test_parse_comma_separated_cleans_and_deduplicates(self) -> None:
        result = parse_comma_separated("Website, Retail, Website, , Direct sales")

        self.assertEqual(
            result,
            ["Website", "Retail", "Direct sales"],
        )

    def test_optional_float_allows_blank_value(self) -> None:
        result = request_optional_float(
            "Value: ",
            input_fn=lambda _: "",
        )

        self.assertIsNone(result)

    def test_optional_float_accepts_formatted_number(self) -> None:
        result = request_optional_float(
            "Value: ",
            input_fn=lambda _: "5,000.50",
        )

        self.assertEqual(result, 5000.50)

    def test_optional_float_retries_invalid_value(self) -> None:
        answers = iter(["invalid", "42.5"])
        messages: list[str] = []

        result = request_optional_float(
            "Value: ",
            input_fn=lambda _: next(answers),
            output_fn=messages.append,
        )

        self.assertEqual(result, 42.5)
        self.assertTrue(messages)

    def test_optional_float_enforces_maximum(self) -> None:
        answers = iter(["101", "80"])

        result = request_optional_float(
            "Margin: ",
            maximum=100,
            input_fn=lambda _: next(answers),
            output_fn=lambda _: None,
        )

        self.assertEqual(result, 80)

    def test_optional_integer_accepts_whole_number(self) -> None:
        result = request_optional_integer(
            "Team size: ",
            input_fn=lambda _: "12",
        )

        self.assertEqual(result, 12)

    def test_yes_no_uses_default_for_blank_answer(self) -> None:
        self.assertTrue(
            request_yes_no(
                "Continue: ",
                default=True,
                input_fn=lambda _: "",
            )
        )

    def test_yes_no_retries_invalid_answer(self) -> None:
        answers = iter(["maybe", "n"])

        result = request_yes_no(
            "Continue: ",
            input_fn=lambda _: next(answers),
            output_fn=lambda _: None,
        )

        self.assertFalse(result)


class CompanyBrainCollectionTests(unittest.TestCase):
    def test_collects_complete_business_intelligence_profile(self) -> None:
        answers = iter(
            [
                "Monthly SaaS subscriptions",
                "999",
                "80",
                "5000",
                "250",
                "14",
                "10000",
                "4",
                "Website, Direct sales",
                "South Africa, United Kingdom",
                "Development capacity, Marketing budget",
                "January planning season",
                "Jasper, HubSpot",
                "Acquire 100 customers, Reach profitability",
            ]
        )

        profile = collect_business_intelligence_profile(
            "marketinglabai-demo",
            input_fn=lambda _: next(answers),
            output_fn=lambda _: None,
        )

        self.assertIsInstance(profile, BusinessIntelligenceProfile)
        self.assertEqual(profile.brand_id, "marketinglabai-demo")
        self.assertEqual(
            profile.revenue_model,
            "Monthly SaaS subscriptions",
        )
        self.assertEqual(profile.average_order_value, 999)
        self.assertEqual(profile.gross_margin_percent, 80)
        self.assertEqual(profile.sales_cycle_days, 14)
        self.assertEqual(
            profile.sales_channels,
            ["Website", "Direct sales"],
        )
        self.assertEqual(
            profile.business_goals,
            ["Acquire 100 customers", "Reach profitability"],
        )


class IntegratedOnboardingTests(unittest.TestCase):
    @patch(
        "app.workflows.company_brain_onboarding."
        "collect_business_intelligence_profile"
    )
    @patch("app.workflows.company_brain_onboarding.collect_brand_profile")
    def test_run_onboarding_saves_brand_and_company_brain(
        self,
        mocked_collect_brand,
        mocked_collect_intelligence,
    ) -> None:
        brand_profile = Mock()
        brand_profile.brand_id = "test-brand"
        brand_profile.name = "Test Brand"

        intelligence_profile = BusinessIntelligenceProfile(
            brand_id="test-brand",
            revenue_model="Services",
        )

        mocked_collect_brand.return_value = brand_profile
        mocked_collect_intelligence.return_value = intelligence_profile

        brand_service = Mock()
        brand_service.brand_exists.return_value = False

        intelligence_service = Mock()

        run_onboarding(
            brand_service=brand_service,
            intelligence_service=intelligence_service,
            input_fn=lambda _: "y",
            output_fn=lambda _: None,
        )

        brand_service.save_brand.assert_called_once_with(brand_profile)
        intelligence_service.save_profile.assert_called_once_with(intelligence_profile)

    @patch("app.workflows.company_brain_onboarding.collect_brand_profile")
    def test_run_onboarding_does_not_overwrite_duplicate_brand(
        self,
        mocked_collect_brand,
    ) -> None:
        brand_profile = Mock()
        brand_profile.brand_id = "existing-brand"
        brand_profile.name = "Existing Brand"
        mocked_collect_brand.return_value = brand_profile

        brand_service = Mock()
        brand_service.brand_exists.return_value = True

        intelligence_service = Mock()

        run_onboarding(
            brand_service=brand_service,
            intelligence_service=intelligence_service,
            input_fn=lambda _: "y",
            output_fn=lambda _: None,
        )

        brand_service.save_brand.assert_not_called()
        intelligence_service.save_profile.assert_not_called()

    @patch("app.workflows.company_brain_onboarding.collect_brand_profile")
    def test_run_onboarding_allows_company_brain_to_be_skipped(
        self,
        mocked_collect_brand,
    ) -> None:
        brand_profile = Mock()
        brand_profile.brand_id = "test-brand"
        brand_profile.name = "Test Brand"
        mocked_collect_brand.return_value = brand_profile

        brand_service = Mock()
        brand_service.brand_exists.return_value = False

        intelligence_service = Mock()

        run_onboarding(
            brand_service=brand_service,
            intelligence_service=intelligence_service,
            input_fn=lambda _: "n",
            output_fn=lambda _: None,
        )

        brand_service.save_brand.assert_called_once_with(brand_profile)
        intelligence_service.save_profile.assert_not_called()


if __name__ == "__main__":
    unittest.main()
