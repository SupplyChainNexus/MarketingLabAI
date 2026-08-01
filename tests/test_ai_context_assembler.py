"""Tests for AI context assembly."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from app.ai.assembler import AIContext, AIContextAssembler
from app.database.connection import SQLiteDatabase
from app.database.repositories import (
    BrandRepository,
    BusinessIntelligenceRepository,
    MemoryRepository,
)
from app.intelligence.models import BusinessIntelligenceProfile
from app.memory.models import MemoryEvent


class AIContextTests(unittest.TestCase):
    def test_context_reports_available_sections(self) -> None:
        context = AIContext(
            company_context="- Revenue model: Retail",
            memory_context="- A useful memory.",
            memory_count=1,
        )

        self.assertTrue(context.company_brain_included)
        self.assertTrue(context.memory_included)
        self.assertEqual(context.memory_count, 1)

    def test_empty_context_reports_no_sections(self) -> None:
        context = AIContext()

        self.assertFalse(context.company_brain_included)
        self.assertFalse(context.memory_included)
        self.assertEqual(context.memory_count, 0)


class AIContextAssemblerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.database = SQLiteDatabase(
            Path(self.temporary_directory.name) / "marketinglabai.db"
        )
        self.database.initialise()

        self.brands = BrandRepository(self.database)
        self.intelligence = BusinessIntelligenceRepository(self.database)
        self.memory = MemoryRepository(self.database)

        self.brands.save(
            {
                "brand_id": "brand-one",
                "name": "Brand One",
                "tenant_id": "default",
            }
        )

    def tearDown(self) -> None:
        self.temporary_directory.cleanup()

    def test_assembler_returns_empty_optional_context(
        self,
    ) -> None:
        assembler = AIContextAssembler()

        context = assembler.build(
            brand_id="brand-one",
        )

        self.assertEqual(context, AIContext())

    def test_assembler_loads_company_brain_context(
        self,
    ) -> None:
        self.intelligence.save(
            BusinessIntelligenceProfile(
                brand_id="brand-one",
                revenue_model="Retail sales",
                business_goals=[
                    "Increase repeat purchases",
                ],
            )
        )

        assembler = AIContextAssembler(
            intelligence_repository=self.intelligence,
        )

        context = assembler.build(
            brand_id="brand-one",
        )

        self.assertTrue(context.company_brain_included)
        self.assertIn(
            "- Revenue model: Retail sales",
            context.company_context,
        )
        self.assertIn(
            "- Business goals: Increase repeat purchases",
            context.company_context,
        )
        self.assertFalse(context.memory_included)

    def test_assembler_loads_institutional_memory(
        self,
    ) -> None:
        self.memory.save(
            MemoryEvent(
                memory_id="memory-one",
                brand_id="brand-one",
                event_type="campaign.performance",
                source="meta",
                summary="Video ads outperformed static images.",
                created_at="2026-08-01T10:00:00+00:00",
            )
        )
        self.memory.save(
            MemoryEvent(
                memory_id="memory-two",
                brand_id="brand-one",
                event_type="customer.preference",
                source="research",
                summary="Customers preferred educational content.",
                created_at="2026-08-01T11:00:00+00:00",
            )
        )

        assembler = AIContextAssembler(
            memory_repository=self.memory,
        )

        context = assembler.build(
            brand_id="brand-one",
        )

        self.assertTrue(context.memory_included)
        self.assertEqual(context.memory_count, 2)
        self.assertLess(
            context.memory_context.index("Customers preferred educational content."),
            context.memory_context.index("Video ads outperformed static images."),
        )

    def test_assembler_combines_company_and_memory_context(
        self,
    ) -> None:
        self.intelligence.save(
            BusinessIntelligenceProfile(
                brand_id="brand-one",
                revenue_model="Subscription",
            )
        )
        self.memory.save(
            MemoryEvent(
                memory_id="memory-one",
                brand_id="brand-one",
                event_type="campaign.performance",
                source="analytics",
                summary="Educational posts delivered the best CTR.",
            )
        )

        assembler = AIContextAssembler(
            intelligence_repository=self.intelligence,
            memory_repository=self.memory,
        )

        context = assembler.build(
            brand_id="brand-one",
        )

        self.assertTrue(context.company_brain_included)
        self.assertTrue(context.memory_included)
        self.assertEqual(context.memory_count, 1)

    def test_assembler_respects_memory_limit(self) -> None:
        for index in range(1, 4):
            self.memory.save(
                MemoryEvent(
                    memory_id=f"memory-{index}",
                    brand_id="brand-one",
                    event_type="campaign.performance",
                    source="analytics",
                    summary=f"Memory number {index}.",
                    created_at=(f"2026-08-01T1{index}:00:00+00:00"),
                )
            )

        assembler = AIContextAssembler(
            memory_repository=self.memory,
            memory_limit=2,
        )

        context = assembler.build(
            brand_id="brand-one",
        )

        self.assertEqual(context.memory_count, 2)
        self.assertIn("Memory number 3.", context.memory_context)
        self.assertIn("Memory number 2.", context.memory_context)
        self.assertNotIn("Memory number 1.", context.memory_context)

    def test_assembler_rejects_blank_brand(self) -> None:
        assembler = AIContextAssembler()

        with self.assertRaisesRegex(
            ValueError,
            "brand_id",
        ):
            assembler.build(
                brand_id=" ",
            )

    def test_assembler_rejects_invalid_memory_limit(
        self,
    ) -> None:
        with self.assertRaisesRegex(
            ValueError,
            "memory_limit",
        ):
            AIContextAssembler(
                memory_limit=0,
            )


if __name__ == "__main__":
    unittest.main()
