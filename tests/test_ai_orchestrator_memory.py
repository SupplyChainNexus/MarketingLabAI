"""Tests for memory-aware AI orchestration."""

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
    MemoryRepository,
)
from app.memory.models import MemoryEvent


class AIOrchestratorMemoryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.database = SQLiteDatabase(
            Path(self.temporary_directory.name) / "marketinglabai.db"
        )
        self.database.initialise()

        self.brands = BrandRepository(self.database)
        self.memory = MemoryRepository(self.database)

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

    def test_orchestrator_injects_memory_context(
        self,
    ) -> None:
        self.memory.save(
            MemoryEvent(
                memory_id="memory-one",
                brand_id="brand-one",
                event_type="campaign.performance",
                source="meta",
                summary=("Video ads outperformed static images."),
                created_at=("2026-08-01T10:00:00+00:00"),
            )
        )
        self.memory.save(
            MemoryEvent(
                memory_id="memory-two",
                brand_id="brand-one",
                event_type="customer.preference",
                source="research",
                summary=("Customers preferred educational content."),
                created_at=("2026-08-01T11:00:00+00:00"),
            )
        )

        orchestrator = AIOrchestrator(
            self.registry,
            context_assembler=AIContextAssembler(
                memory_repository=self.memory,
            ),
        )

        orchestrator.generate(
            tenant_id="default",
            brand_id="brand-one",
            task="Create a campaign",
        )

        request = self.provider.requests[0]

        self.assertIn(
            "Relevant Institutional Memory:",
            request.prompt,
        )
        self.assertIn(
            "Customers preferred educational content.",
            request.prompt,
        )
        self.assertIn(
            "Video ads outperformed static images.",
            request.prompt,
        )
        self.assertLess(
            request.prompt.index("Customers preferred educational content."),
            request.prompt.index("Video ads outperformed static images."),
        )
        self.assertLess(
            request.prompt.index("Relevant Institutional Memory:"),
            request.prompt.index("Task:"),
        )

        self.assertTrue(request.metadata["memory_included"])
        self.assertEqual(
            request.metadata["memory_count"],
            2,
        )

    def test_orchestrator_works_without_memory(
        self,
    ) -> None:
        orchestrator = AIOrchestrator(
            self.registry,
            context_assembler=AIContextAssembler(
                memory_repository=self.memory,
            ),
        )

        orchestrator.generate(
            tenant_id="default",
            brand_id="brand-one",
            task="Create a campaign",
        )

        request = self.provider.requests[0]

        self.assertNotIn(
            "Relevant Institutional Memory:",
            request.prompt,
        )
        self.assertEqual(
            request.prompt,
            "Task:\nCreate a campaign",
        )
        self.assertFalse(request.metadata["memory_included"])
        self.assertEqual(
            request.metadata["memory_count"],
            0,
        )

    def test_orchestrator_respects_memory_limit(
        self,
    ) -> None:
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

        orchestrator = AIOrchestrator(
            self.registry,
            context_assembler=AIContextAssembler(
                memory_repository=self.memory,
                memory_limit=2,
            ),
        )

        orchestrator.generate(
            tenant_id="default",
            brand_id="brand-one",
            task="Create a campaign",
        )

        request = self.provider.requests[0]

        self.assertIn(
            "Memory number 3.",
            request.prompt,
        )
        self.assertIn(
            "Memory number 2.",
            request.prompt,
        )
        self.assertNotIn(
            "Memory number 1.",
            request.prompt,
        )
        self.assertEqual(
            request.metadata["memory_count"],
            2,
        )

    def test_orchestrator_rejects_invalid_assembler(
        self,
    ) -> None:
        with self.assertRaisesRegex(
            TypeError,
            "AIContextAssembler",
        ):
            AIOrchestrator(
                self.registry,
                context_assembler=object(),
            )


if __name__ == "__main__":
    unittest.main()
