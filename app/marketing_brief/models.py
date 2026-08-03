"""Structured Marketing Brief domain models."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any


def current_utc_timestamp() -> str:
    """Return an ISO-formatted UTC timestamp."""

    return datetime.now(UTC).isoformat()


def _required_text(
    field_name: str,
    value: str,
) -> str:
    if not isinstance(value, str):
        raise TypeError(f"{field_name} must be a string.")

    cleaned_value = value.strip()

    if not cleaned_value:
        raise ValueError(f"{field_name} is required.")

    return cleaned_value


def _optional_text(value: str) -> str:
    if not isinstance(value, str):
        raise TypeError("Optional text values must be strings.")

    return value.strip()


def _clean_text_list(
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

        value_key = cleaned_value.casefold()

        if value_key in seen_values:
            continue

        seen_values.add(value_key)
        cleaned_values.append(cleaned_value)

    return cleaned_values


def _clean_metadata(
    metadata: dict[str, Any],
) -> dict[str, Any]:
    if not isinstance(metadata, dict):
        raise TypeError("metadata must be a dictionary.")

    return dict(metadata)


class BriefStatus(StrEnum):
    """Lifecycle status for a Marketing Brief."""

    DRAFT = "draft"
    READY = "ready"
    APPROVED = "approved"
    RETIRED = "retired"


@dataclass(slots=True)
class MarketingBriefEvidence:
    """Traceable evidence supporting one Marketing Brief decision."""

    source_type: str
    source_id: str
    summary: str
    confidence: float = 1.0
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        """Validate and normalise the evidence record."""

        self.source_type = _required_text(
            "source_type",
            self.source_type,
        )
        self.source_id = _required_text(
            "source_id",
            self.source_id,
        )
        self.summary = _required_text(
            "summary",
            self.summary,
        )

        if isinstance(self.confidence, bool):
            raise TypeError("confidence must be a number.")

        if not isinstance(self.confidence, (int, float)):
            raise TypeError("confidence must be a number.")

        self.confidence = float(self.confidence)

        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError("confidence must be between 0 and 1.")

        self.metadata = _clean_metadata(self.metadata)

    def to_dict(self) -> dict[str, Any]:
        """Convert the evidence record into a serialisable dictionary."""

        return asdict(self)

    @classmethod
    def from_dict(
        cls,
        data: dict[str, Any],
    ) -> MarketingBriefEvidence:
        """Create evidence from stored dictionary data."""

        if not isinstance(data, dict):
            raise TypeError("data must be a dictionary.")

        return cls(**data)


@dataclass(slots=True)
class MarketingBrief:
    """A provider-neutral, structured marketing decision artifact."""

    brief_id: str
    tenant_id: str
    brand_id: str
    name: str
    objective: str
    audience: str
    offer: str = ""
    key_message: str = ""
    call_to_action: str = ""
    channels: list[str] = field(default_factory=list)
    deliverables: list[str] = field(default_factory=list)
    constraints: list[str] = field(default_factory=list)
    success_metrics: list[str] = field(default_factory=list)
    customer_segment_ids: list[str] = field(default_factory=list)
    product_ids: list[str] = field(default_factory=list)
    evidence: list[MarketingBriefEvidence] = field(default_factory=list)
    assumptions: list[str] = field(default_factory=list)
    notes: str = ""
    status: BriefStatus = BriefStatus.DRAFT
    version: int = 1
    created_at: str = field(default_factory=current_utc_timestamp)
    updated_at: str = field(default_factory=current_utc_timestamp)

    def __post_init__(self) -> None:
        """Validate and normalise the Marketing Brief."""

        self.brief_id = _required_text(
            "brief_id",
            self.brief_id,
        )
        self.tenant_id = _required_text(
            "tenant_id",
            self.tenant_id,
        )
        self.brand_id = _required_text(
            "brand_id",
            self.brand_id,
        )
        self.name = _required_text(
            "name",
            self.name,
        )
        self.objective = _required_text(
            "objective",
            self.objective,
        )
        self.audience = _required_text(
            "audience",
            self.audience,
        )

        self.offer = _optional_text(self.offer)
        self.key_message = _optional_text(self.key_message)
        self.call_to_action = _optional_text(self.call_to_action)
        self.notes = _optional_text(self.notes)

        self.channels = _clean_text_list(
            "channels",
            self.channels,
        )
        self.deliverables = _clean_text_list(
            "deliverables",
            self.deliverables,
        )
        self.constraints = _clean_text_list(
            "constraints",
            self.constraints,
        )
        self.success_metrics = _clean_text_list(
            "success_metrics",
            self.success_metrics,
        )
        self.customer_segment_ids = _clean_text_list(
            "customer_segment_ids",
            self.customer_segment_ids,
        )
        self.product_ids = _clean_text_list(
            "product_ids",
            self.product_ids,
        )
        self.assumptions = _clean_text_list(
            "assumptions",
            self.assumptions,
        )

        converted_evidence: list[MarketingBriefEvidence] = []

        for evidence_item in self.evidence:
            if isinstance(
                evidence_item,
                MarketingBriefEvidence,
            ):
                converted_item = evidence_item
            elif isinstance(evidence_item, dict):
                converted_item = MarketingBriefEvidence.from_dict(evidence_item)
            else:
                raise TypeError(
                    "evidence must contain " "MarketingBriefEvidence objects."
                )

            converted_evidence.append(converted_item)

        self.evidence = converted_evidence

        if isinstance(self.status, str):
            try:
                self.status = BriefStatus(self.status.strip().lower())
            except ValueError as error:
                raise ValueError("status must be a valid BriefStatus.") from error
        elif not isinstance(self.status, BriefStatus):
            raise TypeError("status must be a BriefStatus or string.")

        if isinstance(self.version, bool):
            raise TypeError("version must be an integer.")

        if not isinstance(self.version, int):
            raise TypeError("version must be an integer.")

        if self.version < 1:
            raise ValueError("version must be at least 1.")

        self.created_at = _required_text(
            "created_at",
            self.created_at,
        )
        self.updated_at = _required_text(
            "updated_at",
            self.updated_at,
        )

        if self.status in {
            BriefStatus.READY,
            BriefStatus.APPROVED,
        }:
            self._validate_execution_readiness()

    @property
    def has_grounding(self) -> bool:
        """Return whether the brief contains traceable evidence."""

        return bool(self.evidence)

    @property
    def is_execution_ready(self) -> bool:
        """Return whether required execution decisions are present."""

        return bool(
            self.channels
            and self.deliverables
            and self.key_message
            and self.call_to_action
        )

    def mark_ready(self) -> None:
        """Move the brief into the ready state."""

        self._validate_execution_readiness()
        self.status = BriefStatus.READY
        self.updated_at = current_utc_timestamp()

    def approve(self) -> None:
        """Approve an execution-ready brief."""

        self._validate_execution_readiness()
        self.status = BriefStatus.APPROVED
        self.updated_at = current_utc_timestamp()

    def retire(self) -> None:
        """Retire the brief without removing its history."""

        self.status = BriefStatus.RETIRED
        self.updated_at = current_utc_timestamp()

    def _validate_execution_readiness(self) -> None:
        missing_fields: list[str] = []

        if not self.channels:
            missing_fields.append("channels")

        if not self.deliverables:
            missing_fields.append("deliverables")

        if not self.key_message:
            missing_fields.append("key_message")

        if not self.call_to_action:
            missing_fields.append("call_to_action")

        if missing_fields:
            raise ValueError(
                "Execution-ready briefs require: " + ", ".join(missing_fields) + "."
            )

    def to_dict(self) -> dict[str, Any]:
        """Convert the Marketing Brief into serialisable data."""

        return {
            "brief_id": self.brief_id,
            "tenant_id": self.tenant_id,
            "brand_id": self.brand_id,
            "name": self.name,
            "objective": self.objective,
            "audience": self.audience,
            "offer": self.offer,
            "key_message": self.key_message,
            "call_to_action": self.call_to_action,
            "channels": list(self.channels),
            "deliverables": list(self.deliverables),
            "constraints": list(self.constraints),
            "success_metrics": list(self.success_metrics),
            "customer_segment_ids": list(self.customer_segment_ids),
            "product_ids": list(self.product_ids),
            "evidence": [evidence_item.to_dict() for evidence_item in self.evidence],
            "assumptions": list(self.assumptions),
            "notes": self.notes,
            "status": self.status.value,
            "version": self.version,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_dict(
        cls,
        data: dict[str, Any],
    ) -> MarketingBrief:
        """Create a Marketing Brief from stored dictionary data."""

        if not isinstance(data, dict):
            raise TypeError("data must be a dictionary.")

        return cls(**data)
