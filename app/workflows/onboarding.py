"""Interactive business onboarding workflow."""

import re
from collections.abc import Callable

from app.brands.brand_service import BrandService
from app.models import BrandProfile

InputFunction = Callable[[str], str]
OutputFunction = Callable[[str], None]


def create_brand_id(name: str) -> str:
    """Create a safe, predictable brand ID from a business name."""

    normalized = name.strip().lower()
    normalized = re.sub(r"[^a-z0-9]+", "-", normalized)
    normalized = normalized.strip("-")

    if not normalized:
        raise ValueError("A valid business name is required.")

    return normalized


def parse_comma_separated(value: str) -> list[str]:
    """Convert comma-separated text into a clean list."""

    return [item.strip() for item in value.split(",") if item.strip()]


def request_required_value(
    prompt: str,
    *,
    input_function: InputFunction = input,
    output_function: OutputFunction = print,
) -> str:
    """Request a required value until the user provides one."""

    while True:
        value = input_function(prompt).strip()

        if value:
            return value

        output_function("This field is required. Please try again.")


def collect_brand_profile(
    *,
    input_function: InputFunction = input,
    output_function: OutputFunction = print,
) -> BrandProfile:
    """Collect onboarding answers and create a brand profile."""

    output_function("")
    output_function("MarketingLabAI Business Onboarding")
    output_function("----------------------------------")

    name = request_required_value(
        "Business name: ",
        input_function=input_function,
        output_function=output_function,
    )

    industry = request_required_value(
        "Industry: ",
        input_function=input_function,
        output_function=output_function,
    )

    description = request_required_value(
        "Describe the business: ",
        input_function=input_function,
        output_function=output_function,
    )

    target_audience = request_required_value(
        "Target audience: ",
        input_function=input_function,
        output_function=output_function,
    )

    products_value = request_required_value(
        "Products or services (comma separated): ",
        input_function=input_function,
        output_function=output_function,
    )

    values_value = input_function("Core values (comma separated, optional): ").strip()

    website = input_function("Website (optional): ").strip()

    return BrandProfile(
        brand_id=create_brand_id(name),
        name=name,
        industry=industry,
        description=description,
        target_audience=target_audience,
        products_or_services=parse_comma_separated(products_value),
        values=parse_comma_separated(values_value),
        website=website,
    )


def run_onboarding(
    *,
    service: BrandService | None = None,
    input_function: InputFunction = input,
    output_function: OutputFunction = print,
) -> BrandProfile:
    """Run onboarding and save the resulting brand profile."""

    brand_service = service or BrandService()

    brand = collect_brand_profile(
        input_function=input_function,
        output_function=output_function,
    )

    if brand_service.brand_exists(brand.brand_id):
        raise ValueError(f"A brand with ID '{brand.brand_id}' already exists.")

    brand_service.save_brand(brand)

    output_function("")
    output_function("Brand onboarding completed successfully")
    output_function(f"Brand ID: {brand.brand_id}")
    output_function(f"Brand name: {brand.name}")

    return brand
