"""SQLite repository tests for Customer Intelligence."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from app.customer_intelligence import (
    CustomerEvidence,
    CustomerIntelligenceProfile,
    CustomerPersona,
    CustomerSegment,
    IdealCustomerProfile,
)
from app.database.connection import SQLiteDatabase
from app.database.repositories import (
    BrandRepository,
    CustomerIntelligenceRepository,
)


class CustomerIntelligenceRepositoryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.database = SQLiteDatabase(
            Path(self.temporary_directory.name) / "marketinglabai.db"
        )
        self.database.initialise()
        self.brands = BrandRepository(self.database)
        self.repository = CustomerIntelligenceRepository(self.database)

        self.brands.save(
            {
                "brand_id": "brand-one",
                "name": "Brand One",
                "tenant_id": "default",
            }
        )

    def tearDown(self) -> None:
        self.temporary_directory.cleanup()

    def test_repository_round_trip_preserves_nested_profile(self) -> None:
        profile = self._build_profile()

        self.repository.save(profile)
        restored = self.repository.get(profile.brand_id)

        self.assertTrue(self.repository.exists(profile.brand_id))
        self.assertEqual(restored.to_dict(), profile.to_dict())
        self.assertIsInstance(restored.segments[0], CustomerSegment)
        self.assertIsInstance(restored.personas[0], CustomerPersona)
        self.assertIsInstance(
            restored.ideal_customer_profiles[0],
            IdealCustomerProfile,
        )

    def test_repository_updates_existing_profile(self) -> None:
        profile = self._build_profile()
        self.repository.save(profile)

        profile.summary = "Updated customer intelligence summary."
        self.repository.save(profile)

        self.assertEqual(self.repository.count(), 1)
        self.assertEqual(
            self.repository.get("brand-one").summary,
            "Updated customer intelligence summary.",
        )

    def test_repository_lists_brand_ids_in_sorted_order(self) -> None:
        self.brands.save(
            {
                "brand_id": "alpha-brand",
                "name": "Alpha Brand",
                "tenant_id": "default",
            }
        )

        self.repository.save(CustomerIntelligenceProfile(brand_id="brand-one"))
        self.repository.save(CustomerIntelligenceProfile(brand_id="alpha-brand"))

        self.assertEqual(
            self.repository.list_brand_ids(),
            ["alpha-brand", "brand-one"],
        )

    def test_repository_requires_customer_intelligence_profile(self) -> None:
        with self.assertRaisesRegex(
            TypeError,
            "CustomerIntelligenceProfile",
        ):
            self.repository.save(object())  # type: ignore[arg-type]

    def test_repository_raises_for_missing_profile(self) -> None:
        with self.assertRaisesRegex(
            FileNotFoundError,
            "customer intelligence profile",
        ):
            self.repository.get("missing-brand")

    def test_brand_delete_cascades_to_customer_intelligence(self) -> None:
        self.repository.save(self._build_profile())

        with self.database.transaction() as connection:
            connection.execute(
                "DELETE FROM brands WHERE brand_id = ?",
                ("brand-one",),
            )

        self.assertFalse(self.repository.exists("brand-one"))

    @staticmethod
    def _build_profile() -> CustomerIntelligenceProfile:
        evidence = CustomerEvidence(
            source="Customer interviews",
            confidence=0.9,
            summary="Vehicle downtime is a major concern.",
            verified=True,
        )

        return CustomerIntelligenceProfile(
            brand_id="brand-one",
            summary="Fleet customers prioritise availability and quality.",
            primary_segment_id="fleet-operators",
            segments=[
                CustomerSegment(
                    segment_id="fleet-operators",
                    name="Fleet Operators",
                    characteristics=["Operate multiple commercial vehicles"],
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
                    customer_questions=["Is it in stock?"],
                    evidence=[evidence],
                )
            ],
        )


if __name__ == "__main__":
    unittest.main()
