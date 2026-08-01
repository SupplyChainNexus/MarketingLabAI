"""Institutional memory prompt context for MarketingLabAI."""

from __future__ import annotations

from collections.abc import Sequence

from app.memory.models import MemoryEvent


class MemoryPromptBuilder:
    """Convert institutional memory events into concise prompt context."""

    def build(
        self,
        events: Sequence[MemoryEvent],
        *,
        limit: int = 10,
    ) -> str:
        """Return institutional memory content for prompt composition."""

        if isinstance(events, (str, bytes)) or not isinstance(
            events,
            Sequence,
        ):
            raise TypeError("events must be a sequence of MemoryEvent objects.")

        if limit < 1:
            raise ValueError("limit must be at least 1.")

        lines: list[str] = []
        seen_summaries: set[str] = set()

        for event in events:
            if not isinstance(event, MemoryEvent):
                raise TypeError("events must contain only MemoryEvent objects.")

            summary = event.summary.strip()
            summary_key = summary.casefold()

            if not summary or summary_key in seen_summaries:
                continue

            seen_summaries.add(summary_key)

            details = [
                event.event_type.strip(),
                event.source.strip(),
            ]
            label = " | ".join(detail for detail in details if detail)

            if label:
                lines.append(f"- [{label}] {summary}")
            else:
                lines.append(f"- {summary}")

            if len(lines) >= limit:
                break

        return "\n".join(lines)
