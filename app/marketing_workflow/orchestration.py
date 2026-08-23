"""Durable API orchestration claims for planning-to-approval operations."""

from __future__ import annotations

import hashlib
import re
import sqlite3
from dataclasses import dataclass
from enum import StrEnum
from typing import Any, Mapping

from app.database.connection import SQLiteDatabase
from app.marketing_workflow.canonical import (
    assert_privacy_safe,
    canonical_json_bytes,
    validate_timestamp,
)
from app.marketing_workflow.models import opaque_actor_ref, required_text

ORCHESTRATION_PLAN_DOMAIN = "earthonox/mlai-033.2/orchestration-plan/v1"
ORCHESTRATION_RESPONSE_DOMAIN = "earthonox/mlai-033.2/orchestration-response/v1"
MAX_PLAN_BYTES = 64 * 1024
MAX_COMMANDS = 8
MAX_COMMAND_BYTES = 16 * 1024
_SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")


class OrchestrationProgress(StrEnum):
    CLAIMED = "claimed"
    WORKFLOW_CREATED = "workflow_created"
    PLANNED = "planned"
    AWAITING_APPROVAL = "awaiting_approval"
    APPROVAL_RECORDED = "approval_recorded"
    APPROVED = "approved"
    CONFLICT_DETECTED = "conflict_detected"
    FAILED = "failed"


PROGRESS_ORDINAL = {
    OrchestrationProgress.CLAIMED: 0,
    OrchestrationProgress.WORKFLOW_CREATED: 1,
    OrchestrationProgress.PLANNED: 2,
    OrchestrationProgress.AWAITING_APPROVAL: 3,
    OrchestrationProgress.APPROVAL_RECORDED: 4,
    OrchestrationProgress.APPROVED: 5,
    OrchestrationProgress.CONFLICT_DETECTED: 6,
    OrchestrationProgress.FAILED: 7,
}
TERMINAL_PROGRESS = frozenset(
    {
        OrchestrationProgress.APPROVED,
        OrchestrationProgress.CONFLICT_DETECTED,
        OrchestrationProgress.FAILED,
    }
)
ALLOWED_PROGRESS_TRANSITIONS = {
    OrchestrationProgress.CLAIMED: frozenset(
        {
            OrchestrationProgress.WORKFLOW_CREATED,
            OrchestrationProgress.CONFLICT_DETECTED,
            OrchestrationProgress.FAILED,
        }
    ),
    OrchestrationProgress.WORKFLOW_CREATED: frozenset(
        {
            OrchestrationProgress.PLANNED,
            OrchestrationProgress.CONFLICT_DETECTED,
            OrchestrationProgress.FAILED,
        }
    ),
    OrchestrationProgress.PLANNED: frozenset(
        {
            OrchestrationProgress.AWAITING_APPROVAL,
            OrchestrationProgress.CONFLICT_DETECTED,
            OrchestrationProgress.FAILED,
        }
    ),
    OrchestrationProgress.AWAITING_APPROVAL: frozenset(
        {
            OrchestrationProgress.APPROVAL_RECORDED,
            OrchestrationProgress.CONFLICT_DETECTED,
            OrchestrationProgress.FAILED,
        }
    ),
    OrchestrationProgress.APPROVAL_RECORDED: frozenset(
        {
            OrchestrationProgress.APPROVED,
            OrchestrationProgress.CONFLICT_DETECTED,
            OrchestrationProgress.FAILED,
        }
    ),
}


class OrchestrationConflictError(RuntimeError):
    """Raised when a durable claim is reused with changed canonical input."""

    def __init__(self, record: "WorkflowApiOrchestration") -> None:
        super().__init__("orchestration claim conflicts with existing input")
        self.record = record


class OrchestrationWorkflowConflictError(RuntimeError):
    """Raised when a deterministic workflow is reserved by another claim."""

    def __init__(self, record: "WorkflowApiOrchestration") -> None:
        super().__init__("workflow identity is already reserved")
        self.record = record


class OrchestrationOptimisticConflictError(RuntimeError):
    """Raised when orchestration progress changed concurrently."""


@dataclass(frozen=True, slots=True)
class WorkflowApiOrchestration:
    orchestration_id: str
    tenant_id: str
    brand_id: str
    actor_ref: str
    operation: str
    client_key_digest: str
    workflow_id: str
    request_hash: str
    command_plan_json: str
    command_plan_sha256: str
    progress_state: OrchestrationProgress
    progress_ordinal: int
    version: int
    failure_class: str | None
    final_response_status: int | None
    final_response_json: str | None
    final_response_sha256: str | None
    created_at: str
    updated_at: str
    completed_at: str | None


@dataclass(frozen=True, slots=True)
class OrchestrationClaim:
    record: WorkflowApiOrchestration
    created: bool
    replay: bool


def _sha256(domain: str, value: bytes) -> str:
    return hashlib.sha256(domain.encode("ascii") + b"\n" + value).hexdigest()


def _is_unique_violation(error: BaseException) -> bool:
    if isinstance(error, sqlite3.IntegrityError):
        return "unique" in str(error).lower() or "constraint" in str(error).lower()
    sqlstate = getattr(error, "sqlstate", None)
    return sqlstate == "23505" or "duplicate key" in str(error).lower()


def _safe_response(value: Mapping[str, Any]) -> tuple[str, str]:
    assert_privacy_safe(value)
    encoded = canonical_json_bytes(value)
    if len(encoded) > MAX_COMMAND_BYTES:
        raise ValueError("safe response exceeds the bounded canonical size")
    return encoded.decode("utf-8"), _sha256(ORCHESTRATION_RESPONSE_DOMAIN, encoded)


def canonical_command_plan(
    value: Mapping[str, Any],
    *,
    tenant_id: str,
    brand_id: str,
    actor_ref: str,
    operation: str,
    workflow_id: str,
    client_key_digest: str,
) -> tuple[str, str]:
    """Validate and encode immutable orchestration command material."""

    if not isinstance(value, Mapping):
        raise TypeError("command plan must be an object")
    assert_privacy_safe(value)
    expected = {
        "record_kind": "workflow_orchestration_plan",
        "orchestration_plan_version": 1,
        "canonicalization_version": "MLAI-CJ-2",
        "mlai_cj_schema_version": 2,
        "safe_command_schema_version": 1,
        "tenant_id": required_text("tenant_id", tenant_id),
        "brand_id": required_text("brand_id", brand_id),
        "actor_ref": opaque_actor_ref(actor_ref),
        "operation": required_text("operation", operation),
        "workflow_id": required_text("workflow_id", workflow_id),
        "client_key_digest": client_key_digest,
    }
    for key, expected_value in expected.items():
        if value.get(key) != expected_value:
            raise ValueError(f"command plan field {key} does not match claim")
    requested_at = value.get("requested_at")
    validate_timestamp(requested_at)
    commands = value.get("commands")
    if not isinstance(commands, list) or not 1 <= len(commands) <= MAX_COMMANDS:
        raise ValueError("command plan must contain one to eight commands")
    for command in commands:
        if not isinstance(command, Mapping):
            raise TypeError("command plan entries must be objects")
        for field in (
            "request_id",
            "command_kind",
            "command_key_digest",
            "requested_at",
            "expected_workflow_version",
            "safe_command",
        ):
            if field not in command:
                raise ValueError(f"command plan is missing {field}")
        validate_timestamp(command["requested_at"])
        if type(command["expected_workflow_version"]) is not int:
            raise TypeError("expected_workflow_version must be an integer")
        assert_privacy_safe(command["safe_command"])
        if len(canonical_json_bytes(command)) > MAX_COMMAND_BYTES:
            raise ValueError("command exceeds the bounded canonical size")
    encoded = canonical_json_bytes(value)
    if len(encoded) > MAX_PLAN_BYTES:
        raise ValueError("command plan exceeds the bounded canonical size")
    return encoded.decode("utf-8"), _sha256(ORCHESTRATION_PLAN_DOMAIN, encoded)


class WorkflowApiOrchestrationRepository:
    """Persist API claims and progress without owning workflow authority."""

    def __init__(self, database: SQLiteDatabase) -> None:
        self.database = database

    @staticmethod
    def _from_row(row) -> WorkflowApiOrchestration:
        return WorkflowApiOrchestration(
            orchestration_id=str(row["orchestration_id"]),
            tenant_id=str(row["tenant_id"]),
            brand_id=str(row["brand_id"]),
            actor_ref=str(row["actor_ref"]),
            operation=str(row["operation"]),
            client_key_digest=str(row["client_key_digest"]),
            workflow_id=str(row["workflow_id"]),
            request_hash=str(row["request_hash"]),
            command_plan_json=str(row["command_plan_json"]),
            command_plan_sha256=str(row["command_plan_sha256"]),
            progress_state=OrchestrationProgress(str(row["progress_state"])),
            progress_ordinal=int(row["progress_ordinal"]),
            version=int(row["version"]),
            failure_class=(
                None if row["failure_class"] is None else str(row["failure_class"])
            ),
            final_response_status=(
                None
                if row["final_response_status"] is None
                else int(row["final_response_status"])
            ),
            final_response_json=(
                None
                if row["final_response_json"] is None
                else str(row["final_response_json"])
            ),
            final_response_sha256=(
                None
                if row["final_response_sha256"] is None
                else str(row["final_response_sha256"])
            ),
            created_at=str(row["created_at"]),
            updated_at=str(row["updated_at"]),
            completed_at=(
                None if row["completed_at"] is None else str(row["completed_at"])
            ),
        )

    @staticmethod
    def _select_by_claim(
        connection, *, tenant_id, brand_id, actor_ref, operation, client_key_digest
    ):
        return connection.execute(
            """
            SELECT * FROM workflow_api_orchestrations
            WHERE tenant_id = ? AND brand_id = ? AND actor_ref = ?
              AND operation = ? AND client_key_digest = ?
            """,
            (tenant_id, brand_id, actor_ref, operation, client_key_digest),
        ).fetchone()

    @staticmethod
    def _select_by_workflow(connection, *, tenant_id, brand_id, workflow_id):
        return connection.execute(
            """
            SELECT * FROM workflow_api_orchestrations
            WHERE tenant_id = ? AND brand_id = ? AND workflow_id = ?
            """,
            (tenant_id, brand_id, workflow_id),
        ).fetchone()

    @staticmethod
    def _select_by_id(connection, orchestration_id):
        return connection.execute(
            "SELECT * FROM workflow_api_orchestrations WHERE orchestration_id = ?",
            (orchestration_id,),
        ).fetchone()

    def claim(
        self,
        *,
        orchestration_id: str,
        tenant_id: str,
        brand_id: str,
        actor_ref: str,
        operation: str,
        client_key_digest: str,
        workflow_id: str,
        request_hash: str,
        command_plan: Mapping[str, Any],
        created_at: str,
    ) -> OrchestrationClaim:
        """Create or replay one durable first-submission claim."""

        plan_json, plan_sha256 = canonical_command_plan(
            command_plan,
            tenant_id=tenant_id,
            brand_id=brand_id,
            actor_ref=actor_ref,
            operation=operation,
            workflow_id=workflow_id,
            client_key_digest=client_key_digest,
        )
        validate_timestamp(created_at)
        required_text("orchestration_id", orchestration_id)
        if not _SHA256_PATTERN.fullmatch(client_key_digest):
            raise ValueError("client_key_digest must be lowercase SHA-256")
        if not _SHA256_PATTERN.fullmatch(request_hash):
            raise ValueError("request_hash must be lowercase SHA-256")
        try:
            with self.database.transaction() as connection:
                connection.execute(
                    """
                    INSERT INTO workflow_api_orchestrations (
                        orchestration_id, tenant_id, brand_id, actor_ref,
                        operation, client_key_digest, workflow_id,
                        request_hash, command_plan_json, command_plan_sha256,
                        progress_state, progress_ordinal, version,
                        created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'claimed', 0, 1, ?, ?)
                    """,
                    (
                        orchestration_id,
                        tenant_id,
                        brand_id,
                        actor_ref,
                        operation,
                        client_key_digest,
                        workflow_id,
                        request_hash,
                        plan_json,
                        plan_sha256,
                        created_at,
                        created_at,
                    ),
                )
        except Exception as error:
            if not _is_unique_violation(error):
                raise
            with self.database.connection() as connection:
                existing = self._select_by_claim(
                    connection,
                    tenant_id=tenant_id,
                    brand_id=brand_id,
                    actor_ref=actor_ref,
                    operation=operation,
                    client_key_digest=client_key_digest,
                )
                claim_match = existing is not None
                if existing is None:
                    existing = self._select_by_workflow(
                        connection,
                        tenant_id=tenant_id,
                        brand_id=brand_id,
                        workflow_id=workflow_id,
                    )
                if existing is None:
                    existing = self._select_by_id(connection, orchestration_id)
            if existing is None:
                raise
            record = self._from_row(existing)
            if not claim_match:
                raise OrchestrationWorkflowConflictError(record) from error
            if record.workflow_id != workflow_id:
                raise OrchestrationWorkflowConflictError(record) from error
            if (
                record.request_hash != request_hash
                or record.command_plan_sha256 != plan_sha256
            ):
                raise OrchestrationConflictError(record) from error
            return OrchestrationClaim(record=record, created=False, replay=True)
        with self.database.connection() as connection:
            row = self._select_by_claim(
                connection,
                tenant_id=tenant_id,
                brand_id=brand_id,
                actor_ref=actor_ref,
                operation=operation,
                client_key_digest=client_key_digest,
            )
            if row is None:
                raise RuntimeError("orchestration claim was not persisted")
            return OrchestrationClaim(
                record=self._from_row(row), created=True, replay=False
            )

    def get(self, orchestration_id: str) -> WorkflowApiOrchestration | None:
        with self.database.connection() as connection:
            row = connection.execute(
                "SELECT * FROM workflow_api_orchestrations WHERE orchestration_id = ?",
                (orchestration_id,),
            ).fetchone()
        return None if row is None else self._from_row(row)

    def advance(
        self,
        *,
        orchestration_id: str,
        expected_version: int,
        progress_state: OrchestrationProgress,
        updated_at: str,
        failure_class: str | None = None,
        final_response: Mapping[str, Any] | None = None,
        final_response_status: int | None = None,
        completed_at: str | None = None,
    ) -> WorkflowApiOrchestration:
        """Advance progress exactly once under optimistic concurrency."""

        if type(expected_version) is not int or expected_version < 1:
            raise ValueError("expected_version must be a positive integer")
        validate_timestamp(updated_at)
        if completed_at is not None:
            validate_timestamp(completed_at)
        response_json = response_sha256 = None
        if final_response is not None:
            if progress_state not in TERMINAL_PROGRESS:
                raise ValueError("final response requires terminal progress")
            response_json, response_sha256 = _safe_response(final_response)
            if (
                type(final_response_status) is not int
                or not 100 <= final_response_status <= 599
            ):
                raise ValueError("final_response_status must be an HTTP status")
        elif final_response_status is not None:
            raise ValueError("final_response_status requires final_response")
        with self.database.transaction() as connection:
            current_row = connection.execute(
                "SELECT * FROM workflow_api_orchestrations WHERE orchestration_id = ?",
                (orchestration_id,),
            ).fetchone()
            if current_row is None:
                raise KeyError(orchestration_id)
            current = self._from_row(current_row)
            if current.version != expected_version:
                raise OrchestrationOptimisticConflictError(
                    "orchestration version changed concurrently"
                )
            if current.progress_state in TERMINAL_PROGRESS:
                raise ValueError("terminal orchestration cannot advance")
            if progress_state not in ALLOWED_PROGRESS_TRANSITIONS.get(
                current.progress_state, frozenset()
            ):
                raise ValueError("invalid orchestration progress transition")
            if (
                progress_state
                not in {
                    OrchestrationProgress.CONFLICT_DETECTED,
                    OrchestrationProgress.FAILED,
                }
                and PROGRESS_ORDINAL[progress_state] <= current.progress_ordinal
            ):
                raise ValueError("orchestration progress must be monotonic")
            next_ordinal = PROGRESS_ORDINAL[progress_state]
            if (
                progress_state in TERMINAL_PROGRESS
                and next_ordinal < current.progress_ordinal
            ):
                raise ValueError("terminal progress cannot move backwards")
            connection.execute(
                """
                UPDATE workflow_api_orchestrations
                SET progress_state = ?, progress_ordinal = ?, version = version + 1,
                    failure_class = ?, final_response_status = ?,
                    final_response_json = ?, final_response_sha256 = ?,
                    updated_at = ?, completed_at = ?
                WHERE orchestration_id = ? AND version = ?
                """,
                (
                    progress_state.value,
                    next_ordinal,
                    failure_class,
                    final_response_status,
                    response_json,
                    response_sha256,
                    updated_at,
                    completed_at,
                    orchestration_id,
                    expected_version,
                ),
            )
            row = connection.execute(
                "SELECT * FROM workflow_api_orchestrations WHERE orchestration_id = ?",
                (orchestration_id,),
            ).fetchone()
            if row is None:
                raise RuntimeError("orchestration disappeared during update")
            return self._from_row(row)
