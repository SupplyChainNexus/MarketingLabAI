"""Shared contracts for Company Brain intelligence builders."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from app.intelligence.models import BusinessIntelligenceProfile


class IntelligenceSectionBuilder(ABC):
    """Build one deterministic Company Brain intelligence section."""

    title: str

    @abstractmethod
    def build(
        self,
        profile: BusinessIntelligenceProfile,
    ) -> list[str]:
        """Return ordered lines for one intelligence section."""

    @staticmethod
    def require_profile(
        profile: BusinessIntelligenceProfile,
    ) -> None:
        """Validate the common builder input."""

        if not isinstance(
            profile,
            BusinessIntelligenceProfile,
        ):
            raise TypeError("profile must be a BusinessIntelligenceProfile.")

    @staticmethod
    def render_value(value: Any) -> str:
        """Render one profile value consistently."""

        if isinstance(value, list):
            return ", ".join(value)

        return str(value)

    @classmethod
    def render_fields(
        cls,
        profile: BusinessIntelligenceProfile,
        fields: tuple[tuple[str, str], ...],
    ) -> list[str]:
        """Render non-empty profile fields in declared order."""

        cls.require_profile(profile)

        lines: list[str] = []

        for field_name, label in fields:
            value = getattr(profile, field_name)

            if value in (None, "", []):
                continue

            lines.append(f"- {label}: {cls.render_value(value)}")

        return lines
