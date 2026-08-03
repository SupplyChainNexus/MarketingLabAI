"""Composable section builders for Customer Intelligence context."""

from __future__ import annotations

from abc import ABC, abstractmethod

from app.customer_intelligence.models import CustomerIntelligenceProfile


class CustomerIntelligenceSectionBuilder(ABC):
    """Build one deterministic section of customer context."""

    title: str

    @abstractmethod
    def build(self, profile: CustomerIntelligenceProfile) -> list[str]:
        """Return formatted lines for this section."""

    @staticmethod
    def require_profile(
        profile: CustomerIntelligenceProfile,
    ) -> CustomerIntelligenceProfile:
        """Validate and return a Customer Intelligence profile."""

        if not isinstance(profile, CustomerIntelligenceProfile):
            raise TypeError("profile must be a CustomerIntelligenceProfile.")

        return profile

    @staticmethod
    def bullet(label: str, values: list[str]) -> str | None:
        """Render a labelled comma-separated list when values exist."""

        if not values:
            return None

        return f"- {label}: {', '.join(values)}"
