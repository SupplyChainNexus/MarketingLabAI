"""Tests for safe Prompt Pack rendering."""

from __future__ import annotations

import unittest

from app.prompts.models import PromptPack
from app.prompts.renderer import PromptPackRenderer


class PromptPackRendererTests(unittest.TestCase):
    def setUp(self) -> None:
        self.renderer = PromptPackRenderer()

    @staticmethod
    def create_pack(
        *,
        template: str = ("Create a {channel} post about {topic}."),
        variables: list[str] | None = None,
    ) -> PromptPack:
        return PromptPack(
            prompt_pack_id="social-post",
            tenant_id="default",
            name="Social Post",
            task_type="social_post",
            template=template,
            variables=(variables if variables is not None else ["channel", "topic"]),
        )

    def test_renderer_replaces_declared_variables(
        self,
    ) -> None:
        result = self.renderer.render(
            self.create_pack(),
            {
                "channel": "LinkedIn",
                "topic": "supply-chain resilience",
            },
        )

        self.assertEqual(
            result,
            ("Create a LinkedIn post about " "supply-chain resilience."),
        )

    def test_renderer_cleans_supplied_values(
        self,
    ) -> None:
        result = self.renderer.render(
            self.create_pack(),
            {
                "channel": " LinkedIn ",
                "topic": " Operations ",
            },
        )

        self.assertEqual(
            result,
            "Create a LinkedIn post about Operations.",
        )

    def test_renderer_supports_repeated_placeholder(
        self,
    ) -> None:
        pack = self.create_pack(
            template=("Write about {topic}. " "End by mentioning {topic}."),
            variables=["topic"],
        )

        result = self.renderer.render(
            pack,
            {"topic": "customer retention"},
        )

        self.assertEqual(
            result,
            (
                "Write about customer retention. "
                "End by mentioning customer retention."
            ),
        )

    def test_renderer_preserves_escaped_braces(
        self,
    ) -> None:
        pack = self.create_pack(
            template=("Return JSON shaped like " '{{"topic": "{topic}"}}.'),
            variables=["topic"],
        )

        result = self.renderer.render(
            pack,
            {"topic": "automation"},
        )

        self.assertEqual(
            result,
            ("Return JSON shaped like " '{"topic": "automation"}.'),
        )

    def test_renderer_rejects_missing_value(
        self,
    ) -> None:
        with self.assertRaisesRegex(
            ValueError,
            "Missing prompt values: topic",
        ):
            self.renderer.render(
                self.create_pack(),
                {"channel": "Facebook"},
            )

    def test_renderer_rejects_unknown_value(
        self,
    ) -> None:
        with self.assertRaisesRegex(
            ValueError,
            "Unknown prompt values: audience",
        ):
            self.renderer.render(
                self.create_pack(),
                {
                    "channel": "Facebook",
                    "topic": "delivery",
                    "audience": "retailers",
                },
            )

    def test_renderer_rejects_undeclared_placeholder(
        self,
    ) -> None:
        pack = self.create_pack(
            variables=["channel"],
        )

        with self.assertRaisesRegex(
            ValueError,
            "undeclared variables: topic",
        ):
            self.renderer.render(
                pack,
                {
                    "channel": "Facebook",
                    "topic": "delivery",
                },
            )

    def test_renderer_rejects_unused_declaration(
        self,
    ) -> None:
        pack = self.create_pack(
            template="Create a post about {topic}.",
            variables=["topic", "audience"],
        )

        with self.assertRaisesRegex(
            ValueError,
            "not used by the template: audience",
        ):
            self.renderer.render(
                pack,
                {"topic": "delivery"},
            )

    def test_renderer_rejects_blank_value(
        self,
    ) -> None:
        with self.assertRaisesRegex(
            ValueError,
            "topic.*cannot be blank",
        ):
            self.renderer.render(
                self.create_pack(),
                {
                    "channel": "Facebook",
                    "topic": " ",
                },
            )

    def test_renderer_rejects_none_value(
        self,
    ) -> None:
        with self.assertRaisesRegex(
            ValueError,
            "topic.*cannot be None",
        ):
            self.renderer.render(
                self.create_pack(),
                {
                    "channel": "Facebook",
                    "topic": None,
                },
            )

    def test_renderer_rejects_attribute_access(
        self,
    ) -> None:
        pack = self.create_pack(
            template="Create a post for {brand.name}.",
            variables=["brand"],
        )

        with self.assertRaisesRegex(
            ValueError,
            "simple variable names",
        ):
            self.renderer.render(
                pack,
                {"brand": "Brand One"},
            )

    def test_renderer_rejects_index_access(
        self,
    ) -> None:
        pack = self.create_pack(
            template="Create a post for {brand[0]}.",
            variables=["brand"],
        )

        with self.assertRaisesRegex(
            ValueError,
            "simple variable names",
        ):
            self.renderer.render(
                pack,
                {"brand": "Brand One"},
            )

    def test_renderer_rejects_format_specification(
        self,
    ) -> None:
        pack = self.create_pack(
            template="Budget: {budget:.2f}",
            variables=["budget"],
        )

        with self.assertRaisesRegex(
            ValueError,
            "format specifications",
        ):
            self.renderer.render(
                pack,
                {"budget": 399},
            )

    def test_renderer_rejects_conversion(
        self,
    ) -> None:
        pack = self.create_pack(
            template="Topic: {topic!r}",
            variables=["topic"],
        )

        with self.assertRaisesRegex(
            ValueError,
            "conversions",
        ):
            self.renderer.render(
                pack,
                {"topic": "delivery"},
            )

    def test_renderer_rejects_invalid_pack(
        self,
    ) -> None:
        with self.assertRaisesRegex(
            TypeError,
            "PromptPack",
        ):
            self.renderer.render(  # type: ignore[arg-type]
                object(),
                {},
            )

    def test_renderer_rejects_non_mapping_values(
        self,
    ) -> None:
        with self.assertRaisesRegex(
            TypeError,
            "mapping",
        ):
            self.renderer.render(  # type: ignore[arg-type]
                self.create_pack(),
                [],
            )


if __name__ == "__main__":
    unittest.main()
