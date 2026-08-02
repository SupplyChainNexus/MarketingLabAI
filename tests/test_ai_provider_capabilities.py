"""Tests for AI provider capability declarations."""

from __future__ import annotations

import unittest

from app.ai.capabilities import ProviderCapabilities


class ProviderCapabilitiesTests(unittest.TestCase):
    def test_defaults_are_conservative(self) -> None:
        capabilities = ProviderCapabilities()

        self.assertFalse(capabilities.supports_structured_output)
        self.assertFalse(capabilities.supports_streaming)
        self.assertFalse(capabilities.supports_tools)
        self.assertFalse(capabilities.supports_images)
        self.assertFalse(capabilities.supports_documents)
        self.assertIsNone(capabilities.maximum_context_tokens)
        self.assertEqual(
            capabilities.available_models,
            [],
        )
        self.assertEqual(
            capabilities.metadata,
            {},
        )

    def test_cleans_and_deduplicates_models(
        self,
    ) -> None:
        capabilities = ProviderCapabilities(
            available_models=[
                " model-one ",
                "MODEL-ONE",
                "",
                "model-two",
            ]
        )

        self.assertEqual(
            capabilities.available_models,
            [
                "model-one",
                "model-two",
            ],
        )

    def test_supports_model_is_case_insensitive(
        self,
    ) -> None:
        capabilities = ProviderCapabilities(
            available_models=[
                "model-one",
            ]
        )

        self.assertTrue(capabilities.supports_model(" MODEL-ONE "))
        self.assertFalse(capabilities.supports_model("model-two"))

    def test_supports_model_rejects_blank_name(
        self,
    ) -> None:
        capabilities = ProviderCapabilities()

        with self.assertRaisesRegex(
            ValueError,
            "model",
        ):
            capabilities.supports_model(" ")

    def test_supports_model_rejects_invalid_type(
        self,
    ) -> None:
        capabilities = ProviderCapabilities()

        with self.assertRaisesRegex(
            TypeError,
            "string",
        ):
            capabilities.supports_model(123)  # type: ignore[arg-type]

    def test_rejects_non_boolean_capability(
        self,
    ) -> None:
        with self.assertRaisesRegex(
            TypeError,
            "supports_streaming",
        ):
            ProviderCapabilities(supports_streaming=1)  # type: ignore[arg-type]

    def test_rejects_invalid_context_token_type(
        self,
    ) -> None:
        with self.assertRaisesRegex(
            TypeError,
            "maximum_context_tokens",
        ):
            ProviderCapabilities(
                maximum_context_tokens=("large")  # type: ignore[arg-type]
            )

    def test_rejects_invalid_context_token_limit(
        self,
    ) -> None:
        with self.assertRaisesRegex(
            ValueError,
            "at least 1",
        ):
            ProviderCapabilities(maximum_context_tokens=0)

    def test_rejects_non_list_models(self) -> None:
        with self.assertRaisesRegex(
            TypeError,
            "available_models",
        ):
            ProviderCapabilities(
                available_models=("model-one",)  # type: ignore[arg-type]
            )

    def test_rejects_non_string_model(self) -> None:
        with self.assertRaisesRegex(
            TypeError,
            "available_models",
        ):
            ProviderCapabilities(
                available_models=[
                    "model-one",
                    2,  # type: ignore[list-item]
                ]
            )

    def test_rejects_invalid_metadata(self) -> None:
        with self.assertRaisesRegex(
            TypeError,
            "metadata",
        ):
            ProviderCapabilities(metadata=[])  # type: ignore[arg-type]

    def test_copies_mutable_inputs(self) -> None:
        models = [
            "model-one",
        ]
        metadata = {
            "region": "global",
        }

        capabilities = ProviderCapabilities(
            available_models=models,
            metadata=metadata,
        )

        models.append("model-two")
        metadata["region"] = "changed"

        self.assertEqual(
            capabilities.available_models,
            ["model-one"],
        )
        self.assertEqual(
            capabilities.metadata,
            {
                "region": "global",
            },
        )

    def test_round_trip_dictionary_conversion(
        self,
    ) -> None:
        capabilities = ProviderCapabilities(
            supports_structured_output=True,
            supports_streaming=True,
            supports_tools=True,
            supports_images=True,
            supports_documents=True,
            maximum_context_tokens=128_000,
            available_models=[
                "model-one",
                "model-two",
            ],
            metadata={
                "region": "global",
            },
        )

        restored = ProviderCapabilities.from_dict(capabilities.to_dict())

        self.assertEqual(
            restored,
            capabilities,
        )

    def test_from_dict_rejects_invalid_input(
        self,
    ) -> None:
        with self.assertRaisesRegex(
            TypeError,
            "dictionary",
        ):
            ProviderCapabilities.from_dict([])  # type: ignore[arg-type]


if __name__ == "__main__":
    unittest.main()
