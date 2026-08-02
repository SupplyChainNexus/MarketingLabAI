"""Core data models for MarketingLabAI."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass
class BrandProfile:
    """Represents a company or organisation using MarketingLabAI."""

    brand_id: str
    name: str
    industry: str
    description: str
    target_audience: str
    products_or_services: list[str] = field(default_factory=list)
    values: list[str] = field(default_factory=list)
    website: str = ""

    def to_dict(self) -> dict[str, Any]:
        """Return a serialisable brand profile."""

        return asdict(self)


@dataclass
class VoiceProfile:
    """Defines how a brand communicates."""

    voice_id: str
    brand_id: str
    summary: str
    tone_traits: list[str]
    preferred_words: list[str] = field(default_factory=list)
    avoided_words: list[str] = field(default_factory=list)
    sentence_style: str = ""
    call_to_action_style: str = ""
    authenticity_rules: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Return a serialisable voice profile."""

        return asdict(self)


@dataclass
class CampaignBrief:
    """Input requirements for a marketing campaign."""

    campaign_id: str
    brand_id: str
    objective: str
    audience: str
    offer: str
    platform: str
    content_type: str
    key_message: str
    call_to_action: str
    additional_context: str = ""

    def to_dict(self) -> dict[str, Any]:
        """Return a serialisable campaign brief."""

        return asdict(self)


@dataclass
class GeneratedContent:
    """A generated marketing asset with AI audit metadata."""

    campaign_id: str
    platform: str
    content_type: str
    content: str
    model: str
    provider: str = ""
    input_tokens: int | None = None
    output_tokens: int | None = None
    finish_reason: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        """Validate and normalise generated-content values."""

        text_fields = (
            "campaign_id",
            "platform",
            "content_type",
            "content",
            "model",
            "provider",
            "finish_reason",
        )

        for field_name in text_fields:
            value = getattr(self, field_name)

            if not isinstance(value, str):
                raise TypeError(f"{field_name} must be a string.")

            setattr(
                self,
                field_name,
                value.strip(),
            )

        required_fields = (
            "campaign_id",
            "platform",
            "content_type",
            "content",
            "model",
        )

        for field_name in required_fields:
            if not getattr(self, field_name):
                raise ValueError(f"{field_name} is required.")

        for field_name in (
            "input_tokens",
            "output_tokens",
        ):
            value = getattr(self, field_name)

            if value is not None:
                if not isinstance(value, int):
                    raise TypeError(f"{field_name} must be an " "integer or None.")

                if value < 0:
                    raise ValueError(f"{field_name} cannot be negative.")

        if not isinstance(self.metadata, dict):
            raise TypeError("metadata must be a dictionary.")

        self.metadata = dict(self.metadata)

    def to_dict(self) -> dict[str, Any]:
        """Return a serialisable generation record."""

        return asdict(self)
