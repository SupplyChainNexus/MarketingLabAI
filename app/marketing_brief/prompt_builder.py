"""Render structured Marketing Briefs into generic prompt sections."""

from __future__ import annotations

from collections.abc import Sequence

from app.ai.prompt import PromptSection
from app.marketing_brief.models import MarketingBrief


class MarketingBriefPromptBuilder:
    """Convert a Marketing Brief into deterministic prompt sections."""

    def build(
        self,
        brief: MarketingBrief,
    ) -> list[PromptSection]:
        """Return non-empty sections in deterministic order."""

        if not isinstance(brief, MarketingBrief):
            raise TypeError("brief must be a MarketingBrief.")

        sections = [
            self._overview_section(brief),
            self._audience_section(brief),
            self._offer_section(brief),
            self._execution_section(brief),
            self._constraints_section(brief),
            self._success_metrics_section(brief),
            self._evidence_section(brief),
            self._assumptions_section(brief),
            self._notes_section(brief),
        ]

        return [section for section in sections if section.render()]

    @staticmethod
    def _overview_section(
        brief: MarketingBrief,
    ) -> PromptSection:
        lines = [
            f"Brief: {brief.name}",
            f"Objective: {brief.objective}",
            f"Status: {brief.status.value}",
            f"Version: {brief.version}",
        ]

        return PromptSection(
            title="Marketing Brief",
            content="\n".join(lines),
        )

    @staticmethod
    def _audience_section(
        brief: MarketingBrief,
    ) -> PromptSection:
        lines = [f"Audience: {brief.audience}"]

        if brief.customer_segment_ids:
            lines.append(
                "Customer segment IDs: " + ", ".join(brief.customer_segment_ids)
            )

        return PromptSection(
            title="Audience",
            content="\n".join(lines),
        )

    @staticmethod
    def _offer_section(
        brief: MarketingBrief,
    ) -> PromptSection:
        lines: list[str] = []

        if brief.offer:
            lines.append(f"Offer: {brief.offer}")

        if brief.key_message:
            lines.append(f"Key message: {brief.key_message}")

        if brief.call_to_action:
            lines.append(f"Call to action: {brief.call_to_action}")

        if brief.product_ids:
            lines.append("Product IDs: " + ", ".join(brief.product_ids))

        return PromptSection(
            title="Offer and Message",
            content="\n".join(lines),
        )

    @staticmethod
    def _execution_section(
        brief: MarketingBrief,
    ) -> PromptSection:
        lines: list[str] = []

        if brief.channels:
            lines.append("Channels: " + ", ".join(brief.channels))

        if brief.deliverables:
            lines.append("Deliverables:")
            lines.extend(f"- {deliverable}" for deliverable in brief.deliverables)

        return PromptSection(
            title="Execution Requirements",
            content="\n".join(lines),
        )

    @staticmethod
    def _constraints_section(
        brief: MarketingBrief,
    ) -> PromptSection:
        return PromptSection(
            title="Constraints",
            content=MarketingBriefPromptBuilder._bullet_list(brief.constraints),
        )

    @staticmethod
    def _success_metrics_section(
        brief: MarketingBrief,
    ) -> PromptSection:
        return PromptSection(
            title="Success Metrics",
            content=MarketingBriefPromptBuilder._bullet_list(brief.success_metrics),
        )

    @staticmethod
    def _evidence_section(
        brief: MarketingBrief,
    ) -> PromptSection:
        lines: list[str] = []

        for evidence in brief.evidence:
            lines.append(
                "- "
                f"[{evidence.source_type}:{evidence.source_id}] "
                f"{evidence.summary} "
                f"(confidence: {evidence.confidence:.2f})"
            )

        return PromptSection(
            title="Supporting Evidence",
            content="\n".join(lines),
        )

    @staticmethod
    def _assumptions_section(
        brief: MarketingBrief,
    ) -> PromptSection:
        return PromptSection(
            title="Explicit Assumptions",
            content=MarketingBriefPromptBuilder._bullet_list(brief.assumptions),
        )

    @staticmethod
    def _notes_section(
        brief: MarketingBrief,
    ) -> PromptSection:
        return PromptSection(
            title="Additional Notes",
            content=brief.notes,
        )

    @staticmethod
    def _bullet_list(
        values: Sequence[str],
    ) -> str:
        return "\n".join(f"- {value}" for value in values)
