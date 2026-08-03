"""Customer Intelligence domain models for MarketingLabAI."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from typing import Any


def current_utc_timestamp() -> str:
    """Return an ISO-formatted UTC timestamp."""

    return datetime.now(UTC).isoformat()


def _clean_required(value: str, field_name: str) -> str:
    if not isinstance(value, str):
        raise TypeError(f"{field_name} must be a string.")

    cleaned = value.strip()

    if not cleaned:
        raise ValueError(f"{field_name} is required.")

    return cleaned


def _clean_optional(value: str) -> str:
    if not isinstance(value, str):
        raise TypeError("optional customer intelligence values must be strings.")

    return value.strip()


def _clean_list(values: list[str]) -> list[str]:
    if not isinstance(values, list):
        raise TypeError("customer intelligence collections must be lists.")

    cleaned_values: list[str] = []

    for value in values:
        if not isinstance(value, str):
            raise TypeError("customer intelligence list values must be strings.")

        cleaned_value = value.strip()

        if cleaned_value and cleaned_value not in cleaned_values:
            cleaned_values.append(cleaned_value)

    return cleaned_values


@dataclass(slots=True)
class CustomerEvidence:
    """Evidence supporting a customer intelligence statement."""

    source: str
    confidence: float
    summary: str = ""
    verified: bool = False
    observed_at: str = ""

    def __post_init__(self) -> None:
        self.source = _clean_required(self.source, "source")
        self.summary = _clean_optional(self.summary)
        self.observed_at = _clean_optional(self.observed_at)

        if isinstance(self.confidence, bool) or not isinstance(
            self.confidence,
            (int, float),
        ):
            raise TypeError("confidence must be a number.")

        self.confidence = float(self.confidence)

        if not 0 <= self.confidence <= 1:
            raise ValueError("confidence must be between 0 and 1.")

        if not isinstance(self.verified, bool):
            raise TypeError("verified must be a boolean.")

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-serialisable dictionary."""

        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> CustomerEvidence:
        """Restore evidence from stored data."""

        if not isinstance(data, dict):
            raise TypeError("evidence data must be a dictionary.")

        return cls(**data)


@dataclass(slots=True)
class CustomerSegment:
    """A broad customer group served by a brand."""

    segment_id: str
    name: str
    description: str = ""
    characteristics: list[str] = field(default_factory=list)
    evidence: list[CustomerEvidence] = field(default_factory=list)

    def __post_init__(self) -> None:
        self.segment_id = _clean_required(self.segment_id, "segment_id")
        self.name = _clean_required(self.name, "segment name")
        self.description = _clean_optional(self.description)
        self.characteristics = _clean_list(self.characteristics)
        self.evidence = _clean_evidence(self.evidence)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> CustomerSegment:
        if not isinstance(data, dict):
            raise TypeError("segment data must be a dictionary.")

        payload = dict(data)
        payload["evidence"] = [
            CustomerEvidence.from_dict(item) for item in payload.get("evidence", [])
        ]
        return cls(**payload)


@dataclass(slots=True)
class IdealCustomerProfile:
    """A description of a high-value organisational customer."""

    icp_id: str
    name: str
    description: str = ""
    industries: list[str] = field(default_factory=list)
    company_sizes: list[str] = field(default_factory=list)
    regions: list[str] = field(default_factory=list)
    needs: list[str] = field(default_factory=list)
    buying_criteria: list[str] = field(default_factory=list)
    evidence: list[CustomerEvidence] = field(default_factory=list)

    def __post_init__(self) -> None:
        self.icp_id = _clean_required(self.icp_id, "icp_id")
        self.name = _clean_required(self.name, "ICP name")
        self.description = _clean_optional(self.description)
        self.industries = _clean_list(self.industries)
        self.company_sizes = _clean_list(self.company_sizes)
        self.regions = _clean_list(self.regions)
        self.needs = _clean_list(self.needs)
        self.buying_criteria = _clean_list(self.buying_criteria)
        self.evidence = _clean_evidence(self.evidence)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> IdealCustomerProfile:
        if not isinstance(data, dict):
            raise TypeError("ICP data must be a dictionary.")

        payload = dict(data)
        payload["evidence"] = [
            CustomerEvidence.from_dict(item) for item in payload.get("evidence", [])
        ]
        return cls(**payload)


@dataclass(slots=True)
class CustomerPersona:
    """A reusable marketing persona linked to a customer segment."""

    persona_id: str
    name: str
    segment_id: str = ""
    role: str = ""
    description: str = ""
    demographics: list[str] = field(default_factory=list)
    psychographics: list[str] = field(default_factory=list)
    pain_points: list[str] = field(default_factory=list)
    desired_outcomes: list[str] = field(default_factory=list)
    motivations: list[str] = field(default_factory=list)
    buying_triggers: list[str] = field(default_factory=list)
    objections: list[str] = field(default_factory=list)
    decision_criteria: list[str] = field(default_factory=list)
    preferred_channels: list[str] = field(default_factory=list)
    journey_stages: list[str] = field(default_factory=list)
    language_terms: list[str] = field(default_factory=list)
    trust_factors: list[str] = field(default_factory=list)
    emotional_drivers: list[str] = field(default_factory=list)
    customer_questions: list[str] = field(default_factory=list)
    evidence: list[CustomerEvidence] = field(default_factory=list)

    def __post_init__(self) -> None:
        self.persona_id = _clean_required(self.persona_id, "persona_id")
        self.name = _clean_required(self.name, "persona name")
        self.segment_id = _clean_optional(self.segment_id)
        self.role = _clean_optional(self.role)
        self.description = _clean_optional(self.description)

        list_fields = (
            "demographics",
            "psychographics",
            "pain_points",
            "desired_outcomes",
            "motivations",
            "buying_triggers",
            "objections",
            "decision_criteria",
            "preferred_channels",
            "journey_stages",
            "language_terms",
            "trust_factors",
            "emotional_drivers",
            "customer_questions",
        )

        for field_name in list_fields:
            setattr(self, field_name, _clean_list(getattr(self, field_name)))

        self.evidence = _clean_evidence(self.evidence)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> CustomerPersona:
        if not isinstance(data, dict):
            raise TypeError("persona data must be a dictionary.")

        payload = dict(data)
        payload["evidence"] = [
            CustomerEvidence.from_dict(item) for item in payload.get("evidence", [])
        ]
        return cls(**payload)


@dataclass(slots=True)
class CustomerIntelligenceProfile:
    """Customer knowledge linked to one MarketingLabAI brand."""

    brand_id: str
    summary: str = ""
    primary_segment_id: str = ""
    segments: list[CustomerSegment] = field(default_factory=list)
    ideal_customer_profiles: list[IdealCustomerProfile] = field(default_factory=list)
    personas: list[CustomerPersona] = field(default_factory=list)
    updated_at: str = field(default_factory=current_utc_timestamp)

    def __post_init__(self) -> None:
        self.brand_id = _clean_required(self.brand_id, "brand_id")
        self.summary = _clean_optional(self.summary)
        self.primary_segment_id = _clean_optional(self.primary_segment_id)
        self.segments = _clean_segments(self.segments)
        self.ideal_customer_profiles = _clean_icps(self.ideal_customer_profiles)
        self.personas = _clean_personas(self.personas)

        _require_unique_ids(
            [segment.segment_id for segment in self.segments],
            "segment_id",
        )
        _require_unique_ids(
            [profile.icp_id for profile in self.ideal_customer_profiles],
            "icp_id",
        )
        _require_unique_ids(
            [persona.persona_id for persona in self.personas],
            "persona_id",
        )

        segment_ids = {segment.segment_id for segment in self.segments}

        if self.primary_segment_id and self.primary_segment_id not in segment_ids:
            raise ValueError("primary_segment_id must reference an existing segment.")

        for persona in self.personas:
            if persona.segment_id and persona.segment_id not in segment_ids:
                raise ValueError(
                    f"persona {persona.persona_id!r} references an unknown segment."
                )

        if not isinstance(self.updated_at, str):
            raise TypeError("updated_at must be a string.")

        if not self.updated_at.strip():
            self.updated_at = current_utc_timestamp()

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-serialisable dictionary."""

        return asdict(self)

    @classmethod
    def from_dict(
        cls,
        data: dict[str, Any],
    ) -> CustomerIntelligenceProfile:
        """Restore a profile from stored data."""

        if not isinstance(data, dict):
            raise TypeError("customer intelligence data must be a dictionary.")

        payload = dict(data)
        payload["segments"] = [
            CustomerSegment.from_dict(item) for item in payload.get("segments", [])
        ]
        payload["ideal_customer_profiles"] = [
            IdealCustomerProfile.from_dict(item)
            for item in payload.get("ideal_customer_profiles", [])
        ]
        payload["personas"] = [
            CustomerPersona.from_dict(item) for item in payload.get("personas", [])
        ]
        return cls(**payload)


def _clean_evidence(values: list[CustomerEvidence]) -> list[CustomerEvidence]:
    if not isinstance(values, list):
        raise TypeError("evidence must be a list.")

    cleaned: list[CustomerEvidence] = []

    for value in values:
        if not isinstance(value, CustomerEvidence):
            raise TypeError("evidence must contain CustomerEvidence objects.")
        cleaned.append(value)

    return cleaned


def _clean_segments(values: list[CustomerSegment]) -> list[CustomerSegment]:
    if not isinstance(values, list):
        raise TypeError("segments must be a list.")

    cleaned: list[CustomerSegment] = []
    for value in values:
        if not isinstance(value, CustomerSegment):
            raise TypeError("segments must contain CustomerSegment objects.")
        cleaned.append(value)
    return cleaned


def _clean_icps(
    values: list[IdealCustomerProfile],
) -> list[IdealCustomerProfile]:
    if not isinstance(values, list):
        raise TypeError("ideal_customer_profiles must be a list.")

    cleaned: list[IdealCustomerProfile] = []
    for value in values:
        if not isinstance(value, IdealCustomerProfile):
            raise TypeError(
                "ideal_customer_profiles must contain IdealCustomerProfile objects."
            )
        cleaned.append(value)
    return cleaned


def _clean_personas(values: list[CustomerPersona]) -> list[CustomerPersona]:
    if not isinstance(values, list):
        raise TypeError("personas must be a list.")

    cleaned: list[CustomerPersona] = []
    for value in values:
        if not isinstance(value, CustomerPersona):
            raise TypeError("personas must contain CustomerPersona objects.")
        cleaned.append(value)
    return cleaned


def _require_unique_ids(values: list[str], field_name: str) -> None:
    if len(values) != len(set(values)):
        raise ValueError(f"{field_name} values must be unique.")
