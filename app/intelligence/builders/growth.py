"""Deterministic growth-intelligence calculations."""

from __future__ import annotations

from app.intelligence.builders.base import (
    IntelligenceSectionBuilder,
)
from app.intelligence.models import BusinessIntelligenceProfile


class GrowthIntelligenceBuilder(IntelligenceSectionBuilder):
    """Build derived commercial metrics from verified inputs."""

    title = "Derived Growth Intelligence"

    def build(
        self,
        profile: BusinessIntelligenceProfile,
    ) -> list[str]:
        self.require_profile(profile)

        lines: list[str] = []

        lifetime_value = profile.customer_lifetime_value
        acquisition_cost = profile.customer_acquisition_cost

        if (
            lifetime_value is not None
            and acquisition_cost is not None
            and acquisition_cost > 0
        ):
            ratio = lifetime_value / acquisition_cost

            lines.append(
                "- Customer lifetime value to acquisition " f"cost ratio: {ratio:.2f}"
            )

        order_value = profile.average_order_value
        margin_percent = profile.gross_margin_percent

        gross_profit_per_order: float | None = None

        if order_value is not None and margin_percent is not None:
            gross_profit_per_order = order_value * margin_percent / 100

            lines.append(
                "- Estimated gross profit per order: " f"{gross_profit_per_order:.2f}"
            )

        if (
            acquisition_cost is not None
            and gross_profit_per_order is not None
            and gross_profit_per_order > 0
        ):
            payback_orders = acquisition_cost / gross_profit_per_order

            lines.append(
                "- Estimated acquisition-cost payback "
                f"in orders: {payback_orders:.2f}"
            )

        return lines
