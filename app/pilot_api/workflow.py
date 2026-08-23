"""Tenant-authorized planning-to-approval API orchestration."""

from __future__ import annotations

import hashlib
import json
import threading
from uuid import uuid4

from app.identity import Permission
from app.marketing_workflow import (
    ApprovalDecision,
    MarketingWorkflowService,
    OrchestrationProgress,
    WorkflowCommand,
    WorkflowState,
    deterministic_actor_ref,
    deterministic_command_key_digest,
    deterministic_subcommand_request_id,
    deterministic_workflow_id,
    validate_client_idempotency_key,
)
from app.marketing_workflow.canonical import (
    canonical_json_bytes,
    idempotency_key_sha256,
    record_sha256,
    utc_timestamp,
)
from app.marketing_workflow.models import WorkflowAuthority
from app.marketing_workflow.orchestration import (
    PROGRESS_ORDINAL,
    OperationClaimConflictError,
    OperationClaimResult,
    WorkflowApiOrchestration,
)
from app.marketing_workflow.repository import WorkflowAccessDeniedError
from app.pilot_api.contracts import (
    workflow_response,
    workflow_response_envelope,
    workflow_response_from_envelope,
)


class _PermissiveWorkflowAuthority(WorkflowAuthority):
    """Endpoint authorization is performed before domain commands are called."""

    def permits(self, **_: object) -> bool:
        return True


class WorkflowApiOperations:
    """Keep transport orchestration outside workflow and artifact owners."""

    def __init__(self, application) -> None:
        self.application = application
        self.authority = _PermissiveWorkflowAuthority()
        self._resume_lock = threading.RLock()

    @staticmethod
    def _request_hash(plan: dict) -> str:
        return hashlib.sha256(canonical_json_bytes(plan)).hexdigest()

    def _parent_root(
        self,
        *,
        tenant_id: str,
        brand_id: str,
        workflow_id: str,
        actor_ref: str,
        operation: str,
        client_digest: str,
        plan: dict,
        requested_at: str,
    ):
        """Return the workflow-level root, creating it only when absent."""

        parent = self.application.workflow_orchestrations.get_by_workflow(
            tenant_id=tenant_id, brand_id=brand_id, workflow_id=workflow_id
        )
        if parent is not None:
            return parent
        result = self.application.workflow_orchestrations.claim(
            # The parent reservation is part of the canonical first-submission
            # material.  Derive it from the deterministic workflow identity so
            # concurrent identical requests cannot manufacture different
            # command plans before the uniqueness claim resolves them.
            orchestration_id=f"orch_{workflow_id}",
            tenant_id=tenant_id,
            brand_id=brand_id,
            actor_ref=actor_ref,
            operation=operation,
            client_key_digest=client_digest,
            workflow_id=workflow_id,
            request_hash=self._request_hash(plan),
            command_plan=plan,
            created_at=requested_at,
        )
        return result.record

    def _operation_claim(
        self,
        *,
        parent,
        tenant_id: str,
        brand_id: str,
        actor_ref: str,
        operation: str,
        client_digest: str,
        workflow_id: str,
        plan: dict,
        requested_at: str,
    ):
        return self.application.workflow_operation_claims.claim(
            operation_claim_id=f"op_{uuid4().hex}",
            parent_orchestration_id=parent.orchestration_id,
            tenant_id=tenant_id,
            brand_id=brand_id,
            actor_ref=actor_ref,
            operation=operation,
            client_key_digest=client_digest,
            workflow_id=workflow_id,
            request_hash=self._request_hash(plan),
            command_plan=plan,
            created_at=requested_at,
        )

    def _persist_operation_response(
        self, claim, *, data: dict, status: int, state: OrchestrationProgress
    ):
        if claim.record.final_response_json:
            return workflow_response_from_envelope(
                json.loads(claim.record.final_response_json), replayed=True
            )
        record = claim.record
        progression = (
            OrchestrationProgress.CLAIMED,
            OrchestrationProgress.WORKFLOW_CREATED,
            OrchestrationProgress.PLANNED,
            OrchestrationProgress.AWAITING_APPROVAL,
            OrchestrationProgress.APPROVAL_RECORDED,
            OrchestrationProgress.APPROVED,
        )
        if state in progression and record.progress_state in progression:
            targets = progression[record.progress_ordinal + 1 :]
            for target in targets:
                if PROGRESS_ORDINAL[target] > PROGRESS_ORDINAL[state]:
                    break
                record = self.application.workflow_operation_claims.advance(
                    operation_claim_id=record.operation_claim_id,
                    expected_version=record.version,
                    progress_state=target,
                    updated_at=utc_timestamp(),
                )
        elif record.progress_state is not state:
            record = self.application.workflow_operation_claims.advance(
                operation_claim_id=record.operation_claim_id,
                expected_version=record.version,
                progress_state=state,
                updated_at=utc_timestamp(),
            )
        response = self._response(status, data)
        record = self.application.workflow_operation_claims.advance(
            operation_claim_id=record.operation_claim_id,
            expected_version=record.version,
            progress_state=record.progress_state,
            updated_at=utc_timestamp(),
            final_response=workflow_response_envelope(response),
            final_response_status=status,
            completed_at=utc_timestamp(),
        )
        return response

    @staticmethod
    def _replayed_operation(claim):
        if claim is None or not claim.record.final_response_json:
            return None
        return workflow_response_from_envelope(
            json.loads(claim.record.final_response_json), replayed=True
        )

    @staticmethod
    def _operation_plan(
        *,
        tenant_id,
        brand_id,
        actor_ref,
        workflow_id,
        operation,
        client_digest,
        parent_id,
        command_kind,
        expected,
        safe,
        requested_at,
    ):
        command = {
            "request_id": deterministic_subcommand_request_id(
                orchestration_id=parent_id,
                ordinal=1,
                command_kind=command_kind,
            ),
            "command_kind": command_kind,
            "command_key_digest": deterministic_command_key_digest(
                client_key_digest=client_digest,
                ordinal=1,
                command_kind=command_kind,
            ),
            "requested_at": requested_at,
            "expected_workflow_version": expected,
            "safe_command": {"schema_version": 1, **safe},
        }
        return {
            "record_kind": "workflow_orchestration_plan",
            "orchestration_plan_version": 1,
            "canonicalization_version": "MLAI-CJ-2",
            "mlai_cj_schema_version": 2,
            "safe_command_schema_version": 1,
            "tenant_id": tenant_id,
            "brand_id": brand_id,
            "actor_ref": actor_ref,
            "operation": operation,
            "workflow_id": workflow_id,
            "client_key_digest": client_digest,
            "requested_at": requested_at,
            "commands": [command],
        }

    @staticmethod
    def actor_ref(principal) -> str:
        return deterministic_actor_ref(
            provider=principal.provider, subject_id=principal.subject_id
        )

    def _authorize(
        self,
        principal,
        tenant_id: str,
        permission: Permission,
        resource_type: str,
        resource_id: str,
        brand_id: str,
    ) -> None:
        try:
            owner = self.application.brands.tenant_id_for(brand_id)
        except FileNotFoundError:
            owner = "missing"
        self.application.authorization.authorize(
            principal,
            tenant_id=tenant_id,
            permission=permission,
            resource_type=resource_type,
            resource_id=resource_id,
            resource_tenant_id=owner,
            audit_action=f"workflow_api.{permission.value}",
        )

    def _command(
        self,
        *,
        tenant_id,
        brand_id,
        actor_ref,
        workflow_id,
        client_digest,
        orchestration_id,
        ordinal,
        kind,
        expected,
        safe,
        requested_at,
    ):
        command_key = deterministic_command_key_digest(
            client_key_digest=client_digest, ordinal=ordinal, command_kind=kind
        )
        return WorkflowCommand(
            request_id=deterministic_subcommand_request_id(
                orchestration_id=orchestration_id, ordinal=ordinal, command_kind=kind
            ),
            tenant_id=tenant_id,
            brand_id=brand_id,
            workflow_id=workflow_id,
            expected_workflow_version=expected,
            command_kind=kind,
            caller_idempotency_key=command_key,
            actor_ref=actor_ref,
            requested_at=requested_at,
            safe_command={"schema_version": 1, **safe},
            safe_command_schema_version=1,
        )

    @staticmethod
    def _response(status: int, data: dict, *, replayed: bool = False):
        return workflow_response(status, data, replayed=replayed)

    @staticmethod
    def _status_data(status, *, technical: bool) -> dict:
        data = {
            "workflow_id": status.workflow_id,
            "state": status.state.value,
            "workflow_version": status.workflow_version,
            "next_action": status.next_action,
            "required_approval": status.required_approval,
            "evidence_available": status.evidence_available,
        }
        if status.blocked_reason is not None:
            data["blocked_reason"] = status.blocked_reason.value
        if technical and status.technical_details:
            data["technical_details"] = status.technical_details
        return data

    def create_and_plan(
        self, *, principal, tenant_id: str, request, idempotency_key: str
    ):
        self._authorize(
            principal,
            tenant_id,
            Permission.GENERATE,
            "brand",
            request.brand_id,
            request.brand_id,
        )
        actor = self.actor_ref(principal)
        client_key = validate_client_idempotency_key(idempotency_key)
        client_digest = idempotency_key_sha256(client_key)
        plan = self.application.campaign_plans.get(
            request.campaign_plan_id,
            tenant_id=tenant_id,
            version=request.campaign_plan_version,
        )
        if plan.brand_id != request.brand_id:
            raise WorkflowAccessDeniedError("workflow is unavailable")
        brief = None
        if request.marketing_brief_id:
            brief = self.application.marketing_briefs.get(
                request.marketing_brief_id,
                tenant_id=tenant_id,
                version=request.marketing_brief_version,
            )
            if brief.brand_id != request.brand_id:
                raise WorkflowAccessDeniedError("workflow is unavailable")
        workflow_id = deterministic_workflow_id(
            tenant_id=tenant_id,
            brand_id=request.brand_id,
            actor_ref=actor,
            operation="create_and_plan",
            client_key_digest=client_digest,
        )
        existing_claim = self.application.workflow_orchestrations.get_by_claim(
            tenant_id=tenant_id,
            brand_id=request.brand_id,
            actor_ref=actor,
            operation="create_and_plan",
            client_key_digest=client_digest,
        )
        orchestration_id = (
            existing_claim.orchestration_id
            if existing_claim is not None
            else f"orch_{workflow_id}"
        )
        requested_at = (
            json.loads(existing_claim.command_plan_json).get("requested_at")
            if existing_claim is not None
            else utc_timestamp()
        )
        commands = [
            {
                "request_id": deterministic_subcommand_request_id(
                    orchestration_id=orchestration_id,
                    ordinal=1,
                    command_kind="create_workflow",
                ),
                "command_kind": "create_workflow",
                "command_key_digest": deterministic_command_key_digest(
                    client_key_digest=client_digest,
                    ordinal=1,
                    command_kind="create_workflow",
                ),
                "requested_at": requested_at,
                "expected_workflow_version": 1,
                "safe_command": {
                    "schema_version": 1,
                    "operation": "create_workflow",
                    "campaign_plan": {
                        "kind": "campaign_plan",
                        "id": plan.campaign_id,
                        "version": plan.version,
                    },
                },
            },
            {
                "request_id": deterministic_subcommand_request_id(
                    orchestration_id=orchestration_id,
                    ordinal=2,
                    command_kind="plan_workflow",
                ),
                "command_kind": "plan_workflow",
                "command_key_digest": deterministic_command_key_digest(
                    client_key_digest=client_digest,
                    ordinal=2,
                    command_kind="plan_workflow",
                ),
                "requested_at": requested_at,
                "expected_workflow_version": 1,
                "safe_command": {
                    "schema_version": 1,
                    "operation": "transition",
                    "target_state": "planned",
                    "action": "internal_planning",
                },
            },
            {
                "request_id": deterministic_subcommand_request_id(
                    orchestration_id=orchestration_id,
                    ordinal=3,
                    command_kind="request_approval",
                ),
                "command_kind": "request_approval",
                "command_key_digest": deterministic_command_key_digest(
                    client_key_digest=client_digest,
                    ordinal=3,
                    command_kind="request_approval",
                ),
                "requested_at": requested_at,
                "expected_workflow_version": 2,
                "safe_command": {
                    "schema_version": 1,
                    "operation": "transition",
                    "target_state": "awaiting_approval",
                    "action": "internal_planning",
                },
            },
        ]
        command_plan = {
            "record_kind": "workflow_orchestration_plan",
            "orchestration_plan_version": 1,
            "canonicalization_version": "MLAI-CJ-2",
            "mlai_cj_schema_version": 2,
            "safe_command_schema_version": 1,
            "tenant_id": tenant_id,
            "brand_id": request.brand_id,
            "actor_ref": actor,
            "operation": "create_and_plan",
            "workflow_id": workflow_id,
            "client_key_digest": client_digest,
            "requested_at": requested_at,
            "commands": commands,
        }
        request_hash = (
            __import__("hashlib").sha256(canonical_json_bytes(command_plan)).hexdigest()
        )
        claim = self.application.workflow_orchestrations.claim(
            orchestration_id=orchestration_id,
            tenant_id=tenant_id,
            brand_id=request.brand_id,
            actor_ref=actor,
            operation="create_and_plan",
            client_key_digest=client_digest,
            workflow_id=workflow_id,
            request_hash=request_hash,
            command_plan=command_plan,
            created_at=requested_at,
        )
        # All mutation and child-claim reconciliation runs through the same
        # single-flight recovery path.  This serializes same-process first
        # submissions while the durable parent claim remains the cross-process
        # reservation boundary.
        return self._resume_claim(
            claim.record,
            principal=principal,
            tenant_id=tenant_id,
            idempotency_key=client_key,
        )

    def _resume_claim(
        self,
        record: WorkflowApiOrchestration,
        *,
        principal,
        tenant_id: str,
        idempotency_key: str,
    ):
        with self._resume_lock:
            current = (
                self.application.workflow_orchestrations.get(record.orchestration_id)
                or record
            )
            return self._resume_claim_locked(
                current,
                principal=principal,
                tenant_id=tenant_id,
                idempotency_key=idempotency_key,
            )

    def _resume_claim_locked(
        self,
        record: WorkflowApiOrchestration,
        *,
        principal,
        tenant_id: str,
        idempotency_key: str,
    ):
        if record.final_response_json:
            return workflow_response_from_envelope(
                json.loads(record.final_response_json), replayed=True
            )
        child_record = self.application.workflow_operation_claims.get_by_claim(
            tenant_id=record.tenant_id,
            brand_id=record.brand_id,
            actor_ref=record.actor_ref,
            operation="create_and_plan",
            client_key_digest=record.client_key_digest,
        )
        child = (
            None
            if child_record is None
            else OperationClaimResult(record=child_record, created=False, replay=True)
        )
        if child is not None and child.record.final_response_json:
            return workflow_response_from_envelope(
                json.loads(child.record.final_response_json), replayed=True
            )
        plan = json.loads(record.command_plan_json)
        commands = plan["commands"]
        service = MarketingWorkflowService(
            self.application.marketing_workflows, authority=self.authority
        )
        workflow = None
        try:
            workflow = self.application.marketing_workflows.get(
                tenant_id=record.tenant_id,
                brand_id=record.brand_id,
                workflow_id=record.workflow_id,
            )
        except WorkflowAccessDeniedError:
            workflow = None
        if record.progress_state is OrchestrationProgress.CLAIMED:
            if workflow is None:
                create_safe = commands[0]["safe_command"]
                campaign = create_safe["campaign_plan"]
                brief = create_safe.get("marketing_brief")
                command = self._command(
                    tenant_id=record.tenant_id,
                    brand_id=record.brand_id,
                    actor_ref=record.actor_ref,
                    workflow_id=record.workflow_id,
                    client_digest=record.client_key_digest,
                    orchestration_id=record.orchestration_id,
                    ordinal=1,
                    kind="create_workflow",
                    expected=1,
                    safe=create_safe,
                    requested_at=plan["requested_at"],
                )
                service.create(
                    command,
                    campaign_plan_id=campaign["id"],
                    campaign_plan_version=campaign["version"],
                    marketing_brief_id=brief.get("id") if brief else None,
                    marketing_brief_version=brief.get("version") if brief else None,
                )
            workflow = self.application.marketing_workflows.get(
                tenant_id=record.tenant_id,
                brand_id=record.brand_id,
                workflow_id=record.workflow_id,
            )
            # Migration 20 requires a non-null workflow foreign key.  Create
            # the operation child immediately after the workflow exists and
            # before advancing the parent or issuing further transitions.
            if child is None:
                child = self._operation_claim(
                    parent=record,
                    tenant_id=record.tenant_id,
                    brand_id=record.brand_id,
                    actor_ref=record.actor_ref,
                    operation="create_and_plan",
                    client_digest=record.client_key_digest,
                    workflow_id=record.workflow_id,
                    plan=plan,
                    requested_at=plan["requested_at"],
                )
            record = self.application.workflow_orchestrations.advance(
                orchestration_id=record.orchestration_id,
                expected_version=record.version,
                progress_state=OrchestrationProgress.WORKFLOW_CREATED,
                updated_at=utc_timestamp(),
            )
        if child is None:
            if workflow is None:
                workflow = self.application.marketing_workflows.get(
                    tenant_id=record.tenant_id,
                    brand_id=record.brand_id,
                    workflow_id=record.workflow_id,
                )
            child = self._operation_claim(
                parent=record,
                tenant_id=record.tenant_id,
                brand_id=record.brand_id,
                actor_ref=record.actor_ref,
                operation="create_and_plan",
                client_digest=record.client_key_digest,
                workflow_id=record.workflow_id,
                plan=plan,
                requested_at=plan["requested_at"],
            )
        if record.progress_state is OrchestrationProgress.WORKFLOW_CREATED:
            command = self._command(
                tenant_id=record.tenant_id,
                brand_id=record.brand_id,
                actor_ref=record.actor_ref,
                workflow_id=record.workflow_id,
                client_digest=record.client_key_digest,
                orchestration_id=record.orchestration_id,
                ordinal=2,
                kind="plan_workflow",
                expected=workflow.version,
                safe={
                    "operation": "transition",
                    "target_state": "planned",
                    "action": "internal_planning",
                },
                requested_at=plan["requested_at"],
            )
            service.transition(command, target_state=WorkflowState.PLANNED)
            record = self.application.workflow_orchestrations.advance(
                orchestration_id=record.orchestration_id,
                expected_version=record.version,
                progress_state=OrchestrationProgress.PLANNED,
                updated_at=utc_timestamp(),
            )
            workflow = self.application.marketing_workflows.get(
                tenant_id=record.tenant_id,
                brand_id=record.brand_id,
                workflow_id=record.workflow_id,
            )
        if record.progress_state is OrchestrationProgress.PLANNED:
            command = self._command(
                tenant_id=record.tenant_id,
                brand_id=record.brand_id,
                actor_ref=record.actor_ref,
                workflow_id=record.workflow_id,
                client_digest=record.client_key_digest,
                orchestration_id=record.orchestration_id,
                ordinal=3,
                kind="request_approval",
                expected=workflow.version,
                safe={
                    "operation": "transition",
                    "target_state": "awaiting_approval",
                    "action": "internal_planning",
                },
                requested_at=plan["requested_at"],
            )
            service.transition(command, target_state=WorkflowState.AWAITING_APPROVAL)
            record = self.application.workflow_orchestrations.advance(
                orchestration_id=record.orchestration_id,
                expected_version=record.version,
                progress_state=OrchestrationProgress.AWAITING_APPROVAL,
                updated_at=utc_timestamp(),
            )
        status = self.status(
            principal=principal,
            tenant_id=tenant_id,
            brand_id=record.brand_id,
            workflow_id=record.workflow_id,
        )
        progress_order = (
            OrchestrationProgress.WORKFLOW_CREATED,
            OrchestrationProgress.PLANNED,
            OrchestrationProgress.AWAITING_APPROVAL,
        )
        for target in progress_order:
            if child.record.progress_state is target:
                continue
            if child.record.progress_ordinal >= PROGRESS_ORDINAL[target]:
                continue
            child = type(child)(
                record=self.application.workflow_operation_claims.advance(
                    operation_claim_id=child.record.operation_claim_id,
                    expected_version=child.record.version,
                    progress_state=target,
                    updated_at=utc_timestamp(),
                ),
                created=child.created,
                replay=child.replay,
            )
        return self._persist_operation_response(
            child,
            status=202,
            state=OrchestrationProgress.AWAITING_APPROVAL,
            data=status.data,
        )

    def status(self, *, principal, tenant_id: str, brand_id: str, workflow_id: str):
        self._authorize(
            principal, tenant_id, Permission.VIEW, "workflow", workflow_id, brand_id
        )
        actor = self.actor_ref(principal)
        include = self._has_approve(principal, tenant_id)
        workflow = self.application.marketing_workflows.get(
            tenant_id=tenant_id, brand_id=brand_id, workflow_id=workflow_id
        )
        client_digest = idempotency_key_sha256(
            f"status:{workflow_id}:{workflow.version}:{actor}"
        )
        requested_at = workflow.updated_at
        plan = self._operation_plan(
            tenant_id=tenant_id,
            brand_id=brand_id,
            actor_ref=actor,
            workflow_id=workflow_id,
            operation="status",
            client_digest=client_digest,
            parent_id=(
                self.application.workflow_orchestrations.get_by_workflow(
                    tenant_id=tenant_id, brand_id=brand_id, workflow_id=workflow_id
                )
                or type("Root", (), {"orchestration_id": f"status_{workflow_id}"})()
            ).orchestration_id,
            command_kind="status",
            expected=workflow.version,
            safe={"operation": "status", "action": "operator_status_view"},
            requested_at=requested_at,
        )
        parent = self._parent_root(
            tenant_id=tenant_id,
            brand_id=brand_id,
            workflow_id=workflow_id,
            actor_ref=actor,
            operation="status",
            client_digest=client_digest,
            plan=plan,
            requested_at=requested_at,
        )
        plan = self._operation_plan(
            tenant_id=tenant_id,
            brand_id=brand_id,
            actor_ref=actor,
            workflow_id=workflow_id,
            operation="status",
            client_digest=client_digest,
            parent_id=parent.orchestration_id,
            command_kind="status",
            expected=workflow.version,
            safe={"operation": "status", "action": "operator_status_view"},
            requested_at=requested_at,
        )
        claim = self._operation_claim(
            parent=parent,
            tenant_id=tenant_id,
            brand_id=brand_id,
            actor_ref=actor,
            operation="status",
            client_digest=client_digest,
            workflow_id=workflow_id,
            plan=plan,
            requested_at=requested_at,
        )
        service = MarketingWorkflowService(
            self.application.marketing_workflows, authority=self.authority
        )
        data = self._status_data(
            service.operator_status(
                tenant_id=tenant_id,
                brand_id=brand_id,
                workflow_id=workflow_id,
                actor_ref=actor,
                include_technical_details=include,
            ),
            technical=include,
        )
        return self._persist_operation_response(
            claim, data=data, status=200, state=OrchestrationProgress.CLAIMED
        )

    def _has_approve(self, principal, tenant_id: str) -> bool:
        membership = self.application.identities.get_membership(
            provider=principal.provider,
            subject_id=principal.subject_id,
            tenant_id=tenant_id,
        )
        return bool(membership and membership.grants(Permission.APPROVE))

    def request_approval(
        self,
        *,
        principal,
        tenant_id: str,
        brand_id: str,
        workflow_id: str,
        expected_version: int,
        idempotency_key: str,
    ):
        self._authorize(
            principal, tenant_id, Permission.GENERATE, "workflow", workflow_id, brand_id
        )
        workflow = self.application.marketing_workflows.get(
            tenant_id=tenant_id, brand_id=brand_id, workflow_id=workflow_id
        )
        actor = self.actor_ref(principal)
        client_digest = idempotency_key_sha256(
            validate_client_idempotency_key(idempotency_key)
        )
        requested_at = workflow.updated_at
        parent_plan = self._operation_plan(
            tenant_id=tenant_id,
            brand_id=brand_id,
            actor_ref=actor,
            workflow_id=workflow_id,
            operation="request_approval",
            client_digest=client_digest,
            parent_id=f"root_{workflow_id}",
            command_kind="request_approval",
            expected=expected_version,
            safe={
                "operation": "transition",
                "target_state": "awaiting_approval",
                "action": "internal_planning",
            },
            requested_at=requested_at,
        )
        parent = self._parent_root(
            tenant_id=tenant_id,
            brand_id=brand_id,
            workflow_id=workflow_id,
            actor_ref=actor,
            operation="request_approval",
            client_digest=client_digest,
            plan=parent_plan,
            requested_at=requested_at,
        )
        plan = self._operation_plan(
            tenant_id=tenant_id,
            brand_id=brand_id,
            actor_ref=actor,
            workflow_id=workflow_id,
            operation="request_approval",
            client_digest=client_digest,
            parent_id=parent.orchestration_id,
            command_kind="request_approval",
            expected=expected_version,
            safe={
                "operation": "transition",
                "target_state": "awaiting_approval",
                "action": "internal_planning",
            },
            requested_at=requested_at,
        )
        claim = self._operation_claim(
            parent=parent,
            tenant_id=tenant_id,
            brand_id=brand_id,
            actor_ref=actor,
            operation="request_approval",
            client_digest=client_digest,
            workflow_id=workflow_id,
            plan=plan,
            requested_at=requested_at,
        )
        replay = self._replayed_operation(claim)
        if replay is not None:
            return replay
        if workflow.state is WorkflowState.AWAITING_APPROVAL:
            if expected_version != workflow.version:
                raise ValueError("workflow version does not match")
            data = {
                "workflow_id": workflow_id,
                "state": workflow.state.value,
                "workflow_version": workflow.version,
                "next_action": "approval_decision",
            }
            return self._persist_operation_response(
                claim, data=data, status=200, state=OrchestrationProgress.CLAIMED
            )
        command = self._command(
            tenant_id=tenant_id,
            brand_id=brand_id,
            actor_ref=actor,
            workflow_id=workflow_id,
            client_digest=client_digest,
            orchestration_id=parent.orchestration_id,
            ordinal=1,
            kind="request_approval",
            expected=expected_version,
            safe={
                "operation": "transition",
                "target_state": "awaiting_approval",
                "action": "internal_planning",
            },
            requested_at=requested_at,
        )
        receipt = MarketingWorkflowService(
            self.application.marketing_workflows, authority=self.authority
        ).transition(command, target_state=WorkflowState.AWAITING_APPROVAL)
        data = {
            "workflow_id": workflow_id,
            "state": "awaiting_approval",
            "workflow_version": receipt.workflow_version_after,
            "receipt_id": receipt.receipt_id,
        }
        return self._persist_operation_response(
            claim, data=data, status=200, state=OrchestrationProgress.CLAIMED
        )

    def decide(
        self,
        *,
        principal,
        tenant_id: str,
        brand_id: str,
        workflow_id: str,
        expected_version: int,
        decision: str,
        idempotency_key: str,
    ):
        self._authorize(
            principal, tenant_id, Permission.APPROVE, "workflow", workflow_id, brand_id
        )
        workflow = self.application.marketing_workflows.get(
            tenant_id=tenant_id, brand_id=brand_id, workflow_id=workflow_id
        )
        actor = self.actor_ref(principal)
        digest = idempotency_key_sha256(
            validate_client_idempotency_key(idempotency_key)
        )
        existing_claim = self.application.workflow_operation_claims.get_by_claim(
            tenant_id=tenant_id,
            brand_id=brand_id,
            actor_ref=actor,
            operation="approval_decision",
            client_key_digest=digest,
        )
        if existing_claim is not None and existing_claim.final_response_json:
            stored_plan = json.loads(existing_claim.command_plan_json)
            stored_command = stored_plan["commands"][0]
            stored_safe = stored_command["safe_command"]
            candidate_plan = self._operation_plan(
                tenant_id=tenant_id,
                brand_id=brand_id,
                actor_ref=actor,
                workflow_id=workflow_id,
                operation="approval_decision",
                client_digest=digest,
                parent_id=existing_claim.parent_orchestration_id,
                command_kind="record_approval",
                expected=expected_version,
                safe={**stored_safe, "decision": decision},
                requested_at=stored_plan["requested_at"],
            )
            if (
                existing_claim.workflow_id != workflow_id
                or self._request_hash(candidate_plan) != existing_claim.request_hash
            ):
                raise OperationClaimConflictError(existing_claim)
            return workflow_response_from_envelope(
                json.loads(existing_claim.final_response_json), replayed=True
            )
        requester = self._approval_requester(
            tenant_id, brand_id, workflow_id, expected_version
        )
        requested_at = workflow.updated_at
        safe = {
            "operation": "record_approval",
            "action": "internal_planning",
            "decision": decision,
            "requested_by_actor_ref": requester,
        }
        parent_plan = self._operation_plan(
            tenant_id=tenant_id,
            brand_id=brand_id,
            actor_ref=actor,
            workflow_id=workflow_id,
            operation="approval_decision",
            client_digest=digest,
            parent_id=f"root_{workflow_id}",
            command_kind="record_approval",
            expected=expected_version,
            safe=safe,
            requested_at=requested_at,
        )
        parent = self._parent_root(
            tenant_id=tenant_id,
            brand_id=brand_id,
            workflow_id=workflow_id,
            actor_ref=actor,
            operation="approval_decision",
            client_digest=digest,
            plan=parent_plan,
            requested_at=requested_at,
        )
        plan = self._operation_plan(
            tenant_id=tenant_id,
            brand_id=brand_id,
            actor_ref=actor,
            workflow_id=workflow_id,
            operation="approval_decision",
            client_digest=digest,
            parent_id=parent.orchestration_id,
            command_kind="record_approval",
            expected=expected_version,
            safe=safe,
            requested_at=requested_at,
        )
        claim = self._operation_claim(
            parent=parent,
            tenant_id=tenant_id,
            brand_id=brand_id,
            actor_ref=actor,
            operation="approval_decision",
            client_digest=digest,
            workflow_id=workflow_id,
            plan=plan,
            requested_at=requested_at,
        )
        replay = self._replayed_operation(claim)
        if replay is not None:
            return replay
        command = self._command(
            tenant_id=tenant_id,
            brand_id=brand_id,
            actor_ref=actor,
            workflow_id=workflow_id,
            client_digest=digest,
            orchestration_id=parent.orchestration_id,
            ordinal=1,
            kind="record_approval",
            expected=expected_version,
            safe=safe,
            requested_at=requested_at,
        )
        service = MarketingWorkflowService(
            self.application.marketing_workflows, authority=self.authority
        )
        existing_approval = self.application.marketing_workflows.approval_for(
            tenant_id=tenant_id,
            brand_id=brand_id,
            workflow_id=workflow_id,
            workflow_version=workflow.version,
            action="internal_planning",
        )
        if workflow.state is WorkflowState.APPROVED and existing_approval is None:
            raise ValueError("approved workflow lacks its authoritative approval")
        if existing_approval is not None:
            self._validate_approval_evidence(
                tenant_id, brand_id, workflow_id, existing_approval
            )
            if existing_approval.decision.value != decision:
                raise ValueError("approval decision conflicts with existing decision")
            receipt = None
        else:
            receipt = service.record_approval(
                command,
                action="internal_planning",
                decision=ApprovalDecision(decision),
                requested_by_actor_ref=requester,
            )
        orchestration = self.application.workflow_orchestrations.get_by_workflow(
            tenant_id=tenant_id, brand_id=brand_id, workflow_id=workflow_id
        )
        if decision == "approved":
            if workflow.state is WorkflowState.APPROVED:
                transition = None
            else:
                transition = self._command(
                    tenant_id=tenant_id,
                    brand_id=brand_id,
                    actor_ref=actor,
                    workflow_id=workflow_id,
                    client_digest=digest,
                    orchestration_id=parent.orchestration_id,
                    ordinal=2,
                    kind="approve_workflow",
                    expected=expected_version,
                    safe={
                        "operation": "transition",
                        "target_state": "approved",
                        "action": "internal_planning",
                    },
                    requested_at=requested_at,
                )
                receipt = service.transition(
                    transition, target_state=WorkflowState.APPROVED
                )
            if orchestration is not None:
                if (
                    orchestration.progress_state
                    is OrchestrationProgress.AWAITING_APPROVAL
                ):
                    orchestration = self.application.workflow_orchestrations.advance(
                        orchestration_id=orchestration.orchestration_id,
                        expected_version=orchestration.version,
                        progress_state=OrchestrationProgress.APPROVAL_RECORDED,
                        updated_at=utc_timestamp(),
                    )
                if (
                    orchestration.progress_state
                    is OrchestrationProgress.APPROVAL_RECORDED
                ):
                    self.application.workflow_orchestrations.advance(
                        orchestration_id=orchestration.orchestration_id,
                        expected_version=orchestration.version,
                        progress_state=OrchestrationProgress.APPROVED,
                        updated_at=utc_timestamp(),
                    )
            state = "approved"
        else:
            if (
                orchestration is not None
                and orchestration.progress_state
                is OrchestrationProgress.AWAITING_APPROVAL
            ):
                self.application.workflow_orchestrations.advance(
                    orchestration_id=orchestration.orchestration_id,
                    expected_version=orchestration.version,
                    progress_state=OrchestrationProgress.APPROVAL_RECORDED,
                    updated_at=utc_timestamp(),
                )
            state = "planned"
        if receipt is None:
            receipt_id = existing_approval.approval_id
            version_after = workflow.version
        else:
            receipt_id = receipt.receipt_id
            version_after = receipt.workflow_version_after
        data = {
            "workflow_id": workflow_id,
            "state": state,
            "workflow_version": version_after,
            "receipt_id": receipt_id,
            "decision": decision,
        }
        return self._persist_operation_response(
            claim,
            data=data,
            status=200,
            state=(
                OrchestrationProgress.APPROVED
                if decision == "approved"
                else OrchestrationProgress.CLAIMED
            ),
        )

    def _approval_requester(
        self, tenant_id: str, brand_id: str, workflow_id: str, version: int
    ) -> str:
        with self.application.database.connection() as connection:
            rows = connection.execute(
                """
                SELECT evidence_id, tenant_id, brand_id, workflow_id,
                       workflow_version, sequence, predecessor_sha256,
                       evidence_sha256, canonical_json
                FROM workflow_evidence
                WHERE tenant_id = ? AND brand_id = ? AND workflow_id = ?
                ORDER BY sequence ASC
                """,
                (tenant_id, brand_id, workflow_id),
            ).fetchall()
            receipts = {}
            for row in rows:
                envelope = json.loads(str(row["canonical_json"]))
                if (
                    envelope.get("record_kind") != "workflow_evidence"
                    or envelope.get("evidence_id") != row["evidence_id"]
                    or envelope.get("tenant_id") != tenant_id
                    or envelope.get("brand_id") != brand_id
                    or envelope.get("workflow_id") != workflow_id
                    or envelope.get("workflow_version") != int(row["workflow_version"])
                ):
                    raise ValueError("approval requester evidence identity is invalid")
                receipt_id = envelope.get("command_receipt_id")
                if receipt_id:
                    receipt = connection.execute(
                        """
                        SELECT receipt_id, tenant_id, brand_id, workflow_id,
                               command_kind, outcome, canonical_json, receipt_hash
                        FROM workflow_command_receipts
                        WHERE receipt_id = ?
                        """,
                        (receipt_id,),
                    ).fetchone()
                    if receipt is None:
                        raise ValueError("approval requester receipt is missing")
                    receipt_envelope = json.loads(str(receipt["canonical_json"]))
                    if (
                        receipt_envelope.get("record_kind") != "command_receipt"
                        or receipt_envelope.get("receipt_id") != receipt["receipt_id"]
                        or receipt_envelope.get("tenant_id") != tenant_id
                        or receipt_envelope.get("brand_id") != brand_id
                        or receipt_envelope.get("request_workflow_id") != workflow_id
                        or receipt_envelope.get("command_kind")
                        != envelope.get("action")
                        or receipt_envelope.get("request_hash")
                        != envelope.get("sanitized_input_sha256")
                        or record_sha256("command_receipt", receipt_envelope)
                        != receipt["receipt_hash"]
                    ):
                        raise ValueError(
                            "approval requester receipt material is invalid"
                        )
                    receipts[str(receipt_id)] = receipt
        if not rows:
            raise ValueError("approval requester evidence is missing or ambiguous")
        expected_sequence = 1
        predecessor = "0" * 64
        matches = []
        for row in rows:
            envelope = json.loads(str(row["canonical_json"]))
            if int(row["sequence"]) != expected_sequence:
                raise ValueError("approval requester evidence sequence is invalid")
            if str(row["predecessor_sha256"]) != predecessor:
                raise ValueError("approval requester evidence chain is invalid")
            digest = record_sha256("workflow_evidence", envelope)
            if digest != str(row["evidence_sha256"]):
                raise ValueError("approval requester evidence digest is invalid")
            if envelope.get("command_receipt_id") is None:
                raise ValueError(
                    "approval requester evidence receipt binding is missing"
                )
            predecessor = digest
            expected_sequence += 1
            if (
                envelope.get("to_state") == "awaiting_approval"
                and envelope.get("action") == "transition"
            ):
                if (
                    envelope.get("tenant_id") != tenant_id
                    or envelope.get("brand_id") != brand_id
                    or envelope.get("workflow_id") != workflow_id
                    or envelope.get("workflow_version") != version
                    or envelope.get("action") != "transition"
                    or envelope.get("from_state") != "planned"
                    or not envelope.get("command_receipt_id")
                ):
                    raise ValueError("approval requester evidence binding is invalid")
                receipt = receipts.get(str(envelope["command_receipt_id"]))
                if receipt is None or any(
                    (
                        receipt["tenant_id"] != tenant_id,
                        receipt["brand_id"] != brand_id,
                        receipt["workflow_id"] != workflow_id,
                        receipt["command_kind"] != "transition",
                        str(receipt["outcome"]) != "applied",
                        int(
                            json.loads(str(receipt["canonical_json"]))[
                                "workflow_version_after"
                            ]
                        )
                        != version,
                        json.loads(str(receipt["canonical_json"])).get("request_id")
                        is None,
                    )
                ):
                    raise ValueError("approval requester receipt binding is invalid")
                matches.append(envelope.get("actor_ref"))
        if len(matches) != 1 or not matches[0]:
            raise ValueError("approval requester evidence is missing or ambiguous")
        return str(matches[0])

    def _validate_approval_evidence(
        self, tenant_id: str, brand_id: str, workflow_id: str, approval
    ) -> None:
        """Require one canonical evidence/receipt pair for an existing approval."""

        with self.application.database.connection() as connection:
            rows = connection.execute(
                """
                SELECT evidence_id, canonical_json, evidence_sha256
                FROM workflow_evidence
                WHERE tenant_id = ? AND brand_id = ? AND workflow_id = ?
                ORDER BY sequence ASC
                """,
                (tenant_id, brand_id, workflow_id),
            ).fetchall()
            matches = []
            for row in rows:
                envelope = json.loads(str(row["canonical_json"]))
                approval_ref = envelope.get("approval_ref")
                if not isinstance(approval_ref, dict):
                    continue
                if (
                    approval_ref.get("kind") != "workflow_approval"
                    or approval_ref.get("id") != approval.approval_id
                    or approval_ref.get("version") != approval.workflow_version
                    or envelope.get("tenant_id") != tenant_id
                    or envelope.get("brand_id") != brand_id
                    or envelope.get("workflow_id") != workflow_id
                    or envelope.get("workflow_version") != approval.workflow_version
                    or envelope.get("action") != "record_approval"
                    or envelope.get("actor_ref") != approval.decided_by_actor_ref
                    or record_sha256("workflow_evidence", envelope)
                    != row["evidence_sha256"]
                ):
                    raise ValueError("approval evidence binding is invalid")
                receipt_id = envelope.get("command_receipt_id")
                if not receipt_id:
                    raise ValueError("approval evidence receipt is missing")
                receipt = connection.execute(
                    """
                    SELECT receipt_id, tenant_id, brand_id, workflow_id,
                           command_kind, outcome, canonical_json, receipt_hash
                    FROM workflow_command_receipts
                    WHERE receipt_id = ?
                    """,
                    (receipt_id,),
                ).fetchone()
                if receipt is None:
                    raise ValueError("approval evidence receipt is missing")
                receipt_envelope = json.loads(str(receipt["canonical_json"]))
                safe_refs = receipt_envelope.get("safe_result_refs")
                if (
                    receipt_envelope.get("record_kind") != "command_receipt"
                    or receipt_envelope.get("receipt_id") != receipt_id
                    or receipt_envelope.get("tenant_id") != tenant_id
                    or receipt_envelope.get("brand_id") != brand_id
                    or receipt_envelope.get("request_workflow_id") != workflow_id
                    or receipt_envelope.get("command_kind") != "record_approval"
                    or receipt_envelope.get("outcome") != "applied"
                    or receipt_envelope.get("workflow_version_after")
                    != approval.workflow_version
                    or record_sha256("command_receipt", receipt_envelope)
                    != receipt["receipt_hash"]
                    or not isinstance(safe_refs, list)
                    or not any(
                        isinstance(ref, dict)
                        and ref.get("kind") == "workflow_approval"
                        and ref.get("id") == approval.approval_id
                        and ref.get("version") == approval.workflow_version
                        for ref in safe_refs
                    )
                ):
                    raise ValueError("approval evidence receipt binding is invalid")
                matches.append(row["evidence_id"])
        if len(matches) != 1:
            raise ValueError("approval evidence is missing or ambiguous")
