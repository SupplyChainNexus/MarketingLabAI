"""Core data models for MarketingLabAI."""

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
        return asdict(self)


@dataclass
class GeneratedContent:
    """A generated marketing asset."""

    campaign_id: str
    platform: str
    content_type: str
    content: str
    model: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
