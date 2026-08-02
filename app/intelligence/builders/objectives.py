"""Strategic objective rendering."""

from __future__ import annotations

from app.intelligence.builders.base import (
    IntelligenceSectionBuilder,
)
from app.intelligence.models import BusinessIntelligenceProfile


class StrategicObjectiveBuilder(IntelligenceSectionBuilder):
    """Build declared business objectives."""

    title = "Strategic Objectives"

    _FIELDS = (("business_goals", "Business goals"),)

    def build(
        self,
        profile: BusinessIntelligenceProfile,
    ) -> list[str]:
        return self.render_fields(
            profile,
            self._FIELDS,
        )
