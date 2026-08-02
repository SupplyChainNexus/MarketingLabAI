"""Tests for AI provider requirements."""

from __future__ import annotations

import unittest

from app.ai.requirements import ProviderRequirements


class ProviderRequirementsTests(unittest.TestCase):
    def test_defaults_require_no_special_capabilities(
        self,
    ) -> None:
        requirements = ProviderRequirements()

        self.assertEqual(
            requirements.model,
            "",
        )
        self.assertFalse(requirements.requires_streaming)
        self.assertFalse(requirements.requires_tools)
        self.assertFalse(requirements.requires_structured_output)
        self.assertFalse(requirements.requires_image_input)
        self.assertFalse(requirements.requires_document_input)
        self.assertIsNone(requirements.minimum_context_tokens)
        self.assertEqual(
            requirements.metadata,
            {},
        )
        self.assertFalse(requirements.has_capability_requirements)

    def test_cleans_model_name(self) -> None:
        requirements = ProviderRequirements(model=" model-one ")

        self.assertEqual(
            requirements.model,
            "model-one",
        )

    def test_blank_model_becomes_empty_string(
        self,
    ) -> None:
        requirements = ProviderRequirements(model=" ")

        self.assertEqual(
            requirements.model,
            "",
        )

    def test_detects_capability_requirements(
        self,
    ) -> None:
        requirements = ProviderRequirements(requires_tools=True)

        self.assertTrue(requirements.has_capability_requirements)

    def test_context_requirement_counts_as_capability(
        self,
    ) -> None:
        requirements = ProviderRequirements(minimum_context_tokens=32_000)

        self.assertTrue(requirements.has_capability_requirements)

    def test_rejects_invalid_model_type(self) -> None:
        with self.assertRaisesRegex(
            TypeError,
            "model",
        ):
            ProviderRequirements(model=123)  # type: ignore[arg-type]

    def test_rejects_invalid_boolean(self) -> None:
        with self.assertRaisesRegex(
            TypeError,
            "requires_streaming",
        ):
            ProviderRequirements(requires_streaming=1)  # type: ignore[arg-type]

    def test_rejects_invalid_context_type(
        self,
    ) -> None:
        with self.assertRaisesRegex(
            TypeError,
            "minimum_context_tokens",
        ):
            ProviderRequirements(
                minimum_context_tokens=("large")  # type: ignore[arg-type]
            )

    def test_rejects_invalid_context_value(
        self,
    ) -> None:
        with self.assertRaisesRegex(
            ValueError,
            "at least 1",
        ):
            ProviderRequirements(minimum_context_tokens=0)

    def test_rejects_invalid_metadata(self) -> None:
        with self.assertRaisesRegex(
            TypeError,
            "metadata",
        ):
            ProviderRequirements(metadata=[])  # type: ignore[arg-type]

    def test_copies_metadata(self) -> None:
        metadata = {
            "task_type": "campaign",
        }

        requirements = ProviderRequirements(metadata=metadata)

        metadata["task_type"] = "changed"

        self.assertEqual(
            requirements.metadata,
            {
                "task_type": "campaign",
            },
        )

    def test_requirements_are_immutable(self) -> None:
        requirements = ProviderRequirements()

        with self.assertRaises(
            (AttributeError, TypeError),
        ):
            requirements.model = "changed"  # type: ignore[misc]

    def test_round_trip_dictionary_conversion(
        self,
    ) -> None:
        requirements = ProviderRequirements(
            model="model-one",
            requires_streaming=True,
            requires_tools=True,
            requires_structured_output=True,
            requires_image_input=True,
            requires_document_input=True,
            minimum_context_tokens=128_000,
            metadata={
                "task_type": "campaign",
            },
        )

        restored = ProviderRequirements.from_dict(requirements.to_dict())

        self.assertEqual(
            restored,
            requirements,
        )

    def test_to_dict_copies_metadata(self) -> None:
        requirements = ProviderRequirements(
            metadata={
                "task_type": "campaign",
            }
        )

        payload = requirements.to_dict()
        payload["metadata"]["task_type"] = "changed"

        self.assertEqual(
            requirements.metadata,
            {
                "task_type": "campaign",
            },
        )

    def test_from_dict_rejects_invalid_input(
        self,
    ) -> None:
        with self.assertRaisesRegex(
            TypeError,
            "dictionary",
        ):
            ProviderRequirements.from_dict([])  # type: ignore[arg-type]


if __name__ == "__main__":
    unittest.main()
