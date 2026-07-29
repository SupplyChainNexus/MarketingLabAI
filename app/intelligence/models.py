"""Business intelligence models for the MarketingLabAI Company Brain."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from typing import Any


def current_utc_timestamp() -> str:
    """Return an ISO-formatted UTC timestamp."""

    return datetime.now(UTC).isoformat()


@dataclass(slots=True)
class BusinessIntelligenceProfile:
    """Commercial and operational context linked to a brand."""

    brand_id: str
    revenue_model: str = ""
    average_order_value: float | None = None
    gross_margin_percent: float | None = None
    customer_lifetime_value: float | None = None
    customer_acquisition_cost: float | None = None
    sales_cycle_days: int | None = None
    monthly_marketing_budget: float | None = None
    team_size: int | None = None
    sales_channels: list[str] = field(default_factory=list)
    geographic_markets: list[str] = field(default_factory=list)
    capacity_constraints: list[str] = field(default_factory=list)
    seasonality: list[str] = field(default_factory=list)
    competitors: list[str] = field(default_factory=list)
    business_goals: list[str] = field(default_factory=list)
    updated_at: str = field(default_factory=current_utc_timestamp)

    def __post_init__(self) -> None:
        """Validate profile values after initialisation."""

        self.brand_id = self.brand_id.strip()

        if not self.brand_id:
            raise ValueError("brand_id is required.")

        self.revenue_model = self.revenue_model.strip()

        self._validate_non_negative_float(
            "average_order_value",
            self.average_order_value,
        )
        self._validate_non_negative_float(
            "customer_lifetime_value",
            self.customer_lifetime_value,
        )
        self._validate_non_negative_float(
            "customer_acquisition_cost",
            self.customer_acquisition_cost,
        )
        self._validate_non_negative_float(
            "monthly_marketing_budget",
            self.monthly_marketing_budget,
        )

        if self.gross_margin_percent is not None:
            if not 0 <= self.gross_margin_percent <= 100:
                raise ValueError("gross_margin_percent must be between 0 and 100.")

        self._validate_non_negative_integer(
            "sales_cycle_days",
            self.sales_cycle_days,
        )
        self._validate_non_negative_integer(
            "team_size",
            self.team_size,
        )

        self.sales_channels = self._clean_list(self.sales_channels)
        self.geographic_markets = self._clean_list(self.geographic_markets)
        self.capacity_constraints = self._clean_list(self.capacity_constraints)
        self.seasonality = self._clean_list(self.seasonality)
        self.competitors = self._clean_list(self.competitors)
        self.business_goals = self._clean_list(self.business_goals)

        if not self.updated_at.strip():
            self.updated_at = current_utc_timestamp()

    @staticmethod
    def _validate_non_negative_float(
        field_name: str,
        value: float | None,
    ) -> None:
        if value is not None and value < 0:
            raise ValueError(f"{field_name} cannot be negative.")

    @staticmethod
    def _validate_non_negative_integer(
        field_name: str,
        value: int | None,
    ) -> None:
        if value is not None and value < 0:
            raise ValueError(f"{field_name} cannot be negative.")

    @staticmethod
    def _clean_list(values: list[str]) -> list[str]:
        cleaned_values: list[str] = []

        for value in values:
            cleaned_value = value.strip()

            if cleaned_value and cleaned_value not in cleaned_values:
                cleaned_values.append(cleaned_value)

        return cleaned_values

    def to_dict(self) -> dict[str, Any]:
        """Convert the profile into a JSON-serialisable dictionary."""

        return asdict(self)

    @classmethod
    def from_dict(
        cls,
        data: dict[str, Any],
    ) -> BusinessIntelligenceProfile:
        """Create a profile from stored dictionary data."""

        return cls(**data)
