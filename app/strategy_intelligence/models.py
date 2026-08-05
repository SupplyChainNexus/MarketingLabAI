"""Evidence-grounded Marketing Strategy Intelligence models."""

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


class StrategyStatus(StrEnum):
    DRAFT = "draft"
    APPROVED = "approved"
    RETIRED = "retired"


@dataclass(slots=True)
class StrategyEvidence:
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
class StrategyUnknown:
    field_name: str
    reason: str

    def __post_init__(self) -> None:
        self.field_name = _required(self.field_name, "unknown field_name")
        self.reason = _required(self.reason, "unknown reason")


@dataclass(slots=True)
class StrategyDecision:
    """One immutable version of a brand-owned marketing strategy decision."""

    strategy_id: str
    version: int
    tenant_id: str
    brand_id: str
    positioning_id: str
    positioning_version: int
    status: StrategyStatus = StrategyStatus.DRAFT
    planning_horizon: str = ""
    business_objectives: list[str] = field(default_factory=list)
    strategic_choices: list[str] = field(default_factory=list)
    explicit_non_choices: list[str] = field(default_factory=list)
    assumptions: list[str] = field(default_factory=list)
    unknowns: list[StrategyUnknown] = field(default_factory=list)
    evidence: list[StrategyEvidence] = field(default_factory=list)
    confidence: float = 0.0
    created_at: str = field(default_factory=current_utc_timestamp)
    updated_at: str = field(default_factory=current_utc_timestamp)
    approved_at: str = ""

    def __post_init__(self) -> None:
        self.strategy_id = _required(self.strategy_id, "strategy_id")
        if isinstance(self.version, bool) or not isinstance(self.version, int):
            raise TypeError("version must be an integer.")
        if self.version < 1:
            raise ValueError("version must be at least 1.")
        self.tenant_id = _required(self.tenant_id, "tenant_id")
        self.brand_id = _required(self.brand_id, "brand_id")
        self.positioning_id = _required(self.positioning_id, "positioning_id")
        if isinstance(self.positioning_version, bool) or not isinstance(
            self.positioning_version, int
        ):
            raise TypeError("positioning_version must be an integer.")
        if self.positioning_version < 1:
            raise ValueError("positioning_version must be at least 1.")
        self.status = StrategyStatus(self.status)
        self.planning_horizon = _optional(self.planning_horizon, "planning_horizon")
        self.approved_at = _optional(self.approved_at, "approved_at")
        for name in (
            "business_objectives",
            "strategic_choices",
            "explicit_non_choices",
            "assumptions",
        ):
            setattr(self, name, _unique_text(getattr(self, name), name))
        if not isinstance(self.unknowns, list) or any(
            not isinstance(item, StrategyUnknown) for item in self.unknowns
        ):
            raise TypeError("unknowns must contain StrategyUnknown objects.")
        if len({item.field_name for item in self.unknowns}) != len(self.unknowns):
            raise ValueError("unknown field names must be unique.")
        if not isinstance(self.evidence, list) or any(
            not isinstance(item, StrategyEvidence) for item in self.evidence
        ):
            raise TypeError("evidence must contain StrategyEvidence objects.")
        if isinstance(self.confidence, bool) or not isinstance(
            self.confidence, (int, float)
        ):
            raise TypeError("confidence must be a number.")
        self.confidence = float(self.confidence)
        if not 0 <= self.confidence <= 1:
            raise ValueError("confidence must be between 0 and 1.")
        self.created_at = _required(self.created_at, "created_at")
        self.updated_at = _required(self.updated_at, "updated_at")
        if self.status is StrategyStatus.APPROVED:
            if not self.business_objectives:
                raise ValueError("approved strategy requires a business objective.")
            if not any(item.verified for item in self.evidence):
                raise ValueError("approved strategy requires verified evidence.")
            if not self.approved_at:
                raise ValueError("approved strategy requires approved_at.")
        elif self.approved_at:
            raise ValueError("only approved strategy may contain approved_at.")

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "StrategyDecision":
        if not isinstance(data, dict):
            raise TypeError("data must be a dictionary.")
        payload = dict(data)
        payload["unknowns"] = [
            StrategyUnknown(**item) for item in payload.get("unknowns", [])
        ]
        payload["evidence"] = [
            StrategyEvidence(**item) for item in payload.get("evidence", [])
        ]
        return cls(**payload)
