"""Prompt composition for MarketingLabAI."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True, frozen=True)
class PromptSection:
    """One section of a composed AI prompt."""

    title: str
    content: str

    def render(self) -> str:
        """Render the section."""

        title = self.title.strip()
        content = self.content.strip()

        if not title:
            raise ValueError("title is required.")

        if not content:
            return ""

        return f"{title}:\n{content}"


class PromptComposer:
    """Compose prompts from reusable sections."""

    def __init__(self) -> None:
        self._sections: list[PromptSection] = []

    def add(
        self,
        section: PromptSection,
    ) -> None:
        """Add a non-empty prompt section."""

        if not isinstance(section, PromptSection):
            raise TypeError("section must be a PromptSection.")

        if section.render():
            self._sections.append(section)

    def compose(self) -> str:
        """Return the composed prompt."""

        rendered_sections = [section.render() for section in self._sections]

        return "\n\n".join(section for section in rendered_sections if section)
