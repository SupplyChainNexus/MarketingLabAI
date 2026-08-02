"""Requirements used to select compatible AI providers."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True, frozen=True)
class ProviderRequirements:
    """Describe the capabilities required for an AI operation."""

    model: str = ""
    requires_streaming: bool = False
    requires_tools: bool = False
    requires_structured_output: bool = False
    requires_image_input: bool = False
    requires_document_input: bool = False
    minimum_context_tokens: int | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        """Validate and normalize requirement values."""

        if not isinstance(self.model, str):
            raise TypeError("model must be a string.")

        boolean_fields = (
            "requires_streaming",
            "requires_tools",
            "requires_structured_output",
            "requires_image_input",
            "requires_document_input",
        )

        for field_name in boolean_fields:
            value = getattr(self, field_name)

            if not isinstance(value, bool):
                raise TypeError(f"{field_name} must be a boolean.")

        if self.minimum_context_tokens is not None:
            if not isinstance(
                self.minimum_context_tokens,
                int,
            ):
                raise TypeError("minimum_context_tokens must be " "an integer or None.")

            if self.minimum_context_tokens < 1:
                raise ValueError("minimum_context_tokens must be " "at least 1.")

        if not isinstance(self.metadata, dict):
            raise TypeError("metadata must be a dictionary.")

        object.__setattr__(
            self,
            "model",
            self.model.strip(),
        )
        object.__setattr__(
            self,
            "metadata",
            dict(self.metadata),
        )

    @property
    def has_capability_requirements(self) -> bool:
        """Return whether capability matching is required."""

        return any(
            (
                self.requires_streaming,
                self.requires_tools,
                self.requires_structured_output,
                self.requires_image_input,
                self.requires_document_input,
                self.minimum_context_tokens is not None,
            )
        )

    def to_dict(self) -> dict[str, Any]:
        """Convert requirements into serializable data."""

        return {
            "model": self.model,
            "requires_streaming": self.requires_streaming,
            "requires_tools": self.requires_tools,
            "requires_structured_output": (self.requires_structured_output),
            "requires_image_input": (self.requires_image_input),
            "requires_document_input": (self.requires_document_input),
            "minimum_context_tokens": (self.minimum_context_tokens),
            "metadata": dict(self.metadata),
        }

    @classmethod
    def from_dict(
        cls,
        data: dict[str, Any],
    ) -> ProviderRequirements:
        """Restore requirements from serialized data."""

        if not isinstance(data, dict):
            raise TypeError("data must be a dictionary.")

        return cls(**data)
