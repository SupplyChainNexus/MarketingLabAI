"""Integrated brand and Company Brain onboarding workflow."""

from __future__ import annotations

from collections.abc import Callable
from typing import TypeAlias

from app.brands.brand_service import BrandService
from app.intelligence.models import BusinessIntelligenceProfile
from app.intelligence.service import BusinessIntelligenceService
from app.workflows.onboarding import collect_brand_profile

InputFunction: TypeAlias = Callable[[str], str]
OutputFunction: TypeAlias = Callable[[str], None]


def parse_comma_separated(value: str) -> list[str]:
    """Convert a comma-separated answer into a clean list."""

    cleaned_values: list[str] = []

    for item in value.split(","):
        cleaned_item = item.strip()

        if cleaned_item and cleaned_item not in cleaned_values:
            cleaned_values.append(cleaned_item)

    return cleaned_values


def request_optional_float(
    prompt: str,
    *,
    minimum: float = 0,
    maximum: float | None = None,
    input_fn: InputFunction = input,
    output_fn: OutputFunction = print,
) -> float | None:
    """Request an optional numeric value and validate its range."""

    while True:
        raw_value = input_fn(prompt).strip()

        if not raw_value:
            return None

        normalised_value = raw_value.replace(" ", "").replace(",", "").replace("%", "")

        try:
            value = float(normalised_value)
        except ValueError:
            output_fn("Please enter a valid number or press Enter to skip.")
            continue

        if value < minimum:
            output_fn(f"The value cannot be lower than {minimum:g}.")
            continue

        if maximum is not None and value > maximum:
            output_fn(f"The value cannot be higher than {maximum:g}.")
            continue

        return value


def request_optional_integer(
    prompt: str,
    *,
    minimum: int = 0,
    input_fn: InputFunction = input,
    output_fn: OutputFunction = print,
) -> int | None:
    """Request an optional whole number."""

    while True:
        raw_value = input_fn(prompt).strip()

        if not raw_value:
            return None

        normalised_value = raw_value.replace(" ", "").replace(",", "")

        try:
            value = int(normalised_value)
        except ValueError:
            output_fn("Please enter a valid whole number or press Enter to skip.")
            continue

        if value < minimum:
            output_fn(f"The value cannot be lower than {minimum}.")
            continue

        return value


def request_yes_no(
    prompt: str,
    *,
    default: bool = True,
    input_fn: InputFunction = input,
    output_fn: OutputFunction = print,
) -> bool:
    """Request a yes-or-no answer."""

    while True:
        raw_value = input_fn(prompt).strip().lower()

        if not raw_value:
            return default

        if raw_value in {"y", "yes"}:
            return True

        if raw_value in {"n", "no"}:
            return False

        output_fn("Please answer Y or N.")


def collect_business_intelligence_profile(
    brand_id: str,
    *,
    input_fn: InputFunction = input,
    output_fn: OutputFunction = print,
) -> BusinessIntelligenceProfile:
    """Collect commercial and operational business context."""

    output_fn("")
    output_fn("MarketingLabAI Company Brain")
    output_fn("----------------------------")
    output_fn(
        "These questions help MarketingLabAI make commercially informed "
        "recommendations."
    )
    output_fn("Optional questions may be skipped by pressing Enter.")
    output_fn("")

    revenue_model = input_fn(
        "Revenue model, for example subscriptions, retail sales, or services: "
    ).strip()

    average_order_value = request_optional_float(
        "Average customer order or transaction value: ",
        input_fn=input_fn,
        output_fn=output_fn,
    )

    gross_margin_percent = request_optional_float(
        "Estimated gross margin percentage: ",
        maximum=100,
        input_fn=input_fn,
        output_fn=output_fn,
    )

    customer_lifetime_value = request_optional_float(
        "Estimated customer lifetime value: ",
        input_fn=input_fn,
        output_fn=output_fn,
    )

    customer_acquisition_cost = request_optional_float(
        "Estimated customer acquisition cost: ",
        input_fn=input_fn,
        output_fn=output_fn,
    )

    sales_cycle_days = request_optional_integer(
        "Typical number of days from first contact to sale: ",
        input_fn=input_fn,
        output_fn=output_fn,
    )

    monthly_marketing_budget = request_optional_float(
        "Monthly marketing budget in your operating currency: ",
        input_fn=input_fn,
        output_fn=output_fn,
    )

    team_size = request_optional_integer(
        "Number of people involved in sales and marketing: ",
        input_fn=input_fn,
        output_fn=output_fn,
    )

    sales_channels = parse_comma_separated(
        input_fn(
            "Sales channels, comma separated "
            "(website, retail, sales representatives, marketplaces): "
        )
    )

    geographic_markets = parse_comma_separated(
        input_fn("Geographic markets served, comma separated: ")
    )

    capacity_constraints = parse_comma_separated(
        input_fn(
            "Capacity constraints, comma separated "
            "(stock, staff, production, delivery, budget): "
        )
    )

    seasonality = parse_comma_separated(
        input_fn("Seasonal patterns or important trading periods, comma separated: ")
    )

    competitors = parse_comma_separated(
        input_fn("Known competitors, comma separated: ")
    )

    business_goals = parse_comma_separated(
        input_fn("Main business goals for the next 12 months, comma separated: ")
    )

    return BusinessIntelligenceProfile(
        brand_id=brand_id,
        revenue_model=revenue_model,
        average_order_value=average_order_value,
        gross_margin_percent=gross_margin_percent,
        customer_lifetime_value=customer_lifetime_value,
        customer_acquisition_cost=customer_acquisition_cost,
        sales_cycle_days=sales_cycle_days,
        monthly_marketing_budget=monthly_marketing_budget,
        team_size=team_size,
        sales_channels=sales_channels,
        geographic_markets=geographic_markets,
        capacity_constraints=capacity_constraints,
        seasonality=seasonality,
        competitors=competitors,
        business_goals=business_goals,
    )


def run_onboarding(
    *,
    brand_service: BrandService | None = None,
    intelligence_service: BusinessIntelligenceService | None = None,
    input_fn: InputFunction = input,
    output_fn: OutputFunction = print,
) -> None:
    """Onboard a brand and optionally create its Company Brain profile."""

    active_brand_service = brand_service or BrandService()
    active_intelligence_service = intelligence_service or BusinessIntelligenceService()

    profile = collect_brand_profile(
        input_fn=input_fn,
        output_fn=output_fn,
    )

    if active_brand_service.brand_exists(profile.brand_id):
        output_fn("")
        output_fn(f"A brand with ID '{profile.brand_id}' already exists.")
        output_fn("No information was overwritten.")
        return

    active_brand_service.save_brand(profile)

    output_fn("")
    output_fn("Brand onboarding completed successfully")
    output_fn(f"Brand ID: {profile.brand_id}")
    output_fn(f"Brand name: {profile.name}")

    should_create_company_brain = request_yes_no(
        "",
        default=True,
        input_fn=lambda _: input_fn(
            "Create the Company Brain business profile now? [Y/n]: "
        ),
        output_fn=output_fn,
    )

    if not should_create_company_brain:
        output_fn("")
        output_fn("Brand saved. The Company Brain profile can be completed later.")
        return

    intelligence_profile = collect_business_intelligence_profile(
        profile.brand_id,
        input_fn=input_fn,
        output_fn=output_fn,
    )

    active_intelligence_service.save_profile(intelligence_profile)

    output_fn("")
    output_fn("Company Brain profile completed successfully")
    output_fn(f"Linked brand ID: {profile.brand_id}")
    output_fn(
        "MarketingLabAI can now use this commercial context in future "
        "strategies and recommendations."
    )
