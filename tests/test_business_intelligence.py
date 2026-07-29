"""Tests for the MarketingLabAI Business Intelligence Profile."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from app.intelligence.models import BusinessIntelligenceProfile
from app.intelligence.service import BusinessIntelligenceService


class BusinessIntelligenceProfileTests(unittest.TestCase):
    def test_profile_requires_brand_id(self) -> None:
        with self.assertRaisesRegex(ValueError, "brand_id is required"):
            BusinessIntelligenceProfile(brand_id="  ")

    def test_profile_rejects_negative_financial_values(self) -> None:
        with self.assertRaisesRegex(
            ValueError,
            "monthly_marketing_budget cannot be negative",
        ):
            BusinessIntelligenceProfile(
                brand_id="test-brand",
                monthly_marketing_budget=-1,
            )

    def test_profile_rejects_invalid_margin(self) -> None:
        with self.assertRaisesRegex(
            ValueError,
            "gross_margin_percent must be between 0 and 100",
        ):
            BusinessIntelligenceProfile(
                brand_id="test-brand",
                gross_margin_percent=101,
            )

    def test_profile_cleans_and_deduplicates_lists(self) -> None:
        profile = BusinessIntelligenceProfile(
            brand_id="test-brand",
            sales_channels=[
                " Website ",
                "",
                "Website",
                "Retail",
            ],
        )

        self.assertEqual(
            profile.sales_channels,
            ["Website", "Retail"],
        )

    def test_profile_round_trip_dictionary_conversion(self) -> None:
        profile = self._build_profile()

        restored_profile = BusinessIntelligenceProfile.from_dict(profile.to_dict())

        self.assertEqual(restored_profile.to_dict(), profile.to_dict())

    @staticmethod
    def _build_profile() -> BusinessIntelligenceProfile:
        return BusinessIntelligenceProfile(
            brand_id="marketinglabai-demo",
            revenue_model="Monthly SaaS subscriptions",
            average_order_value=99.0,
            gross_margin_percent=80.0,
            customer_lifetime_value=1200.0,
            customer_acquisition_cost=150.0,
            sales_cycle_days=14,
            monthly_marketing_budget=5000.0,
            team_size=3,
            sales_channels=["Website", "Direct sales"],
            geographic_markets=["South Africa"],
            capacity_constraints=["Limited development capacity"],
            seasonality=["Annual planning season"],
            competitors=["Competitor A", "Competitor B"],
            business_goals=[
                "Acquire paying customers",
                "Improve customer retention",
            ],
        )


class BusinessIntelligenceServiceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.storage_path = Path(self.temporary_directory.name)
        self.service = BusinessIntelligenceService(self.storage_path)

    def tearDown(self) -> None:
        self.temporary_directory.cleanup()

    def test_service_saves_and_loads_profile(self) -> None:
        profile = self._build_profile()

        saved_path = self.service.save_profile(profile)
        loaded_profile = self.service.get_profile(profile.brand_id)

        self.assertTrue(saved_path.exists())
        self.assertEqual(
            loaded_profile.brand_id,
            "marketinglabai-demo",
        )
        self.assertEqual(
            loaded_profile.revenue_model,
            "Monthly SaaS subscriptions",
        )

    def test_service_reports_profile_existence(self) -> None:
        profile = self._build_profile()

        self.assertFalse(self.service.profile_exists(profile.brand_id))

        self.service.save_profile(profile)

        self.assertTrue(self.service.profile_exists(profile.brand_id))

    def test_service_lists_brand_ids_in_sorted_order(self) -> None:
        self.service.save_profile(BusinessIntelligenceProfile(brand_id="zeta-brand"))
        self.service.save_profile(BusinessIntelligenceProfile(brand_id="alpha-brand"))

        self.assertEqual(
            self.service.list_brand_ids(),
            ["alpha-brand", "zeta-brand"],
        )

    def test_service_overwrites_existing_profile(self) -> None:
        profile = self._build_profile()
        self.service.save_profile(profile)

        profile.revenue_model = "Usage-based SaaS"
        self.service.save_profile(profile)

        loaded_profile = self.service.get_profile(profile.brand_id)

        self.assertEqual(
            loaded_profile.revenue_model,
            "Usage-based SaaS",
        )

    def test_service_raises_for_missing_profile(self) -> None:
        with self.assertRaisesRegex(
            FileNotFoundError,
            "No business intelligence profile exists",
        ):
            self.service.get_profile("missing-brand")

    def test_service_deletes_existing_profile(self) -> None:
        profile = self._build_profile()
        self.service.save_profile(profile)

        first_result = self.service.delete_profile(profile.brand_id)
        second_result = self.service.delete_profile(profile.brand_id)

        self.assertTrue(first_result)
        self.assertFalse(second_result)
        self.assertFalse(self.service.profile_exists(profile.brand_id))

    def test_service_rejects_invalid_brand_path(self) -> None:
        with self.assertRaisesRegex(
            ValueError,
            "invalid path characters",
        ):
            self.service.profile_exists("../unsafe-brand")

    @staticmethod
    def _build_profile() -> BusinessIntelligenceProfile:
        return BusinessIntelligenceProfile(
            brand_id="marketinglabai-demo",
            revenue_model="Monthly SaaS subscriptions",
            monthly_marketing_budget=5000.0,
            sales_channels=["Website"],
            geographic_markets=["South Africa"],
            business_goals=["Acquire paying customers"],
        )


if __name__ == "__main__":
    unittest.main()
