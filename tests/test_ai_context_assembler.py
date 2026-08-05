"""Tests for AI context assembly."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from app.ai.assembler import AIContext, AIContextAssembler
from app.customer_intelligence import (
    CustomerIntelligenceProfile,
    CustomerPersona,
    CustomerSegment,
)
from app.customer_intelligence.provider import CustomerContextProvider
from app.database.connection import SQLiteDatabase
from app.database.repositories import (
    BrandRepository,
    BusinessIntelligenceRepository,
    CustomerIntelligenceRepository,
    MemoryRepository,
)
from app.intelligence.models import BusinessIntelligenceProfile
from app.memory.models import MemoryEvent
from app.product_intelligence import (
    ProductContextProvider,
    ProductEvidence,
    ProductIntelligenceProfile,
    ProductIntelligenceRepository,
    ProductRecord,
    ProductType,
)


class AIContextTests(unittest.TestCase):
    def test_context_reports_available_sections(self) -> None:
        context = AIContext(
            company_context="- Revenue model: Retail",
            memory_context="- A useful memory.",
            memory_count=1,
            customer_context="- Pain points: Vehicle downtime",
            product_context="Name: Priority sourcing",
        )

        self.assertTrue(context.company_brain_included)
        self.assertTrue(context.customer_intelligence_included)
        self.assertTrue(context.memory_included)
        self.assertTrue(context.product_intelligence_included)
        self.assertEqual(context.memory_count, 1)

    def test_empty_context_reports_no_sections(self) -> None:
        context = AIContext()

        self.assertFalse(context.company_brain_included)
        self.assertFalse(context.customer_intelligence_included)
        self.assertFalse(context.memory_included)
        self.assertFalse(context.product_intelligence_included)
        self.assertEqual(context.memory_count, 0)

    def test_existing_positional_arguments_remain_compatible(self) -> None:
        context = AIContext(
            "- Revenue model: Retail",
            "- A useful memory.",
            1,
        )

        self.assertEqual(
            context.company_context,
            "- Revenue model: Retail",
        )
        self.assertEqual(
            context.memory_context,
            "- A useful memory.",
        )
        self.assertEqual(context.memory_count, 1)
        self.assertEqual(context.customer_context, "")


class AIContextAssemblerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.database = SQLiteDatabase(
            Path(self.temporary_directory.name) / "marketinglabai.db"
        )
        self.database.initialise()

        self.brands = BrandRepository(self.database)
        self.intelligence = BusinessIntelligenceRepository(self.database)
        self.customers = CustomerIntelligenceRepository(self.database)
        self.products = ProductIntelligenceRepository(self.database)
        self.memory = MemoryRepository(self.database)
        self.customer_provider = CustomerContextProvider(
            repository=self.customers,
        )
        self.product_provider = ProductContextProvider(self.products)

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
        self.assertFalse(context.customer_intelligence_included)
        self.assertFalse(context.memory_included)

    def test_assembler_returns_empty_customer_context_when_absent(
        self,
    ) -> None:
        assembler = AIContextAssembler(
            customer_context_provider=self.customer_provider,
        )

        context = assembler.build(
            brand_id="brand-one",
        )

        self.assertFalse(context.customer_intelligence_included)
        self.assertEqual(context.customer_context, "")

    def test_assembler_loads_customer_intelligence_context(
        self,
    ) -> None:
        self.customers.save(
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
                        preferred_channels=["WhatsApp"],
                    )
                ],
            )
        )

        assembler = AIContextAssembler(
            customer_context_provider=self.customer_provider,
        )

        context = assembler.build(
            brand_id="brand-one",
        )

        self.assertTrue(context.customer_intelligence_included)
        self.assertIn(
            "- Summary: Fleet customers value fast availability.",
            context.customer_context,
        )
        self.assertIn(
            "- Pain points: Vehicle downtime",
            context.customer_context,
        )
        self.assertIn(
            "- Preferred channels: WhatsApp",
            context.customer_context,
        )
        self.assertFalse(context.company_brain_included)
        self.assertFalse(context.memory_included)

    def test_assembler_loads_tenant_scoped_product_context(self) -> None:
        self.products.save(
            ProductIntelligenceProfile(
                tenant_id="default",
                brand_id="brand-one",
                products=[
                    ProductRecord(
                        "service-one",
                        "Priority sourcing",
                        ProductType.SERVICE,
                        evidence=[ProductEvidence("Synthetic catalogue")],
                    )
                ],
            )
        )
        assembler = AIContextAssembler(
            product_context_provider=self.product_provider,
        )

        context = assembler.build(tenant_id="default", brand_id="brand-one")

        self.assertTrue(context.product_intelligence_included)
        self.assertIn("Name: Priority sourcing", context.product_context)
        self.assertIn("Price: Unknown", context.product_context)

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

    def test_assembler_combines_all_available_context(
        self,
    ) -> None:
        self.intelligence.save(
            BusinessIntelligenceProfile(
                brand_id="brand-one",
                revenue_model="Subscription",
            )
        )
        self.customers.save(
            CustomerIntelligenceProfile(
                brand_id="brand-one",
                summary="Fleet managers prioritise uptime.",
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
            customer_context_provider=self.customer_provider,
            memory_repository=self.memory,
        )

        context = assembler.build(
            brand_id="brand-one",
        )

        self.assertTrue(context.company_brain_included)
        self.assertTrue(context.customer_intelligence_included)
        self.assertTrue(context.memory_included)
        self.assertEqual(context.memory_count, 1)
        self.assertIn(
            "- Revenue model: Subscription",
            context.company_context,
        )
        self.assertIn(
            "- Summary: Fleet managers prioritise uptime.",
            context.customer_context,
        )
        self.assertIn(
            "Educational posts delivered the best CTR.",
            context.memory_context,
        )

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

    def test_assembler_rejects_non_string_brand(self) -> None:
        assembler = AIContextAssembler()

        with self.assertRaisesRegex(
            TypeError,
            "brand_id must be a string",
        ):
            assembler.build(
                brand_id=123,  # type: ignore[arg-type]
            )

    def test_assembler_rejects_invalid_customer_provider(
        self,
    ) -> None:
        with self.assertRaisesRegex(
            TypeError,
            "CustomerContextProvider",
        ):
            AIContextAssembler(
                customer_context_provider=object(),  # type: ignore[arg-type]
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
