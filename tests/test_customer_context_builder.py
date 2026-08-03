"""Tests for Customer Intelligence context composition."""

from __future__ import annotations

import unittest

from app.customer_intelligence import (
    CustomerContextBuilder,
    CustomerEvidence,
    CustomerIntelligenceProfile,
    CustomerPersona,
    CustomerSegment,
    IdealCustomerProfile,
)
from app.customer_intelligence.builders import (
    CustomerIntelligenceSectionBuilder,
)


class CustomerContextBuilderTests(unittest.TestCase):
    def test_builder_composes_customer_context_in_order(self) -> None:
        context = CustomerContextBuilder().build(self._build_profile())

        headings = [
            "Customer Overview:",
            "Customer Segments:",
            "Ideal Customer Profiles:",
            "Customer Personas:",
            "Customer Evidence:",
        ]

        positions = [context.index(heading) for heading in headings]
        self.assertEqual(positions, sorted(positions))

        self.assertIn(
            "- Summary: Fleet customers prioritise availability.",
            context,
        )
        self.assertIn(
            "- Fleet Operators [fleet-operators]",
            context,
        )
        self.assertIn(
            "- Regional Fleet [regional-fleet]",
            context,
        )
        self.assertIn(
            "- Fleet Manager [fleet-manager]",
            context,
        )
        self.assertIn(
            "- Pain points: Vehicle downtime",
            context,
        )
        self.assertIn(
            "- Preferred channels: WhatsApp, Google",
            context,
        )
        self.assertIn(
            "confidence: 0.90; verified",
            context,
        )

    def test_builder_omits_empty_sections(self) -> None:
        context = CustomerContextBuilder().build(
            CustomerIntelligenceProfile(brand_id="brand-one")
        )

        self.assertEqual(context, "")

    def test_builder_rejects_invalid_profile(self) -> None:
        with self.assertRaisesRegex(
            TypeError,
            "CustomerIntelligenceProfile",
        ):
            CustomerContextBuilder().build(object())  # type: ignore[arg-type]

    def test_builder_rejects_invalid_section_builder(self) -> None:
        with self.assertRaisesRegex(
            TypeError,
            "CustomerIntelligenceSectionBuilder",
        ):
            CustomerContextBuilder(
                builders=[object()],  # type: ignore[list-item]
            )

    def test_builder_supports_custom_sections(self) -> None:
        context = CustomerContextBuilder(
            builders=[CustomCustomerSectionBuilder()]
        ).build(
            CustomerIntelligenceProfile(
                brand_id="brand-one",
                summary="Known customers.",
            )
        )

        self.assertEqual(
            context,
            "Custom Customer Context:\n- Known customers.",
        )

    def test_evidence_is_deduplicated(self) -> None:
        evidence = CustomerEvidence(
            source="Interviews",
            confidence=0.8,
            summary="Downtime matters.",
            verified=True,
        )
        profile = CustomerIntelligenceProfile(
            brand_id="brand-one",
            segments=[
                CustomerSegment(
                    segment_id="fleet",
                    name="Fleet",
                    evidence=[evidence],
                )
            ],
            personas=[
                CustomerPersona(
                    persona_id="manager",
                    name="Manager",
                    segment_id="fleet",
                    evidence=[evidence],
                )
            ],
        )

        context = CustomerContextBuilder().build(profile)

        self.assertEqual(
            context.count("Downtime matters."),
            1,
        )

    @staticmethod
    def _build_profile() -> CustomerIntelligenceProfile:
        evidence = CustomerEvidence(
            source="Customer interviews",
            confidence=0.9,
            summary="Downtime reduces fleet revenue.",
            verified=True,
            observed_at="2026-08-01",
        )

        return CustomerIntelligenceProfile(
            brand_id="brand-one",
            summary="Fleet customers prioritise availability.",
            primary_segment_id="fleet-operators",
            segments=[
                CustomerSegment(
                    segment_id="fleet-operators",
                    name="Fleet Operators",
                    description="Businesses operating vehicle fleets.",
                    characteristics=["Multiple commercial vehicles"],
                    evidence=[evidence],
                )
            ],
            ideal_customer_profiles=[
                IdealCustomerProfile(
                    icp_id="regional-fleet",
                    name="Regional Fleet",
                    industries=["Transport"],
                    company_sizes=["10-100 vehicles"],
                    regions=["Western Cape"],
                    needs=["Fast parts availability"],
                    buying_criteria=["Quality", "Availability"],
                    evidence=[evidence],
                )
            ],
            personas=[
                CustomerPersona(
                    persona_id="fleet-manager",
                    name="Fleet Manager",
                    segment_id="fleet-operators",
                    role="Maintenance decision-maker",
                    pain_points=["Vehicle downtime"],
                    desired_outcomes=["Keep vehicles operating"],
                    motivations=["Protect fleet revenue"],
                    buying_triggers=["Vehicle failure"],
                    objections=["Uncertain product quality"],
                    decision_criteria=["Correct fitment"],
                    preferred_channels=["WhatsApp", "Google"],
                    journey_stages=["Supplier comparison"],
                    language_terms=["Keep it on the road"],
                    trust_factors=["Technical knowledge"],
                    emotional_drivers=["Confidence"],
                    customer_questions=["Is it in stock?"],
                    evidence=[evidence],
                )
            ],
        )


class CustomCustomerSectionBuilder(CustomerIntelligenceSectionBuilder):
    title = "Custom Customer Context"

    def build(
        self,
        profile: CustomerIntelligenceProfile,
    ) -> list[str]:
        profile = self.require_profile(profile)

        if not profile.summary:
            return []

        return [f"- {profile.summary}"]


if __name__ == "__main__":
    unittest.main()
