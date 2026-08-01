"""Tests for modular prompt composition."""

from __future__ import annotations

import unittest

from app.ai.prompt import PromptComposer, PromptSection


class PromptSectionTests(unittest.TestCase):
    def test_render_formats_title_and_content(self) -> None:
        section = PromptSection(
            title="Task",
            content="Create a campaign",
        )

        self.assertEqual(
            section.render(),
            "Task:\nCreate a campaign",
        )

    def test_render_cleans_values(self) -> None:
        section = PromptSection(
            title="  Task  ",
            content="  Create a campaign  ",
        )

        self.assertEqual(
            section.render(),
            "Task:\nCreate a campaign",
        )

    def test_render_rejects_blank_title(self) -> None:
        section = PromptSection(
            title=" ",
            content="Create a campaign",
        )

        with self.assertRaisesRegex(
            ValueError,
            "title",
        ):
            section.render()

    def test_render_returns_blank_for_empty_content(
        self,
    ) -> None:
        section = PromptSection(
            title="Instructions",
            content=" ",
        )

        self.assertEqual(section.render(), "")


class PromptComposerTests(unittest.TestCase):
    def test_composer_joins_sections_in_order(
        self,
    ) -> None:
        composer = PromptComposer()
        composer.add(
            PromptSection(
                title="Company Context",
                content="Revenue model: Retail",
            )
        )
        composer.add(
            PromptSection(
                title="Task",
                content="Create a campaign",
            )
        )

        self.assertEqual(
            composer.compose(),
            (
                "Company Context:\n"
                "Revenue model: Retail\n\n"
                "Task:\n"
                "Create a campaign"
            ),
        )

    def test_composer_ignores_empty_sections(
        self,
    ) -> None:
        composer = PromptComposer()
        composer.add(
            PromptSection(
                title="Instructions",
                content="",
            )
        )
        composer.add(
            PromptSection(
                title="Task",
                content="Create a campaign",
            )
        )

        self.assertEqual(
            composer.compose(),
            "Task:\nCreate a campaign",
        )

    def test_composer_rejects_invalid_section(
        self,
    ) -> None:
        composer = PromptComposer()

        with self.assertRaisesRegex(
            TypeError,
            "PromptSection",
        ):
            composer.add(object())  # type: ignore[arg-type]

    def test_empty_composer_returns_blank(self) -> None:
        self.assertEqual(
            PromptComposer().compose(),
            "",
        )


if __name__ == "__main__":
    unittest.main()
