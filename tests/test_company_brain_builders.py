"""Tests for composable Company Brain intelligence builders."""

from __future__ import annotations

import unittest
from typing import cast

from app.ai.context import CompanyBrainPromptBuilder
from app.intelligence.builders import (
    CommercialIntelligenceBuilder,
    CompetitiveIntelligenceBuilder,
    GrowthIntelligenceBuilder,
    IntelligenceSectionBuilder,
    MarketIntelligenceBuilder,
    OperationalIntelligenceBuilder,
    StrategicObjectiveBuilder,
)
from app.intelligence.models import BusinessIntelligenceProfile


class CompanyBrainBuilderTests(unittest.TestCase):
    def setUp(self) -> None:
        self.profile = BusinessIntelligenceProfile(
            brand_id="brand-one",
            revenue_model="Retail sales",
            average_order_value=400,
            gross_margin_percent=50,
            customer_lifetime_value=1200,
            customer_acquisition_cost=100,
            sales_cycle_days=7,
            monthly_marketing_budget=5000,
            team_size=4,
            sales_channels=[
                "Website",
                "Retail store",
            ],
            geographic_markets=[
                "South Africa",
            ],
            capacity_constraints=[
                "Limited delivery capacity",
            ],
            seasonality=[
                "December peak",
            ],
            competitors=[
                "Competitor One",
            ],
            business_goals=[
                "Increase repeat purchases",
            ],
        )

    def test_commercial_builder_renders_verified_fields(
        self,
    ) -> None:
        lines = CommercialIntelligenceBuilder().build(self.profile)

        self.assertIn(
            "- Revenue model: Retail sales",
            lines,
        )
        self.assertIn(
            "- Average order value: 400",
            lines,
        )
        self.assertIn(
            "- Monthly marketing budget: 5000",
            lines,
        )

    def test_market_builder_renders_market_context(
        self,
    ) -> None:
        lines = MarketIntelligenceBuilder().build(self.profile)

        self.assertIn(
            "- Sales channels: Website, Retail store",
            lines,
        )
        self.assertIn(
            "- Geographic markets: South Africa",
            lines,
        )
        self.assertIn(
            "- Seasonality: December peak",
            lines,
        )

    def test_operational_builder_renders_capacity(
        self,
    ) -> None:
        lines = OperationalIntelligenceBuilder().build(self.profile)

        self.assertIn(
            "- Sales cycle days: 7",
            lines,
        )
        self.assertIn(
            "- Team size: 4",
            lines,
        )
        self.assertIn(
            "- Capacity constraints: " "Limited delivery capacity",
            lines,
        )

    def test_competition_builder_renders_competitors(
        self,
    ) -> None:
        lines = CompetitiveIntelligenceBuilder().build(self.profile)

        self.assertEqual(
            lines,
            [
                "- Known competitors: Competitor One",
            ],
        )

    def test_objective_builder_renders_goals(
        self,
    ) -> None:
        lines = StrategicObjectiveBuilder().build(self.profile)

        self.assertEqual(
            lines,
            [
                "- Business goals: " "Increase repeat purchases",
            ],
        )

    def test_growth_builder_derives_verified_metrics(
        self,
    ) -> None:
        lines = GrowthIntelligenceBuilder().build(self.profile)

        self.assertEqual(
            lines,
            [
                "- Customer lifetime value to " "acquisition cost ratio: 12.00",
                "- Estimated gross profit per order: " "200.00",
                "- Estimated acquisition-cost payback " "in orders: 0.50",
            ],
        )

    def test_growth_builder_omits_unavailable_metrics(
        self,
    ) -> None:
        profile = BusinessIntelligenceProfile(
            brand_id="brand-one",
        )

        self.assertEqual(
            GrowthIntelligenceBuilder().build(profile),
            [],
        )

    def test_prompt_builder_composes_sections_in_order(
        self,
    ) -> None:
        context = CompanyBrainPromptBuilder().build(self.profile)

        self.assertLess(
            context.index("Commercial Intelligence:"),
            context.index("Derived Growth Intelligence:"),
        )
        self.assertLess(
            context.index("Derived Growth Intelligence:"),
            context.index("Market Intelligence:"),
        )
        self.assertLess(
            context.index("Market Intelligence:"),
            context.index("Operational Intelligence:"),
        )
        self.assertLess(
            context.index("Operational Intelligence:"),
            context.index("Competitive Intelligence:"),
        )
        self.assertLess(
            context.index("Competitive Intelligence:"),
            context.index("Strategic Objectives:"),
        )

    def test_prompt_builder_omits_empty_sections(
        self,
    ) -> None:
        profile = BusinessIntelligenceProfile(
            brand_id="brand-one",
            revenue_model="Services",
        )

        context = CompanyBrainPromptBuilder().build(profile)

        self.assertIn(
            "Commercial Intelligence:",
            context,
        )
        self.assertNotIn(
            "Market Intelligence:",
            context,
        )
        self.assertNotIn(
            "Operational Intelligence:",
            context,
        )
        self.assertNotIn(
            "Strategic Objectives:",
            context,
        )

    def test_prompt_builder_accepts_custom_builders(
        self,
    ) -> None:
        builder = CompanyBrainPromptBuilder(
            builders=[
                StrategicObjectiveBuilder(),
            ]
        )

        context = builder.build(self.profile)

        self.assertIn(
            "Strategic Objectives:",
            context,
        )
        self.assertNotIn(
            "Commercial Intelligence:",
            context,
        )

    def test_prompt_builder_rejects_invalid_builder(
        self,
    ) -> None:
        invalid_builder = cast(
            IntelligenceSectionBuilder,
            object(),
        )

        with self.assertRaisesRegex(
            TypeError,
            "IntelligenceSectionBuilder",
        ):
            CompanyBrainPromptBuilder(builders=[invalid_builder])

    def test_builder_rejects_invalid_profile(
        self,
    ) -> None:
        invalid_profile = cast(
            BusinessIntelligenceProfile,
            object(),
        )

        with self.assertRaisesRegex(
            TypeError,
            "BusinessIntelligenceProfile",
        ):
            CommercialIntelligenceBuilder().build(invalid_profile)


if __name__ == "__main__":
    unittest.main()
