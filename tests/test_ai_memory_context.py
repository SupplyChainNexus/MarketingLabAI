"""Tests for institutional memory prompt context."""

from __future__ import annotations

import unittest

from app.ai.memory import MemoryPromptBuilder
from app.memory.models import MemoryEvent


def create_memory(
    *,
    memory_id: str,
    summary: str,
    event_type: str = "campaign.performance",
    source: str = "analytics",
    created_at: str = "2026-08-01T12:00:00+00:00",
) -> MemoryEvent:
    """Create a memory event for testing."""

    return MemoryEvent(
        memory_id=memory_id,
        brand_id="brand-one",
        event_type=event_type,
        source=source,
        summary=summary,
        created_at=created_at,
    )


class MemoryPromptBuilderTests(unittest.TestCase):
    def setUp(self) -> None:
        self.builder = MemoryPromptBuilder()

    def test_builder_formats_memory_events(self) -> None:
        events = [
            create_memory(
                memory_id="memory-one",
                summary="Video ads outperformed static images.",
                event_type="campaign.performance",
                source="meta",
            ),
            create_memory(
                memory_id="memory-two",
                summary="Customers preferred educational content.",
                event_type="customer.preference",
                source="research",
            ),
        ]

        context = self.builder.build(events)

        self.assertEqual(
            context,
            (
                "- [campaign.performance | meta] "
                "Video ads outperformed static images.\n"
                "- [customer.preference | research] "
                "Customers preferred educational content."
            ),
        )

    def test_builder_preserves_input_order(self) -> None:
        events = [
            create_memory(
                memory_id="newest",
                summary="Newest memory.",
            ),
            create_memory(
                memory_id="older",
                summary="Older memory.",
            ),
        ]

        context = self.builder.build(events)

        self.assertLess(
            context.index("Newest memory."),
            context.index("Older memory."),
        )

    def test_builder_removes_duplicate_summaries(self) -> None:
        events = [
            create_memory(
                memory_id="memory-one",
                summary="Video performed best.",
            ),
            create_memory(
                memory_id="memory-two",
                summary="video performed best.",
                source="manual-review",
            ),
        ]

        context = self.builder.build(events)

        self.assertEqual(
            context.count("performed best."),
            1,
        )

    def test_builder_respects_limit(self) -> None:
        events = [
            create_memory(
                memory_id=f"memory-{index}",
                summary=f"Memory number {index}.",
            )
            for index in range(1, 6)
        ]

        context = self.builder.build(
            events,
            limit=2,
        )

        self.assertIn("Memory number 1.", context)
        self.assertIn("Memory number 2.", context)
        self.assertNotIn("Memory number 3.", context)

    def test_builder_returns_blank_for_empty_sequence(
        self,
    ) -> None:
        self.assertEqual(
            self.builder.build([]),
            "",
        )

    def test_builder_rejects_invalid_limit(self) -> None:
        with self.assertRaisesRegex(
            ValueError,
            "limit",
        ):
            self.builder.build(
                [],
                limit=0,
            )

    def test_builder_rejects_non_sequence(self) -> None:
        with self.assertRaisesRegex(
            TypeError,
            "sequence",
        ):
            self.builder.build(  # type: ignore[arg-type]
                object(),
            )

    def test_builder_rejects_invalid_event(self) -> None:
        with self.assertRaisesRegex(
            TypeError,
            "MemoryEvent",
        ):
            self.builder.build(  # type: ignore[list-item]
                [object()],
            )

    def test_builder_does_not_add_section_heading(
        self,
    ) -> None:
        context = self.builder.build(
            [
                create_memory(
                    memory_id="memory-one",
                    summary="A useful memory.",
                )
            ]
        )

        self.assertNotIn(
            "Relevant Institutional Memory:",
            context,
        )


if __name__ == "__main__":
    unittest.main()
