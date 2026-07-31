"""Provider-neutral AI request and response models."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass(slots=True)
class IntelligenceRequest:
    """A provider-neutral AI generation request."""

    prompt: str
    system_instruction: str = ""
    model: str = ""
    temperature: float | None = None
    max_output_tokens: int | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.prompt = self.prompt.strip()
        self.system_instruction = self.system_instruction.strip()
        self.model = self.model.strip()

        if not self.prompt:
            raise ValueError("prompt is required.")

        if self.temperature is not None:
            if not 0 <= self.temperature <= 2:
                raise ValueError("temperature must be between 0 and 2.")

        if self.max_output_tokens is not None:
            if self.max_output_tokens < 1:
                raise ValueError("max_output_tokens must be at least 1.")

        if not isinstance(self.metadata, dict):
            raise TypeError("metadata must be a dictionary.")

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(
        cls,
        payload: dict[str, Any],
    ) -> "IntelligenceRequest":
        if not isinstance(payload, dict):
            raise TypeError("Intelligence request payload must be a dictionary.")

        return cls(
            prompt=str(payload.get("prompt", "")),
            system_instruction=str(payload.get("system_instruction", "")),
            model=str(payload.get("model", "")),
            temperature=payload.get("temperature"),
            max_output_tokens=payload.get("max_output_tokens"),
            metadata=dict(payload.get("metadata", {})),
        )


@dataclass(slots=True)
class IntelligenceResponse:
    """A provider-neutral AI generation response."""

    content: str
    provider: str
    model: str
    input_tokens: int | None = None
    output_tokens: int | None = None
    finish_reason: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.content = self.content.strip()
        self.provider = self.provider.strip()
        self.model = self.model.strip()
        self.finish_reason = self.finish_reason.strip()

        if not self.content:
            raise ValueError("Response content is required.")

        if not self.provider:
            raise ValueError("Response provider is required.")

        if not self.model:
            raise ValueError("Response model is required.")

        for name, value in (
            ("input_tokens", self.input_tokens),
            ("output_tokens", self.output_tokens),
        ):
            if value is not None and value < 0:
                raise ValueError(f"{name} cannot be negative.")

        if not isinstance(self.metadata, dict):
            raise TypeError("metadata must be a dictionary.")

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(
        cls,
        payload: dict[str, Any],
    ) -> "IntelligenceResponse":
        if not isinstance(payload, dict):
            raise TypeError("Intelligence response payload must be a dictionary.")

        return cls(
            content=str(payload.get("content", "")),
            provider=str(payload.get("provider", "")),
            model=str(payload.get("model", "")),
            input_tokens=payload.get("input_tokens"),
            output_tokens=payload.get("output_tokens"),
            finish_reason=str(payload.get("finish_reason", "")),
            metadata=dict(payload.get("metadata", {})),
        )
