"""Provider-neutral compliance requirements for content generation."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Any, Mapping


@dataclass(slots=True, frozen=True)
class ComplianceRequirement:
    """A compliance constraint that can guide content generation."""

    rule_id: str
    requirement_type: str
    instruction: str
    priority: str
    mandatory: bool = True
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        """Validate and defensively copy requirement values."""

        text_fields = (
            "rule_id",
            "requirement_type",
            "instruction",
            "priority",
        )

        for field_name in text_fields:
            value = getattr(self, field_name)

            if not isinstance(value, str):
                raise TypeError(f"{field_name} must be a string.")

            cleaned_value = value.strip()

            if not cleaned_value:
                raise ValueError(f"{field_name} is required.")

            object.__setattr__(
                self,
                field_name,
                cleaned_value,
            )

        if not isinstance(self.mandatory, bool):
            raise TypeError("mandatory must be a boolean.")

        if not isinstance(self.metadata, Mapping):
            raise TypeError("metadata must be a mapping.")

        copied_metadata = deepcopy(dict(self.metadata))

        object.__setattr__(
            self,
            "metadata",
            MappingProxyType(copied_metadata),
        )

    def to_dict(self) -> dict[str, Any]:
        """Return a serialisable requirement dictionary."""

        return {
            "rule_id": self.rule_id,
            "requirement_type": self.requirement_type,
            "instruction": self.instruction,
            "priority": self.priority,
            "mandatory": self.mandatory,
            "metadata": deepcopy(dict(self.metadata)),
        }
