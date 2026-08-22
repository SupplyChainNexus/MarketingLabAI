"""Provider-neutral durable marketing workflow domain contracts."""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any, Protocol

from app.marketing_workflow.canonical import (
    CANONICALIZATION_VERSION,
    MLAI_CJ_1,
    MLAI_CJ_1_SCHEMA_VERSION,
    MLAI_CJ_2,
    MLAI_CJ_2_SCHEMA_VERSION,
    SCHEMA_VERSION,
    validate_timestamp,
)


class WorkflowState(StrEnum):
    DRAFT = "draft"
    PLANNED = "planned"
    AWAITING_APPROVAL = "awaiting_approval"
    APPROVED = "approved"
    RUNNING = "running"
    BLOCKED = "blocked"
    FAILED = "failed"
    COMPLETED = "completed"
    SUPERSEDED = "superseded"
    CANCELLED = "cancelled"


class FailureClass(StrEnum):
    VALIDATION_FAILED = "validation_failed"
    AUTH_REQUIRED = "auth_required"
    PROVIDER_ERROR = "provider_error"
    RATE_LIMITED = "rate_limited"
    POLICY_BLOCKED = "policy_blocked"
    BUDGET_BLOCKED = "budget_blocked"
    CONFLICT_DETECTED = "conflict_detected"
    NEEDS_HUMAN_DECISION = "needs_human_decision"


class ReceiptOutcome(StrEnum):
    APPLIED = "applied"
    REJECTED = "rejected"
    CONFLICT_DETECTED = "conflict_detected"


class ApprovalDecision(StrEnum):
    APPROVED = "approved"
    REJECTED = "rejected"


class ArtifactAvailability(StrEnum):
    RESERVED = "reserved"
    PERSISTED = "persisted"


TERMINAL_STATES = frozenset(
    {
        WorkflowState.FAILED,
        WorkflowState.COMPLETED,
        WorkflowState.SUPERSEDED,
        WorkflowState.CANCELLED,
    }
)

ALLOWED_TRANSITIONS = {
    WorkflowState.DRAFT: frozenset(
        {WorkflowState.PLANNED, WorkflowState.CANCELLED, WorkflowState.SUPERSEDED}
    ),
    WorkflowState.PLANNED: frozenset(
        {
            WorkflowState.DRAFT,
            WorkflowState.AWAITING_APPROVAL,
            WorkflowState.BLOCKED,
            WorkflowState.CANCELLED,
            WorkflowState.SUPERSEDED,
        }
    ),
    WorkflowState.AWAITING_APPROVAL: frozenset(
        {
            WorkflowState.PLANNED,
            WorkflowState.APPROVED,
            WorkflowState.BLOCKED,
            WorkflowState.CANCELLED,
            WorkflowState.SUPERSEDED,
        }
    ),
    WorkflowState.APPROVED: frozenset(
        {
            WorkflowState.AWAITING_APPROVAL,
            WorkflowState.RUNNING,
            WorkflowState.BLOCKED,
            WorkflowState.CANCELLED,
            WorkflowState.SUPERSEDED,
        }
    ),
    WorkflowState.RUNNING: frozenset(
        {
            WorkflowState.BLOCKED,
            WorkflowState.FAILED,
            WorkflowState.COMPLETED,
            WorkflowState.CANCELLED,
            WorkflowState.SUPERSEDED,
        }
    ),
    WorkflowState.BLOCKED: frozenset(
        {WorkflowState.FAILED, WorkflowState.CANCELLED, WorkflowState.SUPERSEDED}
    ),
    WorkflowState.FAILED: frozenset(),
    WorkflowState.COMPLETED: frozenset(),
    WorkflowState.SUPERSEDED: frozenset(),
    WorkflowState.CANCELLED: frozenset(),
}

EXECUTION_TRANSITIONS = frozenset(
    {
        (WorkflowState.APPROVED, WorkflowState.RUNNING),
        (WorkflowState.BLOCKED, WorkflowState.RUNNING),
        (WorkflowState.RUNNING, WorkflowState.COMPLETED),
    }
)

HIGH_IMPACT_ACTIONS = frozenset(
    {
        "paid_action",
        "spend_reservation",
        "spend_consumption",
        "publishing",
        "campaign_launch",
        "external_distribution",
        "learning_adoption",
        "policy_exception",
        "compliance_exception",
        "privacy_exception",
        "tenant_security_exception",
        "approval_exception",
        "hard_limit_exception",
        "external_state_mutation",
        "external_effect_cancellation",
        "external_effect_supersession",
    }
)
ORDINARY_ACTIONS = frozenset({"internal_planning", "operator_status_view"})


def required_text(name: str, value: str) -> str:
    if not isinstance(value, str):
        raise TypeError(f"{name} must be a string")
    selected = unicodedata.normalize("NFC", value.strip())
    if not selected:
        raise ValueError(f"{name} is required")
    if len(selected.encode("utf-8")) > 512 or any(
        ord(character) < 32 for character in selected
    ):
        raise ValueError(f"{name} must be bounded text without control characters")
    return selected


def opaque_actor_ref(value: str) -> str:
    selected = required_text("actor_ref", value)
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._:/-]{0,255}", selected):
        raise ValueError("actor_ref must be a bounded opaque reference")
    return selected


def positive_version(name: str, value: int) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        raise ValueError(f"{name} must be a positive integer")
    return value


@dataclass(frozen=True, slots=True)
class VersionedReference:
    kind: str
    id: str
    version: int

    def __post_init__(self) -> None:
        object.__setattr__(self, "kind", required_text("kind", self.kind))
        object.__setattr__(self, "id", required_text("id", self.id))
        positive_version("version", self.version)

    def to_dict(self) -> dict[str, Any]:
        return {"kind": self.kind, "id": self.id, "version": self.version}


@dataclass(frozen=True, slots=True)
class CanonicalArtifactReference:
    tenant_id: str
    brand_id: str
    artifact_id: str
    artifact_version: int
    repository_revision: str

    def __post_init__(self) -> None:
        for name in ("tenant_id", "brand_id", "artifact_id", "repository_revision"):
            object.__setattr__(self, name, required_text(name, getattr(self, name)))
        positive_version("artifact_version", self.artifact_version)

    def to_dict(self) -> dict[str, Any]:
        return {
            "tenant_id": self.tenant_id,
            "brand_id": self.brand_id,
            "artifact_id": self.artifact_id,
            "artifact_version": self.artifact_version,
            "repository_revision": self.repository_revision,
        }


@dataclass(frozen=True, slots=True)
class ArtifactProof:
    availability: ArtifactAvailability
    reference: CanonicalArtifactReference
    content_sha256: str | None = None

    def __post_init__(self) -> None:
        if self.availability is ArtifactAvailability.PERSISTED:
            digest = self.content_sha256 or ""
            if len(digest) != 64 or any(
                character not in "0123456789abcdef" for character in digest
            ):
                raise ValueError("persisted artifact proof requires lowercase SHA-256")
        elif self.content_sha256 is not None:
            raise ValueError("reserved artifact proof cannot claim a content digest")


class CanonicalArtifactAvailability(Protocol):
    """Resolve valid local persistence proof or return no proof.

    Implementations must return ``None`` for missing, inaccessible,
    superseded, integrity-invalid, or cross-tenant/cross-brand references.
    """

    def prove(
        self,
        *,
        tenant_id: str,
        brand_id: str,
        reference: CanonicalArtifactReference,
    ) -> ArtifactProof | None: ...


class WorkflowAuthority(Protocol):
    def permits(
        self,
        *,
        actor_ref: str,
        tenant_id: str,
        brand_id: str,
        action: str,
        workflow_version: int,
    ) -> bool: ...


@dataclass(frozen=True, slots=True)
class MarketingWorkflow:
    workflow_id: str
    tenant_id: str
    brand_id: str
    campaign_plan: VersionedReference
    state: WorkflowState
    failure_class: FailureClass | None
    version: int
    created_at: str
    updated_at: str
    marketing_brief: VersionedReference | None = None
    predecessor_workflow_id: str | None = None
    successor_workflow_id: str | None = None
    blocked_resume_state: WorkflowState | None = None
    canonical_artifact_ref: CanonicalArtifactReference | None = None

    def __post_init__(self) -> None:
        for name in ("workflow_id", "tenant_id", "brand_id"):
            object.__setattr__(self, name, required_text(name, getattr(self, name)))
        if self.campaign_plan.kind != "campaign_plan":
            raise ValueError("campaign_plan must be a Campaign Plan reference")
        if self.marketing_brief and self.marketing_brief.kind != "marketing_brief":
            raise ValueError("marketing_brief must be a Marketing Brief reference")
        positive_version("version", self.version)
        validate_timestamp(self.created_at)
        validate_timestamp(self.updated_at)
        if self.state is WorkflowState.BLOCKED and self.blocked_resume_state is None:
            raise ValueError("blocked workflow requires a resume state")
        if (
            self.state is not WorkflowState.BLOCKED
            and self.blocked_resume_state is not None
        ):
            raise ValueError("only blocked workflow may retain a resume state")
        if self.state in {WorkflowState.BLOCKED, WorkflowState.FAILED}:
            if self.failure_class is None:
                raise ValueError("blocked and failed workflows require a failure class")
        elif self.failure_class is not None:
            raise ValueError(
                "failure class is only retained for blocked or failed state"
            )


@dataclass(frozen=True, slots=True)
class WorkflowCommand:
    request_id: str
    tenant_id: str
    brand_id: str
    workflow_id: str
    expected_workflow_version: int
    command_kind: str
    caller_idempotency_key: str
    actor_ref: str
    requested_at: str
    safe_command: dict[str, Any]
    safe_command_schema_version: int = 1

    def __post_init__(self) -> None:
        for name in (
            "request_id",
            "tenant_id",
            "brand_id",
            "workflow_id",
            "command_kind",
            "actor_ref",
        ):
            value = getattr(self, name)
            if name == "actor_ref":
                value = opaque_actor_ref(value)
            else:
                value = required_text(name, value)
            object.__setattr__(self, name, value)
        positive_version("expected_workflow_version", self.expected_workflow_version)
        validate_timestamp(self.requested_at)
        if not isinstance(self.safe_command, dict):
            raise TypeError("safe_command must be an object")
        if type(self.safe_command_schema_version) is not int:
            raise TypeError("safe_command_schema_version must be an integer")

    @property
    def request_workflow_id(self) -> str:
        """Immutable caller-supplied workflow identity for MLAI-CJ-2."""

        return self.workflow_id


@dataclass(frozen=True, slots=True)
class CommandReceipt:
    receipt_id: str
    request_id: str
    request_hash: str
    tenant_id: str
    brand_id: str
    request_workflow_id: str
    workflow_version_before: int
    workflow_version_after: int
    command_kind: str
    idempotency_key_sha256: str
    actor_ref: str
    outcome: ReceiptOutcome
    failure_class: FailureClass | None
    conflicts_with_receipt_id: str | None
    requested_at: str
    recorded_at: str
    safe_result_refs: tuple[VersionedReference, ...] = ()
    authoritative_workflow_id: str | None = None
    canonicalization_version: str = CANONICALIZATION_VERSION
    schema_version: int = SCHEMA_VERSION
    canonical_json: str = ""
    receipt_sha256: str = ""

    @property
    def workflow_id(self) -> str:
        """Compatibility view; canonical identity is request_workflow_id."""

        return self.request_workflow_id


@dataclass(frozen=True, slots=True)
class WorkflowApproval:
    approval_id: str
    tenant_id: str
    brand_id: str
    workflow_id: str
    workflow_version: int
    action: str
    decision: ApprovalDecision
    requested_by_actor_ref: str
    decided_by_actor_ref: str
    decided_at: str

    def __post_init__(self) -> None:
        for name in (
            "approval_id",
            "tenant_id",
            "brand_id",
            "workflow_id",
            "action",
            "requested_by_actor_ref",
            "decided_by_actor_ref",
        ):
            value = getattr(self, name)
            if name in {"requested_by_actor_ref", "decided_by_actor_ref"}:
                value = opaque_actor_ref(value)
            else:
                value = required_text(name, value)
            object.__setattr__(self, name, value)
        positive_version("workflow_version", self.workflow_version)
        validate_timestamp(self.decided_at)


@dataclass(frozen=True, slots=True)
class WorkflowEvidence:
    evidence_id: str
    tenant_id: str
    brand_id: str
    workflow_id: str
    workflow_version: int
    sequence: int
    predecessor_sha256: str
    evidence_sha256: str
    canonical_json: str


@dataclass(frozen=True, slots=True)
class CommandEvaluation:
    outcome: ReceiptOutcome
    failure_class: FailureClass | None
    reason_code: str
    evidence_failure_class: FailureClass | None = None
    target_state: WorkflowState | None = None
    blocked_resume_state: WorkflowState | None = None
    successor_workflow_id: str | None = None
    canonical_artifact_ref: CanonicalArtifactReference | None = None
    artifact_proof: ArtifactProof | None = None
    approval: WorkflowApproval | None = None
    safe_result_refs: tuple[VersionedReference, ...] = ()
    advance_workflow_version: bool = False
    creates_workflow: bool = False


@dataclass(frozen=True, slots=True)
class OperatorStatus:
    workflow_id: str
    state: WorkflowState
    workflow_version: int
    next_action: str | None
    blocked_reason: FailureClass | None
    retry_available: bool
    required_approval: str | None
    evidence_available: bool
    technical_details: dict[str, Any] = field(default_factory=dict)


def envelope_versions(record_kind: str) -> dict[str, Any]:
    if record_kind == "workflow_evidence":
        return {
            "canonicalization_version": MLAI_CJ_1,
            "schema_version": MLAI_CJ_1_SCHEMA_VERSION,
            "record_kind": record_kind,
        }
    return {
        "canonicalization_version": MLAI_CJ_2,
        "schema_version": MLAI_CJ_2_SCHEMA_VERSION,
        "record_kind": record_kind,
    }
