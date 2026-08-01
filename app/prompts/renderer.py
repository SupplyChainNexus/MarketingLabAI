"""Safe deterministic rendering for Prompt Packs."""

from __future__ import annotations

from collections.abc import Mapping
from string import Formatter
from typing import Any

from app.prompts.models import PromptPack


class PromptPackRenderer:
    """Validate and render a versioned Prompt Pack."""

    def render(
        self,
        prompt_pack: PromptPack,
        values: Mapping[str, Any],
    ) -> str:
        """Render a Prompt Pack using validated variable values."""

        if not isinstance(prompt_pack, PromptPack):
            raise TypeError("prompt_pack must be a PromptPack.")

        if not isinstance(values, Mapping):
            raise TypeError("values must be a mapping.")

        placeholders = self._extract_placeholders(prompt_pack.template)
        declared_variables = set(prompt_pack.variables)

        undeclared_placeholders = placeholders - declared_variables

        if undeclared_placeholders:
            names = ", ".join(sorted(undeclared_placeholders))
            raise ValueError("Template contains undeclared " f"variables: {names}.")

        unused_declarations = declared_variables - placeholders

        if unused_declarations:
            names = ", ".join(sorted(unused_declarations))
            raise ValueError(
                "Prompt Pack declares variables " f"not used by the template: {names}."
            )

        supplied_values = dict(values)
        supplied_names = set(supplied_values)

        missing_values = placeholders - supplied_names

        if missing_values:
            names = ", ".join(sorted(missing_values))
            raise ValueError(f"Missing prompt values: {names}.")

        unknown_values = supplied_names - placeholders

        if unknown_values:
            names = ", ".join(sorted(unknown_values))
            raise ValueError(f"Unknown prompt values: {names}.")

        cleaned_values: dict[str, str] = {}

        for name, value in supplied_values.items():
            if value is None:
                raise ValueError(f"Prompt value '{name}' " "cannot be None.")

            rendered_value = str(value).strip()

            if not rendered_value:
                raise ValueError(f"Prompt value '{name}' " "cannot be blank.")

            cleaned_values[name] = rendered_value

        try:
            return prompt_pack.template.format_map(cleaned_values)
        except (KeyError, ValueError) as error:
            raise ValueError(
                "Prompt Pack template could not " "be rendered."
            ) from error

    @staticmethod
    def _extract_placeholders(
        template: str,
    ) -> set[str]:
        """Return validated simple placeholders from a template."""

        placeholders: set[str] = set()

        try:
            parsed_fields = Formatter().parse(template)
        except ValueError as error:
            raise ValueError(
                "Prompt Pack template contains " "invalid braces."
            ) from error

        for (
            _literal_text,
            field_name,
            format_spec,
            conversion,
        ) in parsed_fields:
            if field_name is None:
                continue

            if not field_name:
                raise ValueError("Anonymous prompt placeholders " "are not supported.")

            if "." in field_name or "[" in field_name or "]" in field_name:
                raise ValueError(
                    "Prompt placeholders must use " "simple variable names."
                )

            if not field_name.isidentifier():
                raise ValueError("Prompt placeholders must be " "valid identifiers.")

            if conversion is not None:
                raise ValueError("Prompt placeholder conversions " "are not supported.")

            if format_spec:
                raise ValueError(
                    "Prompt placeholder format " "specifications are not supported."
                )

            placeholders.add(field_name)

        return placeholders
