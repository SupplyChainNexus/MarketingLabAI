"""Competitive intelligence rendering."""

from __future__ import annotations

from app.intelligence.builders.base import (
    IntelligenceSectionBuilder,
)
from app.intelligence.models import BusinessIntelligenceProfile


class CompetitiveIntelligenceBuilder(IntelligenceSectionBuilder):
    """Build known competitor context."""

    title = "Competitive Intelligence"

    _FIELDS = (("competitors", "Known competitors"),)

    def build(
        self,
        profile: BusinessIntelligenceProfile,
    ) -> list[str]:
        return self.render_fields(
            profile,
            self._FIELDS,
        )
