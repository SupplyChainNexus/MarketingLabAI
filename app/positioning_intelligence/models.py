"""Evidence-grounded Positioning Intelligence domain models."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any


def _required(value: str, name: str) -> str:
    if not isinstance(value, str):
        raise TypeError(f"{name} must be a string.")
    cleaned = value.strip()
    if not cleaned:
        raise ValueError(f"{name} is required.")
    return cleaned


def _optional(value: str, name: str) -> str:
    if not isinstance(value, str):
        raise TypeError(f"{name} must be a string.")
    return value.strip()


def _unique_text(values: list[str], name: str) -> list[str]:
    if not isinstance(values, list):
        raise TypeError(f"{name} must be a list.")
    cleaned: list[str] = []
    for value in values:
        value = _required(value, f"{name} value")
        if value not in cleaned:
            cleaned.append(value)
    return cleaned


def current_utc_timestamp() -> str:
    return datetime.now(UTC).isoformat()


class PositioningStatus(StrEnum):
    DRAFT = "draft"
    APPROVED = "approved"
    RETIRED = "retired"


class TargetKind(StrEnum):
    SEGMENT = "segment"
    PERSONA = "persona"
    ICP = "ideal_customer_profile"


@dataclass(slots=True)
class PositioningEvidence:
    source: str
    summary: str
    confidence: float
    verified: bool = False
    observed_at: str = ""

    def __post_init__(self) -> None:
        self.source = _required(self.source, "evidence source")
        self.summary = _required(self.summary, "evidence summary")
        self.observed_at = _optional(self.observed_at, "observed_at")
        if isinstance(self.confidence, bool) or not isinstance(
            self.confidence, (int, float)
        ):
            raise TypeError("confidence must be a number.")
        self.confidence = float(self.confidence)
        if not 0 <= self.confidence <= 1:
            raise ValueError("confidence must be between 0 and 1.")
        if not isinstance(self.verified, bool):
            raise TypeError("verified must be a boolean.")


@dataclass(slots=True)
class PositioningUnknown:
    field_name: str
    reason: str

    def __post_init__(self) -> None:
        self.field_name = _required(self.field_name, "unknown field_name")
        self.reason = _required(self.reason, "unknown reason")


@dataclass(slots=True)
class PositioningDecision:
    """One immutable version of a brand positioning decision."""

    positioning_id: str
    version: int
    tenant_id: str
    brand_id: str
    target_kind: TargetKind
    target_id: str
    product_id: str
    status: PositioningStatus = PositioningStatus.DRAFT
    offer_id: str = ""
    customer_problem: str = ""
    frame_of_reference: str = ""
    value_proposition: str = ""
    differentiators: list[str] = field(default_factory=list)
    proof_points: list[str] = field(default_factory=list)
    alternatives: list[str] = field(default_factory=list)
    assumptions: list[str] = field(default_factory=list)
    unknowns: list[PositioningUnknown] = field(default_factory=list)
    evidence: list[PositioningEvidence] = field(default_factory=list)
    created_at: str = field(default_factory=current_utc_timestamp)
    updated_at: str = field(default_factory=current_utc_timestamp)
    approved_at: str = ""

    def __post_init__(self) -> None:
        self.positioning_id = _required(self.positioning_id, "positioning_id")
        if isinstance(self.version, bool) or not isinstance(self.version, int):
            raise TypeError("version must be an integer.")
        if self.version < 1:
            raise ValueError("version must be at least 1.")
        self.tenant_id = _required(self.tenant_id, "tenant_id")
        self.brand_id = _required(self.brand_id, "brand_id")
        self.target_kind = TargetKind(self.target_kind)
        self.target_id = _required(self.target_id, "target_id")
        self.product_id = _required(self.product_id, "product_id")
        self.status = PositioningStatus(self.status)
        for name in (
            "offer_id",
            "customer_problem",
            "frame_of_reference",
            "value_proposition",
            "approved_at",
        ):
            setattr(self, name, _optional(getattr(self, name), name))
        for name in (
            "differentiators",
            "proof_points",
            "alternatives",
            "assumptions",
        ):
            setattr(self, name, _unique_text(getattr(self, name), name))
        if not isinstance(self.unknowns, list) or any(
            not isinstance(item, PositioningUnknown) for item in self.unknowns
        ):
            raise TypeError("unknowns must contain PositioningUnknown objects.")
        if len({item.field_name for item in self.unknowns}) != len(self.unknowns):
            raise ValueError("unknown field names must be unique.")
        if not isinstance(self.evidence, list) or any(
            not isinstance(item, PositioningEvidence) for item in self.evidence
        ):
            raise TypeError("evidence must contain PositioningEvidence objects.")
        self.created_at = _required(self.created_at, "created_at")
        self.updated_at = _required(self.updated_at, "updated_at")
        if self.status is PositioningStatus.APPROVED:
            if not self.value_proposition:
                raise ValueError("approved positioning requires a value proposition.")
            if not any(item.verified for item in self.evidence):
                raise ValueError("approved positioning requires verified evidence.")
            if not self.approved_at:
                raise ValueError("approved positioning requires approved_at.")
        elif self.approved_at:
            raise ValueError("only approved positioning may contain approved_at.")

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "PositioningDecision":
        if not isinstance(data, dict):
            raise TypeError("data must be a dictionary.")
        payload = dict(data)
        payload["unknowns"] = [
            PositioningUnknown(**item) for item in payload.get("unknowns", [])
        ]
        payload["evidence"] = [
            PositioningEvidence(**item) for item in payload.get("evidence", [])
        ]
        return cls(**payload)
