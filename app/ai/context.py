"""Prompt context builders for MarketingLabAI."""

from __future__ import annotations

from collections.abc import Sequence

from app.intelligence.builders import (
    CommercialIntelligenceBuilder,
    CompetitiveIntelligenceBuilder,
    GrowthIntelligenceBuilder,
    IntelligenceSectionBuilder,
    MarketIntelligenceBuilder,
    OperationalIntelligenceBuilder,
    StrategicObjectiveBuilder,
)
from app.intelligence.models import BusinessIntelligenceProfile


class CompanyBrainPromptBuilder:
    """Compose structured Company Brain intelligence context."""

    def __init__(
        self,
        builders: Sequence[IntelligenceSectionBuilder] | None = None,
    ) -> None:
        selected_builders = (
            list(builders) if builders is not None else self._default_builders()
        )

        for builder in selected_builders:
            if not isinstance(
                builder,
                IntelligenceSectionBuilder,
            ):
                raise TypeError(
                    "builders must contain " "IntelligenceSectionBuilder objects."
                )

            if not builder.title.strip():
                raise ValueError("intelligence builder title is required.")

        self.builders = tuple(selected_builders)

    @staticmethod
    def _default_builders() -> list[IntelligenceSectionBuilder]:
        """Return builders in deterministic composition order."""

        return [
            CommercialIntelligenceBuilder(),
            GrowthIntelligenceBuilder(),
            MarketIntelligenceBuilder(),
            OperationalIntelligenceBuilder(),
            CompetitiveIntelligenceBuilder(),
            StrategicObjectiveBuilder(),
        ]

    def build(
        self,
        profile: BusinessIntelligenceProfile,
    ) -> str:
        """Return structured Company Brain prompt context."""

        if not isinstance(
            profile,
            BusinessIntelligenceProfile,
        ):
            raise TypeError("profile must be a " "BusinessIntelligenceProfile.")

        sections: list[str] = []

        for builder in self.builders:
            lines = builder.build(profile)

            if not lines:
                continue

            sections.append(
                "\n".join(
                    [
                        f"{builder.title}:",
                        *lines,
                    ]
                )
            )

        return "\n\n".join(sections)
