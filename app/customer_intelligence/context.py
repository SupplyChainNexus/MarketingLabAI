"""AI-ready Customer Intelligence context composition."""

from __future__ import annotations

from collections.abc import Sequence

from app.customer_intelligence.builders import (
    CustomerEvidenceBuilder,
    CustomerIntelligenceSectionBuilder,
    CustomerOverviewBuilder,
    CustomerPersonaBuilder,
    CustomerSegmentBuilder,
    IdealCustomerProfileBuilder,
)
from app.customer_intelligence.models import CustomerIntelligenceProfile


class CustomerContextBuilder:
    """Compose deterministic, reusable Customer Intelligence context."""

    def __init__(
        self,
        builders: Sequence[CustomerIntelligenceSectionBuilder] | None = None,
    ) -> None:
        selected_builders = (
            list(builders) if builders is not None else self._default_builders()
        )

        for builder in selected_builders:
            if not isinstance(
                builder,
                CustomerIntelligenceSectionBuilder,
            ):
                raise TypeError(
                    "builders must contain "
                    "CustomerIntelligenceSectionBuilder objects."
                )

            if not builder.title.strip():
                raise ValueError("customer intelligence builder title is required.")

        self.builders = tuple(selected_builders)

    @staticmethod
    def _default_builders() -> list[CustomerIntelligenceSectionBuilder]:
        """Return builders in deterministic composition order."""

        return [
            CustomerOverviewBuilder(),
            CustomerSegmentBuilder(),
            IdealCustomerProfileBuilder(),
            CustomerPersonaBuilder(),
            CustomerEvidenceBuilder(),
        ]

    def build(
        self,
        profile: CustomerIntelligenceProfile,
    ) -> str:
        """Return structured, AI-ready customer context."""

        if not isinstance(profile, CustomerIntelligenceProfile):
            raise TypeError("profile must be a CustomerIntelligenceProfile.")

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
