"""Domain models for MarketingLabAI compliance evaluation."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from typing import Any


def current_utc_timestamp() -> str:
    """Return an ISO-formatted UTC timestamp."""

    return datetime.now(UTC).isoformat()


class ReviewSubjectType(str, Enum):
    """Supported marketing asset types."""

    TEXT = "text"
    IMAGE = "image"
    VIDEO = "video"
    AUDIO = "audio"


class RuleSeverity(str, Enum):
    """Business impact of a compliance rule or finding."""

    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    BLOCKER = "blocker"


class EvaluationMethod(str, Enum):
    """Method used to evaluate a compliance rule."""

    DETERMINISTIC = "deterministic"
    EVIDENCE = "evidence"
    MODEL_ASSISTED = "model_assisted"
    HUMAN = "human"


class ComplianceStatus(str, Enum):
    """Compliance state of a finding or report."""

    PENDING = "pending"
    COMPLIANT = "compliant"
    REQUIRES_REVIEW = "requires_review"
    NON_COMPLIANT = "non_compliant"


def _required_text(field_name: str, value: str) -> str:
    """Clean and validate a required text value."""

    cleaned_value = value.strip()

    if not cleaned_value:
        raise ValueError(f"{field_name} is required.")

    return cleaned_value


def _optional_text(value: str) -> str:
    """Clean an optional text value."""

    return value.strip()


def _clean_string_list(values: list[str]) -> list[str]:
    """Clean and deduplicate a list of strings."""

    cleaned_values: list[str] = []

    for value in values:
        cleaned_value = value.strip()

        if cleaned_value and cleaned_value not in cleaned_values:
            cleaned_values.append(cleaned_value)

    return cleaned_values


def _coerce_enum(
    enum_type: type[Enum],
    value: Enum | str,
    field_name: str,
) -> Enum:
    """Convert a stored string into the required enum type."""

    if isinstance(value, enum_type):
        return value

    try:
        return enum_type(value)
    except (TypeError, ValueError) as error:
        raise ValueError(
            f"{field_name} must be a valid {enum_type.__name__} value."
        ) from error


@dataclass(slots=True)
class BrandRule:
    """A versionable rule used to evaluate marketing content."""

    rule_id: str
    brand_id: str
    name: str
    description: str
    severity: RuleSeverity = RuleSeverity.WARNING
    evaluation_method: EvaluationMethod = EvaluationMethod.DETERMINISTIC
    subject_types: list[ReviewSubjectType] = field(
        default_factory=lambda: [ReviewSubjectType.TEXT]
    )
    category: str = ""
    enabled: bool = True
    evidence_required: bool = False
    version: int = 1
    created_at: str = field(default_factory=current_utc_timestamp)
    updated_at: str = field(default_factory=current_utc_timestamp)

    def __post_init__(self) -> None:
        """Validate and normalise the rule."""

        self.rule_id = _required_text("rule_id", self.rule_id)
        self.brand_id = _required_text("brand_id", self.brand_id)
        self.name = _required_text("name", self.name)
        self.description = _required_text("description", self.description)
        self.category = _optional_text(self.category)

        self.severity = _coerce_enum(
            RuleSeverity,
            self.severity,
            "severity",
        )
        self.evaluation_method = _coerce_enum(
            EvaluationMethod,
            self.evaluation_method,
            "evaluation_method",
        )

        cleaned_subject_types: list[ReviewSubjectType] = []

        for subject_type in self.subject_types:
            converted_type = _coerce_enum(
                ReviewSubjectType,
                subject_type,
                "subject_types",
            )

            if converted_type not in cleaned_subject_types:
                cleaned_subject_types.append(converted_type)

        if not cleaned_subject_types:
            raise ValueError("subject_types must contain at least one value.")

        self.subject_types = cleaned_subject_types

        if self.version < 1:
            raise ValueError("version must be at least 1.")

        if not self.created_at.strip():
            self.created_at = current_utc_timestamp()

        if not self.updated_at.strip():
            self.updated_at = current_utc_timestamp()

    def applies_to(self, subject_type: ReviewSubjectType | str) -> bool:
        """Return whether the rule applies to a subject type."""

        converted_type = _coerce_enum(
            ReviewSubjectType,
            subject_type,
            "subject_type",
        )

        return converted_type in self.subject_types

    def to_dict(self) -> dict[str, Any]:
        """Convert the rule into a JSON-serialisable dictionary."""

        return {
            "rule_id": self.rule_id,
            "brand_id": self.brand_id,
            "name": self.name,
            "description": self.description,
            "severity": self.severity.value,
            "evaluation_method": self.evaluation_method.value,
            "subject_types": [
                subject_type.value for subject_type in self.subject_types
            ],
            "category": self.category,
            "enabled": self.enabled,
            "evidence_required": self.evidence_required,
            "version": self.version,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> BrandRule:
        """Create a rule from stored dictionary data."""

        return cls(**data)


@dataclass(slots=True)
class ComplianceFinding:
    """A single evidence-backed compliance assessment."""

    finding_id: str
    rule_id: str
    subject_id: str
    subject_type: ReviewSubjectType
    status: ComplianceStatus
    severity: RuleSeverity
    evaluation_method: EvaluationMethod
    message: str
    evidence: list[str] = field(default_factory=list)
    recommendation: str = ""
    timestamp_start_seconds: float | None = None
    timestamp_end_seconds: float | None = None
    created_at: str = field(default_factory=current_utc_timestamp)

    def __post_init__(self) -> None:
        """Validate and normalise the finding."""

        self.finding_id = _required_text("finding_id", self.finding_id)
        self.rule_id = _required_text("rule_id", self.rule_id)
        self.subject_id = _required_text("subject_id", self.subject_id)
        self.message = _required_text("message", self.message)
        self.recommendation = _optional_text(self.recommendation)
        self.evidence = _clean_string_list(self.evidence)

        self.subject_type = _coerce_enum(
            ReviewSubjectType,
            self.subject_type,
            "subject_type",
        )
        self.status = _coerce_enum(
            ComplianceStatus,
            self.status,
            "status",
        )
        self.severity = _coerce_enum(
            RuleSeverity,
            self.severity,
            "severity",
        )
        self.evaluation_method = _coerce_enum(
            EvaluationMethod,
            self.evaluation_method,
            "evaluation_method",
        )

        self._validate_timestamps()

        if not self.created_at.strip():
            self.created_at = current_utc_timestamp()

    def _validate_timestamps(self) -> None:
        """Validate optional media timestamps."""

        if self.timestamp_start_seconds is not None:
            if self.timestamp_start_seconds < 0:
                raise ValueError("timestamp_start_seconds cannot be negative.")

        if self.timestamp_end_seconds is not None:
            if self.timestamp_end_seconds < 0:
                raise ValueError("timestamp_end_seconds cannot be negative.")

        if (
            self.timestamp_start_seconds is not None
            and self.timestamp_end_seconds is not None
            and self.timestamp_end_seconds < self.timestamp_start_seconds
        ):
            raise ValueError(
                "timestamp_end_seconds cannot be earlier than "
                "timestamp_start_seconds."
            )

    def to_dict(self) -> dict[str, Any]:
        """Convert the finding into a JSON-serialisable dictionary."""

        return {
            "finding_id": self.finding_id,
            "rule_id": self.rule_id,
            "subject_id": self.subject_id,
            "subject_type": self.subject_type.value,
            "status": self.status.value,
            "severity": self.severity.value,
            "evaluation_method": self.evaluation_method.value,
            "message": self.message,
            "evidence": list(self.evidence),
            "recommendation": self.recommendation,
            "timestamp_start_seconds": self.timestamp_start_seconds,
            "timestamp_end_seconds": self.timestamp_end_seconds,
            "created_at": self.created_at,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ComplianceFinding:
        """Create a finding from stored dictionary data."""

        return cls(**data)


@dataclass(slots=True)
class ComplianceReport:
    """Versioned compliance result for one marketing asset."""

    report_id: str
    brand_id: str
    subject_id: str
    subject_type: ReviewSubjectType
    status: ComplianceStatus = ComplianceStatus.PENDING
    findings: list[ComplianceFinding] = field(default_factory=list)
    summary: str = ""
    ruleset_version: str = ""
    created_at: str = field(default_factory=current_utc_timestamp)
    completed_at: str | None = None

    def __post_init__(self) -> None:
        """Validate and normalise the report."""

        self.report_id = _required_text("report_id", self.report_id)
        self.brand_id = _required_text("brand_id", self.brand_id)
        self.subject_id = _required_text("subject_id", self.subject_id)
        self.summary = _optional_text(self.summary)
        self.ruleset_version = _optional_text(self.ruleset_version)

        self.subject_type = _coerce_enum(
            ReviewSubjectType,
            self.subject_type,
            "subject_type",
        )
        self.status = _coerce_enum(
            ComplianceStatus,
            self.status,
            "status",
        )

        converted_findings: list[ComplianceFinding] = []

        for finding in self.findings:
            if isinstance(finding, ComplianceFinding):
                converted_finding = finding
            elif isinstance(finding, dict):
                converted_finding = ComplianceFinding.from_dict(finding)
            else:
                raise ValueError("findings must contain ComplianceFinding objects.")

            if converted_finding.subject_id != self.subject_id:
                raise ValueError("Every finding must belong to the report subject.")

            if converted_finding.subject_type != self.subject_type:
                raise ValueError("Every finding must use the report subject type.")

            converted_findings.append(converted_finding)

        self.findings = converted_findings

        if not self.created_at.strip():
            self.created_at = current_utc_timestamp()

        if self.completed_at is not None:
            self.completed_at = self.completed_at.strip() or None

    def add_finding(self, finding: ComplianceFinding) -> None:
        """Add a finding that belongs to this report."""

        if finding.subject_id != self.subject_id:
            raise ValueError("The finding does not belong to the report subject.")

        if finding.subject_type != self.subject_type:
            raise ValueError("The finding does not use the report subject type.")

        self.findings.append(finding)

    def to_dict(self) -> dict[str, Any]:
        """Convert the report into a JSON-serialisable dictionary."""

        return {
            "report_id": self.report_id,
            "brand_id": self.brand_id,
            "subject_id": self.subject_id,
            "subject_type": self.subject_type.value,
            "status": self.status.value,
            "findings": [finding.to_dict() for finding in self.findings],
            "summary": self.summary,
            "ruleset_version": self.ruleset_version,
            "created_at": self.created_at,
            "completed_at": self.completed_at,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ComplianceReport:
        """Create a report from stored dictionary data."""

        return cls(**data)
