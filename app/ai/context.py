"""Prompt context builders for MarketingLabAI."""

from __future__ import annotations

from app.intelligence.models import BusinessIntelligenceProfile


class CompanyBrainPromptBuilder:
    """Convert Company Brain data into concise AI prompt context."""

    _FIELD_LABELS = (
        ("revenue_model", "Revenue model"),
        ("average_order_value", "Average order value"),
        ("gross_margin_percent", "Gross margin percent"),
        ("customer_lifetime_value", "Customer lifetime value"),
        ("customer_acquisition_cost", "Customer acquisition cost"),
        ("sales_cycle_days", "Sales cycle days"),
        ("monthly_marketing_budget", "Monthly marketing budget"),
        ("team_size", "Team size"),
        ("sales_channels", "Sales channels"),
        ("geographic_markets", "Geographic markets"),
        ("capacity_constraints", "Capacity constraints"),
        ("seasonality", "Seasonality"),
        ("competitors", "Competitors"),
        ("business_goals", "Business goals"),
    )

    def build(
        self,
        profile: BusinessIntelligenceProfile,
    ) -> str:
        """Return a structured Company Brain prompt section."""

        if not isinstance(
            profile,
            BusinessIntelligenceProfile,
        ):
            raise TypeError("profile must be a " "BusinessIntelligenceProfile.")

        lines = ["Company Context:"]

        for field_name, label in self._FIELD_LABELS:
            value = getattr(profile, field_name)

            if value in (None, "", []):
                continue

            if isinstance(value, list):
                rendered_value = ", ".join(value)
            else:
                rendered_value = str(value)

            lines.append(f"- {label}: {rendered_value}")

        if len(lines) == 1:
            return ""

        return "`n".join(lines)
