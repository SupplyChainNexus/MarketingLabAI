"""Commercial intelligence rendering."""

from __future__ import annotations

from app.intelligence.builders.base import (
    IntelligenceSectionBuilder,
)
from app.intelligence.models import BusinessIntelligenceProfile


class CommercialIntelligenceBuilder(IntelligenceSectionBuilder):
    """Build commercial and financial business context."""

    title = "Commercial Intelligence"

    _FIELDS = (
        ("revenue_model", "Revenue model"),
        ("average_order_value", "Average order value"),
        ("gross_margin_percent", "Gross margin percent"),
        (
            "customer_lifetime_value",
            "Customer lifetime value",
        ),
        (
            "customer_acquisition_cost",
            "Customer acquisition cost",
        ),
        (
            "monthly_marketing_budget",
            "Monthly marketing budget",
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
