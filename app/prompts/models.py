"""Models for versioned MarketingLabAI prompt packs."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

_VARIABLE_PATTERN = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


def current_utc_timestamp() -> str:
    """Return an ISO-formatted UTC timestamp."""

    return datetime.now(UTC).isoformat()


def _required_text(
    field_name: str,
    value: str,
) -> str:
    cleaned_value = value.strip()

    if not cleaned_value:
        raise ValueError(f"{field_name} is required.")

    return cleaned_value


def _optional_text(value: str) -> str:
    return value.strip()


@dataclass(slots=True)
class PromptPack:
    """A reusable, versioned marketing prompt definition."""

    prompt_pack_id: str
    tenant_id: str
    name: str
    task_type: str
    template: str
    description: str = ""
    channel: str = ""
    brand_id: str | None = None
    system_instruction: str = ""
    variables: list[str] = field(default_factory=list)
    enabled: bool = True
    version: int = 1
    created_at: str = field(default_factory=current_utc_timestamp)
    updated_at: str = field(default_factory=current_utc_timestamp)

    def __post_init__(self) -> None:
        """Validate and normalise the prompt pack."""

        self.prompt_pack_id = _required_text(
            "prompt_pack_id",
            self.prompt_pack_id,
        )
        self.tenant_id = _required_text(
            "tenant_id",
            self.tenant_id,
        )
        self.name = _required_text(
            "name",
            self.name,
        )
        self.task_type = _required_text(
            "task_type",
            self.task_type,
        )
        self.template = _required_text(
            "template",
            self.template,
        )

        self.description = _optional_text(self.description)
        self.channel = _optional_text(self.channel)
        self.system_instruction = _optional_text(self.system_instruction)

        if self.brand_id is not None:
            self.brand_id = self.brand_id.strip() or None

        if not isinstance(self.enabled, bool):
            raise TypeError("enabled must be a boolean.")

        if self.version < 1:
            raise ValueError("version must be at least 1.")

        cleaned_variables: list[str] = []
        seen_variables: set[str] = set()

        for variable in self.variables:
            if not isinstance(variable, str):
                raise TypeError("variables must contain strings.")

            cleaned_variable = variable.strip()

            if not cleaned_variable:
                continue

            if not _VARIABLE_PATTERN.fullmatch(cleaned_variable):
                raise ValueError("Prompt variable names must be " "valid identifiers.")

            variable_key = cleaned_variable.casefold()

            if variable_key in seen_variables:
                continue

            seen_variables.add(variable_key)
            cleaned_variables.append(cleaned_variable)

        self.variables = cleaned_variables

        self.created_at = self.created_at.strip() or current_utc_timestamp()
        self.updated_at = self.updated_at.strip() or current_utc_timestamp()

    def to_dict(self) -> dict[str, Any]:
        """Convert the pack into a serialisable dictionary."""

        return {
            "prompt_pack_id": self.prompt_pack_id,
            "tenant_id": self.tenant_id,
            "name": self.name,
            "task_type": self.task_type,
            "template": self.template,
            "description": self.description,
            "channel": self.channel,
            "brand_id": self.brand_id,
            "system_instruction": (self.system_instruction),
            "variables": list(self.variables),
            "enabled": self.enabled,
            "version": self.version,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_dict(
        cls,
        data: dict[str, Any],
    ) -> PromptPack:
        """Create a prompt pack from stored data."""

        if not isinstance(data, dict):
            raise TypeError("data must be a dictionary.")

        return cls(**data)
