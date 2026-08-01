"""Tests for versioned prompt-pack models."""

from __future__ import annotations

import unittest

from app.prompts.models import PromptPack


class PromptPackTests(unittest.TestCase):
    def test_pack_cleans_values_and_variables(
        self,
    ) -> None:
        pack = PromptPack(
            prompt_pack_id=" facebook-organic ",
            tenant_id=" tenant-one ",
            brand_id=" brand-one ",
            name=" Facebook Organic ",
            task_type=" social_post ",
            channel=" facebook ",
            template=" Create a post about {topic}. ",
            system_instruction=(" Follow the supplied brand voice. "),
            variables=[
                " topic ",
                "audience",
                "TOPIC",
                "",
            ],
        )

        self.assertEqual(
            pack.prompt_pack_id,
            "facebook-organic",
        )
        self.assertEqual(
            pack.tenant_id,
            "tenant-one",
        )
        self.assertEqual(
            pack.brand_id,
            "brand-one",
        )
        self.assertEqual(
            pack.template,
            "Create a post about {topic}.",
        )
        self.assertEqual(
            pack.variables,
            ["topic", "audience"],
        )

    def test_pack_allows_global_tenant_pack(
        self,
    ) -> None:
        pack = PromptPack(
            prompt_pack_id="email-newsletter",
            tenant_id="system",
            brand_id=" ",
            name="Email Newsletter",
            task_type="email",
            template="Write an email about {topic}.",
        )

        self.assertIsNone(pack.brand_id)

    def test_pack_rejects_blank_required_values(
        self,
    ) -> None:
        with self.assertRaisesRegex(
            ValueError,
            "name",
        ):
            PromptPack(
                prompt_pack_id="pack-one",
                tenant_id="tenant-one",
                name=" ",
                task_type="social",
                template="Create content.",
            )

    def test_pack_rejects_invalid_variable_name(
        self,
    ) -> None:
        with self.assertRaisesRegex(
            ValueError,
            "valid identifiers",
        ):
            PromptPack(
                prompt_pack_id="pack-one",
                tenant_id="tenant-one",
                name="Pack One",
                task_type="social",
                template="Create content.",
                variables=["target-audience"],
            )

    def test_pack_rejects_invalid_version(
        self,
    ) -> None:
        with self.assertRaisesRegex(
            ValueError,
            "version",
        ):
            PromptPack(
                prompt_pack_id="pack-one",
                tenant_id="tenant-one",
                name="Pack One",
                task_type="social",
                template="Create content.",
                version=0,
            )

    def test_pack_rejects_non_boolean_status(
        self,
    ) -> None:
        with self.assertRaisesRegex(
            TypeError,
            "enabled",
        ):
            PromptPack(
                prompt_pack_id="pack-one",
                tenant_id="tenant-one",
                name="Pack One",
                task_type="social",
                template="Create content.",
                enabled=1,  # type: ignore[arg-type]
            )

    def test_pack_round_trip_dictionary_conversion(
        self,
    ) -> None:
        original = PromptPack(
            prompt_pack_id="meta-ad-copy",
            tenant_id="tenant-one",
            brand_id="brand-one",
            name="Meta Advertisement Copy",
            description="Generate Meta ad variants.",
            task_type="advertisement",
            channel="meta",
            template=("Create an advertisement for " "{product_name}."),
            system_instruction=("Return three concise variants."),
            variables=["product_name"],
            enabled=False,
            version=2,
        )

        restored = PromptPack.from_dict(original.to_dict())

        self.assertEqual(
            restored.to_dict(),
            original.to_dict(),
        )

    def test_from_dict_rejects_invalid_input(
        self,
    ) -> None:
        with self.assertRaisesRegex(
            TypeError,
            "dictionary",
        ):
            PromptPack.from_dict(  # type: ignore[arg-type]
                [],
            )


if __name__ == "__main__":
    unittest.main()
