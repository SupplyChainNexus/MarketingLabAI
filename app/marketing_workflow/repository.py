"""Atomic SQLite/PostgreSQL-compatible durable workflow persistence."""

from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import replace
from typing import Any
from uuid import uuid4

from app.database.connection import SQLiteDatabase
from app.marketing_workflow.canonical import (
    MLAI_CJ_1,
    MLAI_CJ_1_SCHEMA_VERSION,
    MLAI_CJ_2,
    MLAI_CJ_2_SCHEMA_VERSION,
    assert_privacy_safe,
    canonical_json,
    idempotency_key_sha256,
    record_sha256,
    sanitized_sha256,
    utc_timestamp,
    validate_timestamp,
)
from app.marketing_workflow.models import (
    ALLOWED_TRANSITIONS,
    EXECUTION_TRANSITIONS,
    TERMINAL_STATES,
    ApprovalDecision,
    CommandEvaluation,
    CommandReceipt,
    FailureClass,
    MarketingWorkflow,
    ReceiptOutcome,
    VersionedReference,
    WorkflowApproval,
    WorkflowCommand,
    WorkflowEvidence,
    WorkflowState,
    envelope_versions,
    positive_version,
    required_text,
)

GENESIS_PREDECESSOR = "0" * 64


class WorkflowAccessDeniedError(PermissionError):
    """Non-disclosing tenant/brand-scoped workflow denial."""


class OptimisticWorkflowConflictError(RuntimeError):
    """Raised when the persisted workflow version changes concurrently."""


def new_workflow_id() -> str:
    """Return a provider-neutral opaque workflow identifier."""

    return f"mwf_{uuid4().hex}"


class MarketingWorkflowRepository:
    """Own durable workflow state and atomic authority-changing writes."""

    def __init__(self, database: SQLiteDatabase | None = None) -> None:
        self.database = database or SQLiteDatabase()

    def create(
        self, command: WorkflowCommand, workflow: MarketingWorkflow
    ) -> CommandReceipt:
        """Persist a new workflow through a durable idempotent command."""

        if workflow.state is not WorkflowState.DRAFT or workflow.version != 1:
            raise ValueError("new workflows must begin in draft at version 1")
        if (
            command.tenant_id != workflow.tenant_id
            or command.brand_id != workflow.brand_id
            or command.workflow_id != workflow.workflow_id
            or command.command_kind != "create_workflow"
        ):
            raise ValueError("creation command does not match workflow identity")
        request_envelope, key_digest = self._request_envelope(command)
        request_hash = record_sha256("command_request", request_envelope)
        with self.database.transaction() as connection:
            brand_locked = connection.execute(
                """
                UPDATE brands SET brand_id = brand_id
                WHERE tenant_id = ? AND brand_id = ?
                """,
                (workflow.tenant_id, workflow.brand_id),
            )
            if brand_locked.rowcount != 1:
                raise WorkflowAccessDeniedError("workflow references are unavailable")
            if workflow.predecessor_workflow_id:
                locked = connection.execute(
                    """
                    UPDATE marketing_workflows SET version = version
                    WHERE tenant_id = ? AND brand_id = ? AND workflow_id = ?
                      AND state = 'failed'
                    """,
                    (
                        workflow.tenant_id,
                        workflow.brand_id,
                        workflow.predecessor_workflow_id,
                    ),
                )
            else:
                locked = brand_locked
            if locked.rowcount != 1:
                raise WorkflowAccessDeniedError("workflow references are unavailable")
            if workflow.predecessor_workflow_id:
                conflict_scope = self._recovery_conflict_scope(
                    connection,
                    command=command,
                    key_digest=key_digest,
                )
                if conflict_scope is not None:
                    replay = self._recovery_conflict_replay(
                        connection,
                        command=command,
                        key_digest=key_digest,
                        request_hash=request_hash,
                    )
                    if replay is not None:
                        return self._receipt_by_id(
                            connection, str(replay["conflict_receipt_id"])
                        )
                    authoritative_id = str(conflict_scope["authoritative_workflow_id"])
                    authoritative_row = self._lock_workflow_row(
                        connection,
                        tenant_id=workflow.tenant_id,
                        brand_id=workflow.brand_id,
                        workflow_id=authoritative_id,
                    )
                    if authoritative_row is None:
                        raise RuntimeError(
                            "recovery conflict scope references an unavailable successor"
                        )
                    authoritative = self._workflow_from_row(authoritative_row)
                    authoritative_receipt = self._receipt_by_id(
                        connection,
                        str(conflict_scope["authoritative_receipt_id"]),
                    )
                    conflict = self._persist_result(
                        connection,
                        command=command,
                        workflow=authoritative,
                        request_hash=request_hash,
                        key_digest=key_digest,
                        evaluation=self._recovery_conflict_evaluation(
                            authoritative, authoritative_receipt
                        ),
                        conflicts_with_receipt_id=authoritative_receipt.receipt_id,
                        establish_scope=False,
                        authoritative_workflow_id=authoritative.workflow_id,
                    )
                    self._insert_recovery_conflict_replay(
                        connection,
                        command=command,
                        predecessor_workflow_id=workflow.predecessor_workflow_id,
                        request_hash=request_hash,
                        key_digest=key_digest,
                        conflict_receipt=conflict,
                    )
                    return conflict
                recovery = self._recovery_scope(
                    connection,
                    tenant_id=workflow.tenant_id,
                    brand_id=workflow.brand_id,
                    predecessor_workflow_id=workflow.predecessor_workflow_id,
                )
                if recovery is not None:
                    original = self._receipt_by_id(
                        connection, str(recovery["original_receipt_id"])
                    )
                    if str(recovery["request_hash"]) == request_hash:
                        return original
                    successor_id = str(recovery["successor_workflow_id"])
                    successor_row = self._lock_workflow_row(
                        connection,
                        tenant_id=workflow.tenant_id,
                        brand_id=workflow.brand_id,
                        workflow_id=successor_id,
                    )
                    if successor_row is None:
                        raise RuntimeError(
                            "recovery scope references an unavailable successor"
                        )
                    persisted = self._workflow_from_row(successor_row)
                    conflict = self._persist_result(
                        connection,
                        command=command,
                        workflow=persisted,
                        request_hash=request_hash,
                        key_digest=key_digest,
                        evaluation=self._recovery_conflict_evaluation(
                            persisted, original
                        ),
                        conflicts_with_receipt_id=original.receipt_id,
                        establish_scope=False,
                        authoritative_workflow_id=successor_id,
                    )
                    self._insert_recovery_conflict_scope(
                        connection,
                        command=command,
                        predecessor_workflow_id=workflow.predecessor_workflow_id,
                        request_hash=request_hash,
                        key_digest=key_digest,
                        authoritative_workflow_id=successor_id,
                        authoritative_receipt_id=original.receipt_id,
                        conflict_receipt=conflict,
                    )
                    return conflict
            scope = self._idempotency_scope(
                connection, command=command, key_digest=key_digest
            )
            if scope is not None:
                original = self._receipt_by_id(
                    connection, str(scope["original_receipt_id"])
                )
                if str(scope["request_hash"]) == request_hash:
                    return original
                persisted = self._require_workflow(connection, command)
                return self._persist_result(
                    connection,
                    command=command,
                    workflow=persisted,
                    request_hash=request_hash,
                    key_digest=key_digest,
                    evaluation=CommandEvaluation(
                        outcome=ReceiptOutcome.CONFLICT_DETECTED,
                        failure_class=FailureClass.CONFLICT_DETECTED,
                        reason_code="idempotency_input_changed",
                    ),
                    conflicts_with_receipt_id=original.receipt_id,
                    establish_scope=False,
                )
            existing_row = self._workflow_row(
                connection,
                tenant_id=workflow.tenant_id,
                brand_id=workflow.brand_id,
                workflow_id=workflow.workflow_id,
            )
            if existing_row is not None:
                authority = connection.execute(
                    """
                    SELECT original_receipt_id
                    FROM workflow_idempotency_scopes
                    WHERE tenant_id = ? AND brand_id = ? AND workflow_id = ?
                      AND command_kind = 'create_workflow'
                    ORDER BY created_at, original_receipt_id LIMIT 1
                    """,
                    (
                        workflow.tenant_id,
                        workflow.brand_id,
                        workflow.workflow_id,
                    ),
                ).fetchone()
                if authority is None:
                    raise RuntimeError(
                        "existing workflow lacks an authoritative creation receipt"
                    )
                original = self._receipt_by_id(
                    connection, str(authority["original_receipt_id"])
                )
                persisted = self._workflow_from_row(existing_row)
                return self._persist_result(
                    connection,
                    command=command,
                    workflow=persisted,
                    request_hash=request_hash,
                    key_digest=key_digest,
                    evaluation=CommandEvaluation(
                        outcome=ReceiptOutcome.CONFLICT_DETECTED,
                        failure_class=FailureClass.CONFLICT_DETECTED,
                        reason_code="workflow_identifier_already_exists",
                        safe_result_refs=(
                            VersionedReference(
                                "marketing_workflow", workflow.workflow_id, 1
                            ),
                        ),
                    ),
                    conflicts_with_receipt_id=original.receipt_id,
                    establish_scope=False,
                )
            self._validate_owned_references(connection, workflow)
            connection.execute(
                """
                INSERT INTO marketing_workflows (
                    workflow_id, tenant_id, brand_id, campaign_plan_id,
                    campaign_plan_version, marketing_brief_id,
                    marketing_brief_version, predecessor_workflow_id,
                    successor_workflow_id, state, failure_class, version,
                    blocked_resume_state,
                    canonical_artifact_ref_json, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                self._workflow_values(workflow),
            )
            receipt = self._persist_result(
                connection,
                command=command,
                workflow=workflow,
                request_hash=request_hash,
                key_digest=key_digest,
                evaluation=CommandEvaluation(
                    outcome=ReceiptOutcome.APPLIED,
                    failure_class=None,
                    reason_code="workflow_created",
                    safe_result_refs=(
                        VersionedReference(
                            "marketing_workflow", workflow.workflow_id, 1
                        ),
                    ),
                    creates_workflow=True,
                ),
                conflicts_with_receipt_id=None,
                establish_scope=True,
            )
            if workflow.predecessor_workflow_id:
                connection.execute(
                    """
                    INSERT INTO workflow_recovery_scopes (
                        tenant_id, brand_id, predecessor_workflow_id,
                        successor_workflow_id, request_hash,
                        original_receipt_id, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        workflow.tenant_id,
                        workflow.brand_id,
                        workflow.predecessor_workflow_id,
                        workflow.workflow_id,
                        request_hash,
                        receipt.receipt_id,
                        receipt.recorded_at,
                    ),
                )
            return receipt

    def get(
        self, *, tenant_id: str, brand_id: str, workflow_id: str
    ) -> MarketingWorkflow:
        """Return only an exactly tenant-and-brand-scoped workflow."""

        with self.database.connection() as connection:
            row = self._workflow_row(
                connection,
                tenant_id=tenant_id,
                brand_id=brand_id,
                workflow_id=workflow_id,
            )
        if row is None:
            raise WorkflowAccessDeniedError("workflow is unavailable")
        return self._workflow_from_row(row)

    def execute(
        self,
        command: WorkflowCommand,
        evaluator: Callable[[MarketingWorkflow], CommandEvaluation],
    ) -> CommandReceipt:
        """Evaluate and persist a command, receipt and evidence in one transaction."""

        request_envelope, key_digest = self._request_envelope(command)
        request_hash = record_sha256("command_request", request_envelope)
        with self.database.transaction() as connection:
            locked = connection.execute(
                """
                UPDATE marketing_workflows SET version = version
                WHERE tenant_id = ? AND brand_id = ? AND workflow_id = ?
                """,
                (command.tenant_id, command.brand_id, command.workflow_id),
            )
            if locked.rowcount != 1:
                raise WorkflowAccessDeniedError("workflow is unavailable")
            scope = self._idempotency_scope(
                connection, command=command, key_digest=key_digest
            )
            if scope is not None:
                original = self._receipt_by_id(
                    connection, str(scope["original_receipt_id"])
                )
                if str(scope["request_hash"]) == request_hash:
                    return original
                workflow = self._require_workflow(connection, command)
                return self._persist_result(
                    connection,
                    command=command,
                    workflow=workflow,
                    request_hash=request_hash,
                    key_digest=key_digest,
                    evaluation=CommandEvaluation(
                        outcome=ReceiptOutcome.CONFLICT_DETECTED,
                        failure_class=FailureClass.CONFLICT_DETECTED,
                        reason_code="idempotency_input_changed",
                    ),
                    conflicts_with_receipt_id=original.receipt_id,
                    establish_scope=False,
                )

            workflow = self._require_workflow(connection, command)
            evaluation = evaluator(workflow)
            return self._persist_result(
                connection,
                command=command,
                workflow=workflow,
                request_hash=request_hash,
                key_digest=key_digest,
                evaluation=evaluation,
                conflicts_with_receipt_id=None,
                establish_scope=True,
            )

    def list_evidence(
        self, *, tenant_id: str, brand_id: str, workflow_id: str
    ) -> tuple[WorkflowEvidence, ...]:
        self.get(tenant_id=tenant_id, brand_id=brand_id, workflow_id=workflow_id)
        with self.database.connection() as connection:
            rows = connection.execute(
                """
                SELECT evidence_id, tenant_id, brand_id, workflow_id,
                       workflow_version, sequence, predecessor_sha256,
                       evidence_sha256, canonical_json
                FROM workflow_evidence
                WHERE tenant_id = ? AND brand_id = ? AND workflow_id = ?
                ORDER BY sequence
                """,
                (tenant_id, brand_id, workflow_id),
            ).fetchall()
        return tuple(WorkflowEvidence(**dict(row)) for row in rows)

    def approved_for(
        self,
        *,
        tenant_id: str,
        brand_id: str,
        workflow_id: str,
        workflow_version: int,
        action: str,
    ) -> WorkflowApproval | None:
        """Return an immutable approval for the exact version and action."""

        approval = self.approval_for(
            tenant_id=tenant_id,
            brand_id=brand_id,
            workflow_id=workflow_id,
            workflow_version=workflow_version,
            action=action,
        )
        if approval is None or approval.decision is not ApprovalDecision.APPROVED:
            return None
        return approval

    def approval_for(
        self,
        *,
        tenant_id: str,
        brand_id: str,
        workflow_id: str,
        workflow_version: int,
        action: str,
    ) -> WorkflowApproval | None:
        """Return the single immutable decision for an exact binding."""

        self.get(tenant_id=tenant_id, brand_id=brand_id, workflow_id=workflow_id)
        with self.database.connection() as connection:
            row = connection.execute(
                """
                SELECT * FROM workflow_approvals
                WHERE tenant_id = ? AND brand_id = ? AND workflow_id = ?
                  AND workflow_version = ? AND action = ?
                LIMIT 1
                """,
                (tenant_id, brand_id, workflow_id, workflow_version, action),
            ).fetchone()
        if row is None:
            return None
        return WorkflowApproval(
            approval_id=str(row["approval_id"]),
            tenant_id=str(row["tenant_id"]),
            brand_id=str(row["brand_id"]),
            workflow_id=str(row["workflow_id"]),
            workflow_version=int(row["workflow_version"]),
            action=str(row["action"]),
            decision=ApprovalDecision(str(row["decision"])),
            requested_by_actor_ref=str(row["requested_by_actor_ref"]),
            decided_by_actor_ref=str(row["decided_by_actor_ref"]),
            decided_at=str(row["decided_at"]),
        )

    def _persist_result(
        self,
        connection,
        *,
        command: WorkflowCommand,
        workflow: MarketingWorkflow,
        request_hash: str,
        key_digest: str,
        evaluation: CommandEvaluation,
        conflicts_with_receipt_id: str | None,
        establish_scope: bool,
        authoritative_workflow_id: str | None = None,
    ) -> CommandReceipt:
        self._validate_evaluation(workflow, evaluation)
        before_version = 0 if evaluation.creates_workflow else workflow.version
        updated = workflow
        if evaluation.outcome is ReceiptOutcome.APPLIED:
            if evaluation.failure_class is not None:
                raise ValueError("applied evaluation cannot contain a failure")
        if evaluation.advance_workflow_version:
            if (
                evaluation.outcome is not ReceiptOutcome.APPLIED
                or evaluation.target_state is None
            ):
                raise ValueError(
                    "workflow version advancement requires an applied target"
                )
            if evaluation.successor_workflow_id:
                successor = self._workflow_row(
                    connection,
                    tenant_id=workflow.tenant_id,
                    brand_id=workflow.brand_id,
                    workflow_id=evaluation.successor_workflow_id,
                )
                if (
                    successor is None
                    or evaluation.successor_workflow_id == workflow.workflow_id
                ):
                    raise ValueError("successor workflow is unavailable")
            updated = replace(
                workflow,
                state=evaluation.target_state,
                failure_class=evaluation.evidence_failure_class,
                version=workflow.version + 1,
                updated_at=utc_timestamp(),
                blocked_resume_state=evaluation.blocked_resume_state,
                successor_workflow_id=(
                    evaluation.successor_workflow_id or workflow.successor_workflow_id
                ),
                canonical_artifact_ref=(
                    evaluation.canonical_artifact_ref or workflow.canonical_artifact_ref
                ),
            )
            cursor = connection.execute(
                """
                UPDATE marketing_workflows
                SET state = ?, failure_class = ?, version = ?, blocked_resume_state = ?,
                    successor_workflow_id = ?, canonical_artifact_ref_json = ?,
                    updated_at = ?
                WHERE tenant_id = ? AND brand_id = ? AND workflow_id = ?
                  AND version = ?
                """,
                (
                    updated.state.value,
                    updated.failure_class.value if updated.failure_class else None,
                    updated.version,
                    (
                        updated.blocked_resume_state.value
                        if updated.blocked_resume_state
                        else None
                    ),
                    updated.successor_workflow_id,
                    self._artifact_json(updated),
                    updated.updated_at,
                    updated.tenant_id,
                    updated.brand_id,
                    updated.workflow_id,
                    before_version,
                ),
            )
            if cursor.rowcount != 1:
                raise OptimisticWorkflowConflictError("workflow version changed")

        recorded_at = utc_timestamp()
        receipt_id = f"mwr_{uuid4().hex}"
        proof_id = f"mwp_{uuid4().hex}" if evaluation.artifact_proof else None
        proof_ref = (
            VersionedReference("artifact_proof", proof_id, 1) if proof_id else None
        )
        result_refs = evaluation.safe_result_refs + (
            (proof_ref,) if proof_ref is not None else ()
        )
        receipt_envelope = {
            **envelope_versions("command_receipt"),
            "receipt_id": receipt_id,
            "request_id": command.request_id,
            "request_hash": request_hash,
            "tenant_id": command.tenant_id,
            "brand_id": command.brand_id,
            "request_workflow_id": command.request_workflow_id,
            "workflow_version_before": before_version,
            "workflow_version_after": updated.version,
            "command_kind": command.command_kind,
            "idempotency_key_sha256": key_digest,
            "actor_ref": command.actor_ref,
            "outcome": evaluation.outcome.value,
            "failure_class": (
                evaluation.failure_class.value if evaluation.failure_class else None
            ),
            "conflicts_with_receipt_id": conflicts_with_receipt_id,
            "requested_at": validate_timestamp(command.requested_at),
            "recorded_at": recorded_at,
            "safe_result_refs": self._sorted_refs(result_refs),
        }
        if authoritative_workflow_id is not None:
            if authoritative_workflow_id == command.request_workflow_id:
                raise ValueError(
                    "authoritative_workflow_id must be omitted when identities match"
                )
            receipt_envelope["authoritative_workflow_id"] = authoritative_workflow_id
        receipt_json = canonical_json(receipt_envelope)
        receipt_digest = record_sha256("command_receipt", receipt_envelope)
        connection.execute(
            """
            INSERT INTO workflow_command_receipts (
                receipt_id, tenant_id, brand_id, workflow_id, command_kind,
                idempotency_key_sha256, request_hash, receipt_hash, outcome,
                canonical_json, recorded_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                receipt_id,
                command.tenant_id,
                command.brand_id,
                workflow.workflow_id,
                command.command_kind,
                key_digest,
                request_hash,
                receipt_digest,
                evaluation.outcome.value,
                receipt_json,
                recorded_at,
            ),
        )
        if evaluation.approval is not None:
            self._insert_approval(connection, evaluation.approval)
        if establish_scope:
            connection.execute(
                """
                INSERT INTO workflow_idempotency_scopes (
                    tenant_id, brand_id, workflow_id, command_kind,
                    idempotency_key_sha256, request_hash, original_receipt_id,
                    created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    command.tenant_id,
                    command.brand_id,
                    command.workflow_id,
                    command.command_kind,
                    key_digest,
                    request_hash,
                    receipt_id,
                    recorded_at,
                ),
            )
        evidence = self._append_evidence(
            connection,
            workflow=updated,
            actor_ref=command.actor_ref,
            action=command.command_kind,
            from_state=(None if evaluation.creates_workflow else workflow.state),
            to_state=(
                updated.state if evaluation.outcome is ReceiptOutcome.APPLIED else None
            ),
            failure_class=(
                evaluation.evidence_failure_class or evaluation.failure_class
            ),
            command_receipt_id=receipt_id,
            approval=evaluation.approval,
            artifact_ref=proof_ref,
            reason_code=evaluation.reason_code,
            sanitized_input_sha256=request_hash,
            sanitized_output_sha256=sanitized_sha256(
                {
                    "outcome": evaluation.outcome.value,
                    "failure_class": (
                        evaluation.failure_class.value
                        if evaluation.failure_class
                        else None
                    ),
                    "workflow_version_after": updated.version,
                    "safe_result_refs": self._sorted_refs(result_refs),
                }
            ),
        )
        if evaluation.artifact_proof is not None and proof_id is not None:
            self._insert_artifact_proof(
                connection,
                proof_id=proof_id,
                proof=evaluation.artifact_proof,
                workflow=updated,
                receipt_id=receipt_id,
                evidence_id=evidence.evidence_id,
                proved_at=recorded_at,
            )
        return self._receipt_from_envelope(
            receipt_envelope, receipt_json, receipt_digest
        )

    @staticmethod
    def _validate_evaluation(
        workflow: MarketingWorkflow, evaluation: CommandEvaluation
    ) -> None:
        """Fail closed if a caller attempts to bypass aggregate invariants."""

        if evaluation.outcome is ReceiptOutcome.APPLIED:
            if evaluation.failure_class is not None:
                raise ValueError("applied evaluation cannot contain a failure")
        elif evaluation.advance_workflow_version or evaluation.approval is not None:
            raise ValueError("rejected evaluation cannot change authority")
        if evaluation.creates_workflow:
            if (
                evaluation.outcome is not ReceiptOutcome.APPLIED
                or evaluation.advance_workflow_version
                or evaluation.approval is not None
            ):
                raise ValueError("workflow creation evaluation is invalid")
            return
        if not evaluation.advance_workflow_version:
            if evaluation.outcome is ReceiptOutcome.APPLIED:
                approval = evaluation.approval
                if approval is None:
                    raise ValueError(
                        "non-transition application requires an approval record"
                    )
                if (
                    approval.tenant_id != workflow.tenant_id
                    or approval.brand_id != workflow.brand_id
                    or approval.workflow_id != workflow.workflow_id
                    or approval.workflow_version != workflow.version
                ):
                    raise ValueError("approval binding does not match workflow")
            return
        target = evaluation.target_state
        if target is None or workflow.state in TERMINAL_STATES:
            raise ValueError("workflow transition is not permitted")
        allowed = ALLOWED_TRANSITIONS[workflow.state]
        if workflow.state is WorkflowState.BLOCKED and workflow.blocked_resume_state:
            allowed = allowed | frozenset({workflow.blocked_resume_state})
        if target not in allowed:
            raise ValueError("workflow transition is not permitted")
        if target is WorkflowState.SUPERSEDED and not evaluation.successor_workflow_id:
            raise ValueError("supersession requires an immutable successor reference")
        if (workflow.state, target) in EXECUTION_TRANSITIONS:
            if (
                evaluation.canonical_artifact_ref is None
                or evaluation.artifact_proof is None
                or evaluation.artifact_proof.reference
                != evaluation.canonical_artifact_ref
            ):
                raise ValueError(
                    "execution transition requires artifact proof reference"
                )
        elif evaluation.artifact_proof is not None:
            raise ValueError("artifact proof is only valid for execution transitions")
        if target in {WorkflowState.BLOCKED, WorkflowState.FAILED}:
            if evaluation.evidence_failure_class is None:
                raise ValueError("blocked or failed transition requires classification")
        elif evaluation.evidence_failure_class is not None:
            raise ValueError("failure classification does not match target state")
        if evaluation.approval is not None:
            raise ValueError("approval recording cannot also transition state")

    def _append_evidence(
        self,
        connection,
        *,
        workflow: MarketingWorkflow,
        actor_ref: str,
        action: str,
        from_state: WorkflowState | None,
        to_state: WorkflowState | None,
        failure_class: FailureClass | None,
        command_receipt_id: str | None,
        approval: WorkflowApproval | None,
        artifact_ref,
        reason_code: str,
        sanitized_input_sha256: str,
        sanitized_output_sha256: str,
    ) -> WorkflowEvidence:
        previous = connection.execute(
            """
            SELECT sequence, evidence_sha256 FROM workflow_evidence
            WHERE tenant_id = ? AND brand_id = ? AND workflow_id = ?
            ORDER BY sequence DESC LIMIT 1
            """,
            (workflow.tenant_id, workflow.brand_id, workflow.workflow_id),
        ).fetchone()
        sequence = 1 if previous is None else int(previous["sequence"]) + 1
        predecessor = (
            GENESIS_PREDECESSOR
            if previous is None
            else str(previous["evidence_sha256"])
        )
        evidence_id = f"mwe_{uuid4().hex}"
        envelope = {
            **envelope_versions("workflow_evidence"),
            "evidence_id": evidence_id,
            "tenant_id": workflow.tenant_id,
            "brand_id": workflow.brand_id,
            "workflow_id": workflow.workflow_id,
            "workflow_version": workflow.version,
            "sequence": sequence,
            "predecessor_sha256": predecessor,
            "actor_ref": actor_ref,
            "action": action,
            "occurred_at": utc_timestamp(),
            "from_state": from_state.value if from_state else None,
            "to_state": to_state.value if to_state else None,
            "failure_class": failure_class.value if failure_class else None,
            "command_receipt_id": command_receipt_id,
            "approval_ref": (
                VersionedReference(
                    "workflow_approval",
                    approval.approval_id,
                    approval.workflow_version,
                ).to_dict()
                if approval
                else None
            ),
            "artifact_ref": artifact_ref.to_dict() if artifact_ref else None,
            "reason_code": reason_code,
            "safe_source_refs": [],
            "sanitized_input_sha256": sanitized_input_sha256,
            "sanitized_output_sha256": sanitized_output_sha256,
        }
        evidence_json = canonical_json(envelope)
        evidence_digest = record_sha256("workflow_evidence", envelope)
        connection.execute(
            """
            INSERT INTO workflow_evidence (
                evidence_id, tenant_id, brand_id, workflow_id,
                workflow_version, sequence, predecessor_sha256,
                evidence_sha256, canonical_json, occurred_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                evidence_id,
                workflow.tenant_id,
                workflow.brand_id,
                workflow.workflow_id,
                workflow.version,
                sequence,
                predecessor,
                evidence_digest,
                evidence_json,
                envelope["occurred_at"],
            ),
        )
        return WorkflowEvidence(
            evidence_id,
            workflow.tenant_id,
            workflow.brand_id,
            workflow.workflow_id,
            workflow.version,
            sequence,
            predecessor,
            evidence_digest,
            evidence_json,
        )

    def _insert_approval(self, connection, approval: WorkflowApproval) -> None:
        payload = canonical_json(
            {
                "approval_id": approval.approval_id,
                "tenant_id": approval.tenant_id,
                "brand_id": approval.brand_id,
                "workflow_id": approval.workflow_id,
                "workflow_version": approval.workflow_version,
                "action": approval.action,
                "decision": approval.decision.value,
                "requested_by_actor_ref": approval.requested_by_actor_ref,
                "decided_by_actor_ref": approval.decided_by_actor_ref,
                "decided_at": validate_timestamp(approval.decided_at),
            }
        )
        connection.execute(
            """
            INSERT INTO workflow_approvals (
                approval_id, tenant_id, brand_id, workflow_id,
                workflow_version, action, decision, requested_by_actor_ref,
                decided_by_actor_ref, decided_at, canonical_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                approval.approval_id,
                approval.tenant_id,
                approval.brand_id,
                approval.workflow_id,
                approval.workflow_version,
                approval.action,
                approval.decision.value,
                approval.requested_by_actor_ref,
                approval.decided_by_actor_ref,
                approval.decided_at,
                payload,
            ),
        )

    @staticmethod
    def _insert_artifact_proof(
        connection,
        *,
        proof_id: str,
        proof,
        workflow: MarketingWorkflow,
        receipt_id: str,
        evidence_id: str,
        proved_at: str,
    ) -> None:
        reference = proof.reference
        payload = canonical_json(
            {
                "schema_version": 1,
                "proof_id": proof_id,
                "tenant_id": workflow.tenant_id,
                "brand_id": workflow.brand_id,
                "workflow_id": workflow.workflow_id,
                "workflow_version": workflow.version,
                "command_receipt_id": receipt_id,
                "evidence_id": evidence_id,
                "availability": proof.availability.value,
                "artifact_id": reference.artifact_id,
                "artifact_version": reference.artifact_version,
                "repository_revision": reference.repository_revision,
                "content_sha256": proof.content_sha256,
                "proved_at": proved_at,
            }
        )
        connection.execute(
            """
            INSERT INTO workflow_artifact_proofs (
                proof_id, tenant_id, brand_id, workflow_id, workflow_version,
                command_receipt_id, evidence_id, availability, artifact_id,
                artifact_version, repository_revision, content_sha256,
                proved_at, canonical_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                proof_id,
                workflow.tenant_id,
                workflow.brand_id,
                workflow.workflow_id,
                workflow.version,
                receipt_id,
                evidence_id,
                proof.availability.value,
                reference.artifact_id,
                reference.artifact_version,
                reference.repository_revision,
                proof.content_sha256,
                proved_at,
                payload,
            ),
        )

    def _request_envelope(self, command: WorkflowCommand) -> tuple[dict[str, Any], str]:
        for name in (
            "request_id",
            "tenant_id",
            "brand_id",
            "workflow_id",
            "command_kind",
            "actor_ref",
        ):
            required_text(name, getattr(command, name))
        positive_version("expected_workflow_version", command.expected_workflow_version)
        if not isinstance(command.safe_command, dict):
            raise TypeError("safe_command must be an object")
        if (
            type(command.safe_command_schema_version) is not int
            or command.safe_command_schema_version != 1
        ):
            raise ValueError("unsupported safe-command schema version")
        declared_safe_schema = command.safe_command.get("schema_version")
        if type(declared_safe_schema) is not int or declared_safe_schema != 1:
            raise ValueError("safe_command must declare supported schema_version 1")
        assert_privacy_safe(command.safe_command)
        key_digest = idempotency_key_sha256(command.caller_idempotency_key)
        envelope = {
            **envelope_versions("command_request"),
            "request_id": command.request_id,
            "tenant_id": command.tenant_id,
            "brand_id": command.brand_id,
            "request_workflow_id": command.request_workflow_id,
            "expected_workflow_version": command.expected_workflow_version,
            "command_kind": command.command_kind,
            "idempotency_key_sha256": key_digest,
            "actor_ref": command.actor_ref,
            "requested_at": validate_timestamp(command.requested_at),
            "safe_command": command.safe_command,
        }
        return envelope, key_digest

    def _require_workflow(
        self, connection, command: WorkflowCommand
    ) -> MarketingWorkflow:
        row = self._workflow_row(
            connection,
            tenant_id=command.tenant_id,
            brand_id=command.brand_id,
            workflow_id=command.workflow_id,
        )
        if row is None:
            raise WorkflowAccessDeniedError("workflow is unavailable")
        return self._workflow_from_row(row)

    @staticmethod
    def _idempotency_scope(connection, *, command, key_digest: str):
        return connection.execute(
            """
            SELECT request_hash, original_receipt_id
            FROM workflow_idempotency_scopes
            WHERE tenant_id = ? AND brand_id = ? AND workflow_id = ?
              AND command_kind = ? AND idempotency_key_sha256 = ?
            """,
            (
                command.tenant_id,
                command.brand_id,
                command.workflow_id,
                command.command_kind,
                key_digest,
            ),
        ).fetchone()

    @staticmethod
    def _recovery_scope(
        connection,
        *,
        tenant_id: str,
        brand_id: str,
        predecessor_workflow_id: str,
    ):
        recovery = connection.execute(
            """
            SELECT successor_workflow_id, request_hash, original_receipt_id
            FROM workflow_recovery_scopes
            WHERE tenant_id = ? AND brand_id = ?
              AND predecessor_workflow_id = ?
            """,
            (tenant_id, brand_id, predecessor_workflow_id),
        ).fetchone()
        if recovery is not None:
            return recovery
        existing = connection.execute(
            """
            SELECT current.workflow_id AS successor_workflow_id,
                   scope.request_hash, scope.original_receipt_id
            FROM marketing_workflows AS current
            LEFT JOIN workflow_idempotency_scopes AS scope
              ON scope.tenant_id = current.tenant_id
             AND scope.brand_id = current.brand_id
             AND scope.workflow_id = current.workflow_id
             AND scope.command_kind = 'create_workflow'
            WHERE current.tenant_id = ? AND current.brand_id = ?
              AND current.predecessor_workflow_id = ?
            LIMIT 1
            """,
            (tenant_id, brand_id, predecessor_workflow_id),
        ).fetchone()
        if existing is not None and existing["original_receipt_id"] is None:
            raise RuntimeError(
                "recovery successor lacks an authoritative creation receipt"
            )
        return existing

    @staticmethod
    def _recovery_conflict_scope(
        connection,
        *,
        command: WorkflowCommand,
        key_digest: str,
    ):
        return connection.execute(
            """
            SELECT predecessor_workflow_id, authoritative_workflow_id,
                   authoritative_receipt_id
            FROM workflow_recovery_conflict_scopes
            WHERE tenant_id = ? AND brand_id = ?
              AND request_workflow_id = ? AND command_kind = ?
              AND idempotency_key_sha256 = ?
            """,
            (
                command.tenant_id,
                command.brand_id,
                command.request_workflow_id,
                command.command_kind,
                key_digest,
            ),
        ).fetchone()

    @staticmethod
    def _recovery_conflict_replay(
        connection,
        *,
        command: WorkflowCommand,
        key_digest: str,
        request_hash: str,
    ):
        return connection.execute(
            """
            SELECT conflict_receipt_id
            FROM workflow_recovery_conflict_replays
            WHERE tenant_id = ? AND brand_id = ?
              AND request_workflow_id = ? AND command_kind = ?
              AND idempotency_key_sha256 = ? AND request_hash = ?
            """,
            (
                command.tenant_id,
                command.brand_id,
                command.request_workflow_id,
                command.command_kind,
                key_digest,
                request_hash,
            ),
        ).fetchone()

    @staticmethod
    def _recovery_conflict_evaluation(
        authoritative: MarketingWorkflow,
        authoritative_receipt: CommandReceipt,
    ) -> CommandEvaluation:
        return CommandEvaluation(
            outcome=ReceiptOutcome.CONFLICT_DETECTED,
            failure_class=FailureClass.CONFLICT_DETECTED,
            reason_code="recovery_successor_already_exists",
            safe_result_refs=(
                VersionedReference(
                    "command_receipt", authoritative_receipt.receipt_id, 1
                ),
                VersionedReference(
                    "workflow", authoritative.workflow_id, authoritative.version
                ),
            ),
        )

    @staticmethod
    def _insert_recovery_conflict_scope(
        connection,
        *,
        command: WorkflowCommand,
        predecessor_workflow_id: str,
        request_hash: str,
        key_digest: str,
        authoritative_workflow_id: str,
        authoritative_receipt_id: str,
        conflict_receipt: CommandReceipt,
    ) -> None:
        connection.execute(
            """
            INSERT INTO workflow_recovery_conflict_scopes (
                tenant_id, brand_id, predecessor_workflow_id,
                request_workflow_id, command_kind, idempotency_key_sha256,
                request_hash, authoritative_workflow_id,
                authoritative_receipt_id, conflict_receipt_id, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                command.tenant_id,
                command.brand_id,
                predecessor_workflow_id,
                command.request_workflow_id,
                command.command_kind,
                key_digest,
                request_hash,
                authoritative_workflow_id,
                authoritative_receipt_id,
                conflict_receipt.receipt_id,
                conflict_receipt.recorded_at,
            ),
        )
        MarketingWorkflowRepository._insert_recovery_conflict_replay(
            connection,
            command=command,
            predecessor_workflow_id=predecessor_workflow_id,
            request_hash=request_hash,
            key_digest=key_digest,
            conflict_receipt=conflict_receipt,
        )

    @staticmethod
    def _insert_recovery_conflict_replay(
        connection,
        *,
        command: WorkflowCommand,
        predecessor_workflow_id: str,
        request_hash: str,
        key_digest: str,
        conflict_receipt: CommandReceipt,
    ) -> None:
        connection.execute(
            """
            INSERT INTO workflow_recovery_conflict_replays (
                tenant_id, brand_id, request_workflow_id, command_kind,
                idempotency_key_sha256, request_hash,
                requested_predecessor_workflow_id,
                conflict_receipt_id, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                command.tenant_id,
                command.brand_id,
                command.request_workflow_id,
                command.command_kind,
                key_digest,
                request_hash,
                predecessor_workflow_id,
                conflict_receipt.receipt_id,
                conflict_receipt.recorded_at,
            ),
        )

    @staticmethod
    def _workflow_row(connection, *, tenant_id: str, brand_id: str, workflow_id: str):
        return connection.execute(
            """
            SELECT * FROM marketing_workflows
            WHERE tenant_id = ? AND brand_id = ? AND workflow_id = ?
            """,
            (tenant_id, brand_id, workflow_id),
        ).fetchone()

    @staticmethod
    def _lock_workflow_row(
        connection,
        *,
        tenant_id: str,
        brand_id: str,
        workflow_id: str,
    ):
        """Acquire the ordinary command row lock, then read its current version."""

        locked = connection.execute(
            """
            UPDATE marketing_workflows SET version = version
            WHERE tenant_id = ? AND brand_id = ? AND workflow_id = ?
            """,
            (tenant_id, brand_id, workflow_id),
        )
        if locked.rowcount != 1:
            return None
        return MarketingWorkflowRepository._workflow_row(
            connection,
            tenant_id=tenant_id,
            brand_id=brand_id,
            workflow_id=workflow_id,
        )

    @staticmethod
    def _validate_owned_references(connection, workflow: MarketingWorkflow) -> None:
        brand = connection.execute(
            "SELECT tenant_id FROM brands WHERE brand_id = ?", (workflow.brand_id,)
        ).fetchone()
        plan = connection.execute(
            """
            SELECT brand_id FROM campaign_plans
            WHERE tenant_id = ? AND campaign_id = ? AND version = ?
            """,
            (
                workflow.tenant_id,
                workflow.campaign_plan.id,
                workflow.campaign_plan.version,
            ),
        ).fetchone()
        if brand is None or str(brand["tenant_id"]) != workflow.tenant_id:
            raise WorkflowAccessDeniedError("workflow references are unavailable")
        if plan is None or str(plan["brand_id"]) != workflow.brand_id:
            raise WorkflowAccessDeniedError("workflow references are unavailable")
        if workflow.marketing_brief:
            brief = connection.execute(
                """
                SELECT brand_id FROM marketing_briefs
                WHERE tenant_id = ? AND brief_id = ? AND version = ?
                """,
                (
                    workflow.tenant_id,
                    workflow.marketing_brief.id,
                    workflow.marketing_brief.version,
                ),
            ).fetchone()
            if brief is None or str(brief["brand_id"]) != workflow.brand_id:
                raise WorkflowAccessDeniedError("workflow references are unavailable")
        if workflow.predecessor_workflow_id:
            predecessor = MarketingWorkflowRepository._workflow_row(
                connection,
                tenant_id=workflow.tenant_id,
                brand_id=workflow.brand_id,
                workflow_id=workflow.predecessor_workflow_id,
            )
            if (
                predecessor is None
                or str(predecessor["state"]) != WorkflowState.FAILED.value
            ):
                raise ValueError("predecessor must be a failed tenant-owned workflow")
            if (
                str(predecessor["campaign_plan_id"]) != workflow.campaign_plan.id
                or int(predecessor["campaign_plan_version"])
                != workflow.campaign_plan.version
                or predecessor["marketing_brief_id"]
                != (workflow.marketing_brief.id if workflow.marketing_brief else None)
                or predecessor["marketing_brief_version"]
                != (
                    workflow.marketing_brief.version
                    if workflow.marketing_brief
                    else None
                )
            ):
                raise ValueError(
                    "recovery workflow must preserve immutable work references"
                )

    @staticmethod
    def _workflow_values(workflow: MarketingWorkflow) -> tuple[Any, ...]:
        return (
            workflow.workflow_id,
            workflow.tenant_id,
            workflow.brand_id,
            workflow.campaign_plan.id,
            workflow.campaign_plan.version,
            workflow.marketing_brief.id if workflow.marketing_brief else None,
            workflow.marketing_brief.version if workflow.marketing_brief else None,
            workflow.predecessor_workflow_id,
            workflow.successor_workflow_id,
            workflow.state.value,
            workflow.failure_class.value if workflow.failure_class else None,
            workflow.version,
            (
                workflow.blocked_resume_state.value
                if workflow.blocked_resume_state
                else None
            ),
            MarketingWorkflowRepository._artifact_json(workflow),
            workflow.created_at,
            workflow.updated_at,
        )

    @staticmethod
    def _artifact_json(workflow: MarketingWorkflow) -> str | None:
        return (
            canonical_json(workflow.canonical_artifact_ref.to_dict())
            if workflow.canonical_artifact_ref
            else None
        )

    @staticmethod
    def _workflow_from_row(row) -> MarketingWorkflow:
        artifact = (
            json.loads(str(row["canonical_artifact_ref_json"]))
            if row["canonical_artifact_ref_json"]
            else None
        )
        from app.marketing_workflow.models import CanonicalArtifactReference

        return MarketingWorkflow(
            workflow_id=str(row["workflow_id"]),
            tenant_id=str(row["tenant_id"]),
            brand_id=str(row["brand_id"]),
            campaign_plan=VersionedReference(
                "campaign_plan",
                str(row["campaign_plan_id"]),
                int(row["campaign_plan_version"]),
            ),
            marketing_brief=(
                VersionedReference(
                    "marketing_brief",
                    str(row["marketing_brief_id"]),
                    int(row["marketing_brief_version"]),
                )
                if row["marketing_brief_id"] is not None
                else None
            ),
            predecessor_workflow_id=row["predecessor_workflow_id"],
            successor_workflow_id=row["successor_workflow_id"],
            state=WorkflowState(str(row["state"])),
            failure_class=(
                FailureClass(str(row["failure_class"]))
                if row["failure_class"]
                else None
            ),
            version=int(row["version"]),
            blocked_resume_state=(
                WorkflowState(str(row["blocked_resume_state"]))
                if row["blocked_resume_state"]
                else None
            ),
            canonical_artifact_ref=(
                CanonicalArtifactReference(**artifact) if artifact else None
            ),
            created_at=str(row["created_at"]),
            updated_at=str(row["updated_at"]),
        )

    @staticmethod
    def _sorted_refs(refs: tuple[VersionedReference, ...]) -> list[dict[str, Any]]:
        return [
            item.to_dict()
            for item in sorted(
                refs, key=lambda item: (item.kind, item.id, item.version)
            )
        ]

    @staticmethod
    def _receipt_by_id(connection, receipt_id: str) -> CommandReceipt:
        row = connection.execute(
            """
            SELECT canonical_json, receipt_hash FROM workflow_command_receipts
            WHERE receipt_id = ?
            """,
            (receipt_id,),
        ).fetchone()
        if row is None:
            raise RuntimeError("idempotency scope references a missing receipt")
        envelope = json.loads(str(row["canonical_json"]))
        return MarketingWorkflowRepository._receipt_from_envelope(
            envelope, str(row["canonical_json"]), str(row["receipt_hash"])
        )

    @staticmethod
    def _receipt_from_envelope(
        envelope: dict[str, Any], receipt_json: str, receipt_digest: str
    ) -> CommandReceipt:
        schema_version = envelope.get("schema_version")
        if type(schema_version) is not int:
            raise ValueError("schema_version must be an integer")
        pair = (
            envelope.get("canonicalization_version"),
            schema_version,
        )
        if pair == (MLAI_CJ_1, MLAI_CJ_1_SCHEMA_VERSION):
            request_workflow_id = envelope["workflow_id"]
            authoritative_workflow_id = None
        elif pair == (MLAI_CJ_2, MLAI_CJ_2_SCHEMA_VERSION):
            request_workflow_id = envelope["request_workflow_id"]
            authoritative_workflow_id = envelope.get("authoritative_workflow_id")
            if "authoritative_workflow_id" in envelope and (
                authoritative_workflow_id is None
                or authoritative_workflow_id == request_workflow_id
            ):
                raise ValueError(
                    "MLAI-CJ-2 authoritative identity must differ or be omitted"
                )
        else:
            raise ValueError("unsupported or mismatched MLAI-CJ version pair")
        if envelope.get("record_kind") != "command_receipt":
            raise ValueError("persisted receipt has an invalid record kind")
        return CommandReceipt(
            receipt_id=envelope["receipt_id"],
            request_id=envelope["request_id"],
            request_hash=envelope["request_hash"],
            tenant_id=envelope["tenant_id"],
            brand_id=envelope["brand_id"],
            request_workflow_id=request_workflow_id,
            workflow_version_before=envelope["workflow_version_before"],
            workflow_version_after=envelope["workflow_version_after"],
            command_kind=envelope["command_kind"],
            idempotency_key_sha256=envelope["idempotency_key_sha256"],
            actor_ref=envelope["actor_ref"],
            outcome=ReceiptOutcome(envelope["outcome"]),
            failure_class=(
                FailureClass(envelope["failure_class"])
                if envelope["failure_class"]
                else None
            ),
            conflicts_with_receipt_id=envelope["conflicts_with_receipt_id"],
            requested_at=envelope["requested_at"],
            recorded_at=envelope["recorded_at"],
            safe_result_refs=tuple(
                VersionedReference(**item) for item in envelope["safe_result_refs"]
            ),
            authoritative_workflow_id=authoritative_workflow_id,
            canonicalization_version=str(pair[0]),
            schema_version=schema_version,
            canonical_json=receipt_json,
            receipt_sha256=receipt_digest,
        )
