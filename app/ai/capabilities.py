"""Capability declarations for AI intelligence providers."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


def _clean_unique_values(
    field_name: str,
    values: list[str],
) -> list[str]:
    if not isinstance(values, list):
        raise TypeError(f"{field_name} must be a list.")

    cleaned_values: list[str] = []
    seen_values: set[str] = set()

    for value in values:
        if not isinstance(value, str):
            raise TypeError(f"{field_name} must contain strings.")

        cleaned_value = value.strip()

        if not cleaned_value:
            continue

        comparison_key = cleaned_value.casefold()

        if comparison_key in seen_values:
            continue

        seen_values.add(comparison_key)
        cleaned_values.append(cleaned_value)

    return cleaned_values


@dataclass(slots=True)
class ProviderCapabilities:
    """Describe the features supported by an AI provider."""

    supports_structured_output: bool = False
    supports_streaming: bool = False
    supports_tools: bool = False
    supports_images: bool = False
    supports_documents: bool = False
    maximum_context_tokens: int | None = None
    available_models: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        """Validate and normalize capability values."""

        boolean_fields = (
            "supports_structured_output",
            "supports_streaming",
            "supports_tools",
            "supports_images",
            "supports_documents",
        )

        for field_name in boolean_fields:
            value = getattr(self, field_name)

            if not isinstance(value, bool):
                raise TypeError(f"{field_name} must be a boolean.")

        if self.maximum_context_tokens is not None:
            if not isinstance(
                self.maximum_context_tokens,
                int,
            ):
                raise TypeError("maximum_context_tokens must be " "an integer or None.")

            if self.maximum_context_tokens < 1:
                raise ValueError("maximum_context_tokens must be " "at least 1.")

        self.available_models = _clean_unique_values(
            "available_models",
            self.available_models,
        )

        if not isinstance(self.metadata, dict):
            raise TypeError("metadata must be a dictionary.")

        self.metadata = dict(self.metadata)

    def supports_model(
        self,
        model: str,
    ) -> bool:
        """Return whether a named model is supported."""

        if not isinstance(model, str):
            raise TypeError("model must be a string.")

        cleaned_model = model.strip()

        if not cleaned_model:
            raise ValueError("model is required.")

        target = cleaned_model.casefold()

        return any(
            available_model.casefold() == target
            for available_model in self.available_models
        )

    def to_dict(self) -> dict[str, Any]:
        """Convert capabilities into serializable data."""

        return {
            "supports_structured_output": (self.supports_structured_output),
            "supports_streaming": (self.supports_streaming),
            "supports_tools": self.supports_tools,
            "supports_images": self.supports_images,
            "supports_documents": (self.supports_documents),
            "maximum_context_tokens": (self.maximum_context_tokens),
            "available_models": list(self.available_models),
            "metadata": dict(self.metadata),
        }

    @classmethod
    def from_dict(
        cls,
        data: dict[str, Any],
    ) -> ProviderCapabilities:
        """Restore capabilities from serialized data."""

        if not isinstance(data, dict):
            raise TypeError("data must be a dictionary.")

        return cls(**data)
