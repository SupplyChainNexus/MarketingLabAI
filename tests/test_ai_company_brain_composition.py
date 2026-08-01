"""Regression tests for composed Company Brain prompts."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from app.ai.assembler import AIContextAssembler
from app.ai.orchestrator import AIOrchestrator
from app.ai.providers.mock import MockIntelligenceProvider
from app.ai.registry import IntelligenceProviderRegistry
from app.database.connection import SQLiteDatabase
from app.database.repositories import (
    BrandRepository,
    BusinessIntelligenceRepository,
)
from app.intelligence.models import BusinessIntelligenceProfile


class CompanyBrainCompositionTests(unittest.TestCase):
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

        self.intelligence.save(
            BusinessIntelligenceProfile(
                brand_id="brand-one",
                revenue_model="Retail sales",
            )
        )

        self.registry = IntelligenceProviderRegistry()
        self.provider = MockIntelligenceProvider(
            response_content="Generated response",
            model="mock-model",
        )
        self.registry.register(self.provider)

    def tearDown(self) -> None:
        self.temporary_directory.cleanup()

    def test_company_context_heading_occurs_once(
        self,
    ) -> None:
        orchestrator = AIOrchestrator(
            self.registry,
            context_assembler=AIContextAssembler(
                intelligence_repository=self.intelligence,
            ),
        )

        orchestrator.generate(
            tenant_id="default",
            brand_id="brand-one",
            task="Create a campaign",
        )

        prompt = self.provider.requests[0].prompt

        self.assertEqual(
            prompt.count("Company Context:"),
            1,
        )
        self.assertEqual(
            prompt,
            (
                "Company Context:\n"
                "- Revenue model: Retail sales\n\n"
                "Task:\n"
                "Create a campaign"
            ),
        )


if __name__ == "__main__":
    unittest.main()
