"""Tests for the Customer Intelligence context provider."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from app.customer_intelligence import (
    CustomerContextBuilder,
    CustomerIntelligenceProfile,
    CustomerPersona,
    CustomerSegment,
)
from app.customer_intelligence.provider import CustomerContextProvider
from app.database.connection import SQLiteDatabase
from app.database.repositories import (
    BrandRepository,
    CustomerIntelligenceRepository,
)


class CustomerContextProviderTests(unittest.TestCase):
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

    def test_provider_returns_empty_context_when_profile_is_absent(self) -> None:
        provider = CustomerContextProvider(repository=self.repository)

        self.assertEqual(provider.build("brand-one"), "")

    def test_provider_loads_and_builds_customer_context(self) -> None:
        self.repository.save(
            CustomerIntelligenceProfile(
                brand_id="brand-one",
                summary="Fleet customers value fast availability.",
                primary_segment_id="fleet",
                segments=[
                    CustomerSegment(
                        segment_id="fleet",
                        name="Fleet Operators",
                    )
                ],
                personas=[
                    CustomerPersona(
                        persona_id="fleet-manager",
                        name="Fleet Manager",
                        segment_id="fleet",
                        pain_points=["Vehicle downtime"],
                    )
                ],
            )
        )

        provider = CustomerContextProvider(repository=self.repository)

        context = provider.build("brand-one")

        self.assertIn(
            "- Summary: Fleet customers value fast availability.",
            context,
        )
        self.assertIn(
            "- Fleet Operators [fleet]",
            context,
        )
        self.assertIn(
            "- Pain points: Vehicle downtime",
            context,
        )

    def test_provider_rejects_blank_brand_id(self) -> None:
        provider = CustomerContextProvider(repository=self.repository)

        with self.assertRaisesRegex(ValueError, "brand_id is required"):
            provider.build(" ")

    def test_provider_rejects_invalid_repository(self) -> None:
        with self.assertRaisesRegex(
            TypeError,
            "CustomerIntelligenceRepository",
        ):
            CustomerContextProvider(
                repository=object(),  # type: ignore[arg-type]
            )

    def test_provider_rejects_invalid_context_builder(self) -> None:
        with self.assertRaisesRegex(
            TypeError,
            "CustomerContextBuilder",
        ):
            CustomerContextProvider(
                repository=self.repository,
                context_builder=object(),  # type: ignore[arg-type]
            )

    def test_provider_accepts_explicit_context_builder(self) -> None:
        provider = CustomerContextProvider(
            repository=self.repository,
            context_builder=CustomerContextBuilder(),
        )

        self.assertIsInstance(
            provider.context_builder,
            CustomerContextBuilder,
        )


if __name__ == "__main__":
    unittest.main()
