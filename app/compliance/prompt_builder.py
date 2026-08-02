"""Build generic AI prompt sections from compliance requirements."""

from __future__ import annotations

from collections.abc import Sequence

from app.ai.prompt import PromptSection
from app.compliance.requirements import ComplianceRequirement


class CompliancePromptBuilder:
    """Convert compliance requirements into generic prompt sections."""

    SECTION_TITLE = "Compliance Requirements"

    def build_sections(
        self,
        requirements: Sequence[ComplianceRequirement],
    ) -> list[PromptSection]:
        """Return prompt sections for the supplied requirements."""

        if isinstance(
            requirements,
            (str, bytes),
        ) or not isinstance(
            requirements,
            Sequence,
        ):
            raise TypeError("requirements must be a sequence.")

        validated_requirements: list[ComplianceRequirement] = []

        for requirement in requirements:
            if not isinstance(
                requirement,
                ComplianceRequirement,
            ):
                raise TypeError(
                    "requirements must contain " "ComplianceRequirement objects."
                )

            validated_requirements.append(requirement)

        if not validated_requirements:
            return []

        mandatory = [
            requirement
            for requirement in validated_requirements
            if requirement.mandatory
        ]
        recommended = [
            requirement
            for requirement in validated_requirements
            if not requirement.mandatory
        ]

        content_parts: list[str] = []

        if mandatory:
            content_parts.append(
                self._render_group(
                    "Mandatory Requirements",
                    mandatory,
                )
            )

        if recommended:
            content_parts.append(
                self._render_group(
                    "Recommended Requirements",
                    recommended,
                )
            )

        return [
            PromptSection(
                title=self.SECTION_TITLE,
                content="\n\n".join(content_parts),
            )
        ]

    @staticmethod
    def _render_group(
        heading: str,
        requirements: Sequence[ComplianceRequirement],
    ) -> str:
        """Render one ordered requirement group."""

        lines = [
            heading,
            "",
        ]

        lines.extend(f"- {requirement.instruction}" for requirement in requirements)

        return "\n".join(lines)
