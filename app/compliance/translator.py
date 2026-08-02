"""Translate compliance rule definitions into generation requirements."""

from __future__ import annotations

from collections.abc import Callable
from copy import deepcopy
from typing import Any

from app.compliance.requirements import (
    ComplianceRequirement,
)
from app.compliance.rule_packs import RulePackEntry

RequirementFactory = Callable[
    [RulePackEntry],
    ComplianceRequirement,
]


class ComplianceRequirementTranslator:
    """Translate supported rule-pack entries into prompt-neutral constraints."""

    def __init__(self) -> None:
        self._translators: dict[
            str,
            RequirementFactory,
        ] = {
            "required_phrase": (self._translate_required_phrase),
            "required_url": (self._translate_required_url),
            "maximum_length": (self._translate_maximum_length),
            "forbidden_regex": (self._translate_forbidden_regex),
            "maximum_keyword_count": (self._translate_maximum_keyword_count),
        }

    @property
    def supported_types(self) -> tuple[str, ...]:
        """Return supported evaluator types in deterministic order."""

        return tuple(sorted(self._translators))

    def translate(
        self,
        entry: RulePackEntry,
    ) -> ComplianceRequirement:
        """Translate one rule-pack entry."""

        if not isinstance(entry, RulePackEntry):
            raise TypeError("entry must be a RulePackEntry.")

        translator = self._translators.get(entry.evaluator_type)

        if translator is None:
            supported = ", ".join(self.supported_types)
            raise ValueError(
                "Unsupported compliance evaluator type "
                f"'{entry.evaluator_type}'. "
                f"Supported values: {supported}."
            )

        return translator(entry)

    def translate_many(
        self,
        entries: list[RulePackEntry],
    ) -> list[ComplianceRequirement]:
        """Translate multiple entries while preserving their order."""

        if not isinstance(entries, list):
            raise TypeError("entries must be a list.")

        requirements: list[ComplianceRequirement] = []

        for entry in entries:
            requirements.append(self.translate(entry))

        return requirements

    def _translate_required_phrase(
        self,
        entry: RulePackEntry,
    ) -> ComplianceRequirement:
        phrase = self._required_string(
            entry,
            "required_phrase",
        )

        return self._create_requirement(
            entry,
            requirement_type="required_phrase",
            instruction=("Include the exact phrase " f'"{phrase}".'),
        )

    def _translate_required_url(
        self,
        entry: RulePackEntry,
    ) -> ComplianceRequirement:
        url = self._required_string(
            entry,
            "required_url",
        )

        return self._create_requirement(
            entry,
            requirement_type="required_url",
            instruction=("Include the URL " f'"{url}".'),
        )

    def _translate_maximum_length(
        self,
        entry: RulePackEntry,
    ) -> ComplianceRequirement:
        maximum = self._non_negative_integer(
            entry,
            "maximum",
        )

        measurement = entry.evaluator_config.get(
            "measurement",
            "characters",
        )

        if not isinstance(measurement, str):
            raise TypeError("measurement must be a string.")

        cleaned_measurement = measurement.strip()

        if cleaned_measurement not in {
            "characters",
            "words",
        }:
            raise ValueError("measurement must be " "'characters' or 'words'.")

        return self._create_requirement(
            entry,
            requirement_type="maximum_length",
            instruction=(
                f"Keep the content within {maximum} " f"{cleaned_measurement}."
            ),
        )

    def _translate_forbidden_regex(
        self,
        entry: RulePackEntry,
    ) -> ComplianceRequirement:
        pattern = self._required_string(
            entry,
            "pattern",
        )

        return self._create_requirement(
            entry,
            requirement_type="forbidden_regex",
            instruction=(
                "Avoid wording that matches the " f"prohibited pattern `{pattern}`."
            ),
        )

    def _translate_maximum_keyword_count(
        self,
        entry: RulePackEntry,
    ) -> ComplianceRequirement:
        keyword = self._required_string(
            entry,
            "keyword",
        )
        maximum = self._non_negative_integer(
            entry,
            "maximum",
        )

        return self._create_requirement(
            entry,
            requirement_type=("maximum_keyword_count"),
            instruction=(
                f'Use the keyword "{keyword}" no more ' f"than {maximum} times."
            ),
        )

    @staticmethod
    def _create_requirement(
        entry: RulePackEntry,
        *,
        requirement_type: str,
        instruction: str,
    ) -> ComplianceRequirement:
        rule = entry.rule

        return ComplianceRequirement(
            rule_id=rule.rule_id,
            requirement_type=requirement_type,
            instruction=instruction,
            priority=rule.severity.value,
            mandatory=rule.enabled,
            metadata={
                "rule_name": rule.name,
                "rule_description": (rule.description),
                "brand_id": rule.brand_id,
                "category": rule.category,
                "rule_version": rule.version,
                "evaluation_method": (rule.evaluation_method.value),
                "subject_types": [
                    subject_type.value for subject_type in rule.subject_types
                ],
                "evaluator_type": (entry.evaluator_type),
                "evaluator_config": deepcopy(entry.evaluator_config),
            },
        )

    @staticmethod
    def _required_string(
        entry: RulePackEntry,
        field_name: str,
    ) -> str:
        if field_name not in entry.evaluator_config:
            raise ValueError(f"{field_name} is required.")

        value = entry.evaluator_config[field_name]

        if not isinstance(value, str):
            raise TypeError(f"{field_name} must be a string.")

        cleaned_value = value.strip()

        if not cleaned_value:
            raise ValueError(f"{field_name} is required.")

        return cleaned_value

    @staticmethod
    def _non_negative_integer(
        entry: RulePackEntry,
        field_name: str,
    ) -> int:
        value: Any = entry.evaluator_config.get(field_name)

        if isinstance(value, bool) or not isinstance(
            value,
            int,
        ):
            raise TypeError(f"{field_name} must be an integer.")

        if value < 0:
            raise ValueError(f"{field_name} cannot be negative.")

        return value
