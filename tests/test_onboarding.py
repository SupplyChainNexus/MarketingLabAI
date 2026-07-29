"""Tests for the interactive onboarding workflow."""

import unittest
from unittest.mock import Mock

from app.workflows.onboarding import (
    collect_brand_profile,
    create_brand_id,
    parse_comma_separated,
    request_required_value,
    run_onboarding,
)


class OnboardingWorkflowTests(unittest.TestCase):
    def test_creates_safe_brand_id(self) -> None:
        self.assertEqual(
            create_brand_id("Nexus Auto Parts"),
            "nexus-auto-parts",
        )

    def test_removes_special_characters_from_brand_id(self) -> None:
        self.assertEqual(
            create_brand_id("Delight's Marketing & Media"),
            "delight-s-marketing-media",
        )

    def test_rejects_brand_name_without_valid_characters(self) -> None:
        with self.assertRaises(ValueError):
            create_brand_id("!!!")

    def test_parses_comma_separated_values(self) -> None:
        result = parse_comma_separated("Reliable, Affordable,  Fast Service, ")

        self.assertEqual(
            result,
            ["Reliable", "Affordable", "Fast Service"],
        )

    def test_required_value_retries_after_blank_answer(self) -> None:
        answers = iter(["", "   ", "Automotive"])
        messages: list[str] = []

        result = request_required_value(
            "Industry: ",
            input_function=lambda _: next(answers),
            output_function=messages.append,
        )

        self.assertEqual(result, "Automotive")
        self.assertEqual(len(messages), 2)

    def test_collects_complete_brand_profile(self) -> None:
        answers = iter(
            [
                "Nexus Auto Parts",
                "Automotive",
                "Supplier of replacement vehicle parts",
                "Panel beaters and vehicle owners",
                "Body panels, Lamps, Cooling parts",
                "Reliability, Service, Value",
                "https://example.com",
            ]
        )

        brand = collect_brand_profile(
            input_function=lambda _: next(answers),
            output_function=lambda _: None,
        )

        self.assertEqual(brand.brand_id, "nexus-auto-parts")
        self.assertEqual(brand.name, "Nexus Auto Parts")
        self.assertEqual(brand.industry, "Automotive")
        self.assertEqual(
            brand.products_or_services,
            ["Body panels", "Lamps", "Cooling parts"],
        )
        self.assertEqual(
            brand.values,
            ["Reliability", "Service", "Value"],
        )
        self.assertEqual(brand.website, "https://example.com")

    def test_run_onboarding_saves_brand(self) -> None:
        answers = iter(
            [
                "Nexus Auto Parts",
                "Automotive",
                "Replacement vehicle parts supplier",
                "Repair shops",
                "Body panels, Lamps",
                "Service, Reliability",
                "",
            ]
        )

        service = Mock()
        service.brand_exists.return_value = False
        messages: list[str] = []

        brand = run_onboarding(
            service=service,
            input_function=lambda _: next(answers),
            output_function=messages.append,
        )

        service.brand_exists.assert_called_once_with("nexus-auto-parts")
        service.save_brand.assert_called_once_with(brand)
        self.assertIn(
            "Brand onboarding completed successfully",
            messages,
        )

    def test_run_onboarding_rejects_duplicate_brand(self) -> None:
        answers = iter(
            [
                "Nexus Auto Parts",
                "Automotive",
                "Replacement vehicle parts supplier",
                "Repair shops",
                "Body panels",
                "",
                "",
            ]
        )

        service = Mock()
        service.brand_exists.return_value = True

        with self.assertRaisesRegex(
            ValueError,
            "already exists",
        ):
            run_onboarding(
                service=service,
                input_function=lambda _: next(answers),
                output_function=lambda _: None,
            )

        service.save_brand.assert_not_called()


if __name__ == "__main__":
    unittest.main()
