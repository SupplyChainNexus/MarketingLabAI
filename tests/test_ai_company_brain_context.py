"""Tests for Company Brain AI prompt context."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from app.ai.context import CompanyBrainPromptBuilder
from app.ai.orchestrator import AIOrchestrator
from app.ai.providers.mock import MockIntelligenceProvider
from app.ai.registry import IntelligenceProviderRegistry
from app.database.connection import SQLiteDatabase
from app.database.repositories import (
    BrandRepository,
    BusinessIntelligenceRepository,
)
from app.intelligence.models import (
    BusinessIntelligenceProfile,
)


class CompanyBrainPromptBuilderTests(unittest.TestCase):
    def test_builder_formats_available_profile_fields(
        self,
    ) -> None:
        profile = BusinessIntelligenceProfile(
            brand_id="brand-one",
            revenue_model="Retail sales",
            average_order_value=399.0,
            sales_channels=[
                "Website",
                "Takealot",
            ],
            geographic_markets=[
                "South Africa",
            ],
            business_goals=[
                "Increase repeat purchases",
            ],
        )

        context = CompanyBrainPromptBuilder().build(profile)

        self.assertIn(
            "Company Context:",
            context,
        )
        self.assertIn(
            "Revenue model: Retail sales",
            context,
        )
        self.assertIn(
            "Average order value: 399.0",
            context,
        )
        self.assertIn(
            "Sales channels: Website, Takealot",
            context,
        )
        self.assertIn(
            "Business goals: Increase repeat purchases",
            context,
        )

    def test_builder_omits_empty_fields(self) -> None:
        profile = BusinessIntelligenceProfile(
            brand_id="brand-one",
            revenue_model="Retail sales",
        )

        context = CompanyBrainPromptBuilder().build(profile)

        self.assertIn(
            "Revenue model: Retail sales",
            context,
        )
        self.assertNotIn(
            "Sales channels:",
            context,
        )


class AIOrchestratorCompanyBrainTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.database = SQLiteDatabase(
            Path(self.temporary_directory.name) / "marketinglabai.db"
        )
        self.database.initialise()

        self.brands = BrandRepository(self.database)
        self.intelligence = BusinessIntelligenceRepository(self.database)

        self.brands.save(
            {
                "brand_id": "brand-one",
                "name": "Brand One",
                "tenant_id": "default",
            }
        )

        self.registry = IntelligenceProviderRegistry()
        self.provider = MockIntelligenceProvider(
            response_content="Generated response",
            model="mock-model",
        )
        self.registry.register(self.provider)

    def tearDown(self) -> None:
        self.temporary_directory.cleanup()

    def test_orchestrator_injects_company_brain_context(
        self,
    ) -> None:
        self.intelligence.save(
            BusinessIntelligenceProfile(
                brand_id="brand-one",
                revenue_model="Retail sales",
                sales_channels=[
                    "Website",
                    "Retail store",
                ],
                business_goals=[
                    "Grow repeat purchases",
                ],
            )
        )

        orchestrator = AIOrchestrator(
            self.registry,
            intelligence_repository=self.intelligence,
        )

        orchestrator.generate(
            tenant_id="default",
            brand_id="brand-one",
            task="Create a retention campaign",
            instructions="Use a trustworthy tone.",
        )

        request = self.provider.requests[0]

        self.assertIn(
            "Company Context:",
            request.prompt,
        )
        self.assertIn(
            "Revenue model: Retail sales",
            request.prompt,
        )
        self.assertIn(
            "Sales channels: Website, Retail store",
            request.prompt,
        )
        self.assertIn(
            "Task:\nCreate a retention campaign",
            request.prompt,
        )
        self.assertTrue(request.metadata["company_brain_included"])

    def test_orchestrator_works_without_company_brain(
        self,
    ) -> None:
        orchestrator = AIOrchestrator(
            self.registry,
            intelligence_repository=self.intelligence,
        )

        orchestrator.generate(
            tenant_id="default",
            brand_id="brand-one",
            task="Create a campaign",
        )

        request = self.provider.requests[0]

        self.assertNotIn(
            "Company Context:",
            request.prompt,
        )
        self.assertEqual(
            request.prompt,
            "Task:\nCreate a campaign",
        )
        self.assertFalse(request.metadata["company_brain_included"])


if __name__ == "__main__":
    unittest.main()
