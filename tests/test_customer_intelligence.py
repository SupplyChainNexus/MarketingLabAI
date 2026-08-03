"""Tests for MarketingLabAI Customer Intelligence."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from app.customer_intelligence import (
    CustomerEvidence,
    CustomerIntelligenceProfile,
    CustomerIntelligenceService,
    CustomerPersona,
    CustomerSegment,
    IdealCustomerProfile,
)


class CustomerEvidenceTests(unittest.TestCase):
    def test_evidence_cleans_values(self) -> None:
        evidence = CustomerEvidence(
            source=" Customer interviews ",
            confidence=0.8,
            summary=" Repeated concern about downtime ",
        )

        self.assertEqual(evidence.source, "Customer interviews")
        self.assertEqual(evidence.summary, "Repeated concern about downtime")

    def test_evidence_rejects_invalid_confidence(self) -> None:
        with self.assertRaisesRegex(ValueError, "between 0 and 1"):
            CustomerEvidence(source="Research", confidence=1.1)

    def test_evidence_rejects_boolean_confidence(self) -> None:
        with self.assertRaisesRegex(TypeError, "confidence must be a number"):
            CustomerEvidence(source="Research", confidence=True)


class CustomerIntelligenceProfileTests(unittest.TestCase):
    def test_profile_requires_brand_id(self) -> None:
        with self.assertRaisesRegex(ValueError, "brand_id is required"):
            CustomerIntelligenceProfile(brand_id=" ")

    def test_profile_round_trip_preserves_nested_models(self) -> None:
        profile = self._build_profile()

        restored = CustomerIntelligenceProfile.from_dict(profile.to_dict())

        self.assertEqual(restored.to_dict(), profile.to_dict())
        self.assertIsInstance(restored.segments[0], CustomerSegment)
        self.assertIsInstance(restored.personas[0], CustomerPersona)
        self.assertIsInstance(
            restored.ideal_customer_profiles[0],
            IdealCustomerProfile,
        )

    def test_profile_rejects_duplicate_segment_ids(self) -> None:
        with self.assertRaisesRegex(ValueError, "segment_id values must be unique"):
            CustomerIntelligenceProfile(
                brand_id="brand-one",
                segments=[
                    CustomerSegment(segment_id="fleet", name="Fleet"),
                    CustomerSegment(segment_id="fleet", name="Fleet Two"),
                ],
            )

    def test_primary_segment_must_exist(self) -> None:
        with self.assertRaisesRegex(ValueError, "primary_segment_id"):
            CustomerIntelligenceProfile(
                brand_id="brand-one",
                primary_segment_id="missing",
            )

    def test_persona_must_reference_existing_segment(self) -> None:
        with self.assertRaisesRegex(ValueError, "unknown segment"):
            CustomerIntelligenceProfile(
                brand_id="brand-one",
                personas=[
                    CustomerPersona(
                        persona_id="fleet-manager",
                        name="Fleet Manager",
                        segment_id="missing",
                    )
                ],
            )

    def test_persona_cleans_and_deduplicates_insight_lists(self) -> None:
        persona = CustomerPersona(
            persona_id="taxi-owner",
            name="Taxi Owner",
            pain_points=[" Downtime ", "Downtime", ""],
            preferred_channels=[" WhatsApp ", "Facebook"],
        )

        self.assertEqual(persona.pain_points, ["Downtime"])
        self.assertEqual(persona.preferred_channels, ["WhatsApp", "Facebook"])

    @staticmethod
    def _build_profile() -> CustomerIntelligenceProfile:
        evidence = CustomerEvidence(
            source="Customer interviews",
            confidence=0.9,
            summary="Downtime is a major concern.",
            verified=True,
        )
        return CustomerIntelligenceProfile(
            brand_id="strand-auto-parts",
            summary="Customers prioritise availability and reliable parts.",
            primary_segment_id="fleet-operators",
            segments=[
                CustomerSegment(
                    segment_id="fleet-operators",
                    name="Fleet Operators",
                    characteristics=["Own multiple commercial vehicles"],
                    evidence=[evidence],
                )
            ],
            ideal_customer_profiles=[
                IdealCustomerProfile(
                    icp_id="regional-fleet",
                    name="Regional Fleet Business",
                    industries=["Transport"],
                    company_sizes=["10-100 vehicles"],
                    regions=["Western Cape"],
                    needs=["Fast parts availability"],
                    buying_criteria=["Quality", "Availability", "Price"],
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
                    decision_criteria=["Correct fitment", "Availability"],
                    preferred_channels=["WhatsApp", "Google"],
                    journey_stages=["Problem awareness", "Supplier comparison"],
                    language_terms=["Keep the vehicle on the road"],
                    trust_factors=["Technical knowledge"],
                    emotional_drivers=["Confidence"],
                    customer_questions=["Is it in stock?"],
                    evidence=[evidence],
                )
            ],
        )


class CustomerIntelligenceServiceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.service = CustomerIntelligenceService(Path(self.temporary_directory.name))

    def tearDown(self) -> None:
        self.temporary_directory.cleanup()

    def test_service_saves_and_loads_profile(self) -> None:
        profile = CustomerIntelligenceProfile(
            brand_id="brand-one",
            segments=[CustomerSegment(segment_id="retail", name="Retail")],
        )

        saved_path = self.service.save_profile(profile)
        loaded = self.service.get_profile("brand-one")

        self.assertTrue(saved_path.exists())
        self.assertEqual(loaded.to_dict(), profile.to_dict())

    def test_service_lists_brand_ids_in_sorted_order(self) -> None:
        self.service.save_profile(CustomerIntelligenceProfile(brand_id="zeta"))
        self.service.save_profile(CustomerIntelligenceProfile(brand_id="alpha"))

        self.assertEqual(self.service.list_brand_ids(), ["alpha", "zeta"])

    def test_service_deletes_profile(self) -> None:
        self.service.save_profile(CustomerIntelligenceProfile(brand_id="brand-one"))

        self.assertTrue(self.service.delete_profile("brand-one"))
        self.assertFalse(self.service.delete_profile("brand-one"))

    def test_service_raises_for_missing_profile(self) -> None:
        with self.assertRaisesRegex(FileNotFoundError, "customer intelligence"):
            self.service.get_profile("missing")

    def test_service_rejects_invalid_profile_type(self) -> None:
        with self.assertRaisesRegex(TypeError, "CustomerIntelligenceProfile"):
            self.service.save_profile(object())  # type: ignore[arg-type]

    def test_service_rejects_invalid_brand_path(self) -> None:
        with self.assertRaisesRegex(ValueError, "invalid path characters"):
            self.service.profile_exists("../unsafe")


if __name__ == "__main__":
    unittest.main()
