"""Market intelligence rendering."""

from __future__ import annotations

from app.intelligence.builders.base import (
    IntelligenceSectionBuilder,
)
from app.intelligence.models import BusinessIntelligenceProfile


class MarketIntelligenceBuilder(IntelligenceSectionBuilder):
    """Build channel, market and seasonal context."""

    title = "Market Intelligence"

    _FIELDS = (
        ("sales_channels", "Sales channels"),
        ("geographic_markets", "Geographic markets"),
        ("seasonality", "Seasonality"),
    )

    def build(
        self,
        profile: BusinessIntelligenceProfile,
    ) -> list[str]:
        return self.render_fields(
            profile,
            self._FIELDS,
        )
