"""Operational intelligence rendering."""

from __future__ import annotations

from app.intelligence.builders.base import (
    IntelligenceSectionBuilder,
)
from app.intelligence.models import BusinessIntelligenceProfile


class OperationalIntelligenceBuilder(IntelligenceSectionBuilder):
    """Build operational capacity and delivery context."""

    title = "Operational Intelligence"

    _FIELDS = (
        ("sales_cycle_days", "Sales cycle days"),
        ("team_size", "Team size"),
        (
            "capacity_constraints",
            "Capacity constraints",
        ),
    )

    def build(
        self,
        profile: BusinessIntelligenceProfile,
    ) -> list[str]:
        return self.render_fields(
            profile,
            self._FIELDS,
        )
