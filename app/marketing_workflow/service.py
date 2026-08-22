"""Deterministic application service for the durable workflow foundation."""

from __future__ import annotations

import hmac
from dataclasses import replace
from uuid import uuid4

from app.marketing_workflow.canonical import utc_timestamp
from app.marketing_workflow.models import (
    ALLOWED_TRANSITIONS,
    EXECUTION_TRANSITIONS,
    HIGH_IMPACT_ACTIONS,
    ORDINARY_ACTIONS,
    TERMINAL_STATES,
    ApprovalDecision,
    ArtifactAvailability,
    ArtifactProof,
    CanonicalArtifactAvailability,
    CanonicalArtifactReference,
    CommandEvaluation,
    CommandReceipt,
    FailureClass,
    MarketingWorkflow,
    OperatorStatus,
    ReceiptOutcome,
    VersionedReference,
    WorkflowApproval,
    WorkflowAuthority,
    WorkflowCommand,
    WorkflowState,
    opaque_actor_ref,
    positive_version,
    required_text,
)
from app.marketing_workflow.repository import (
    MarketingWorkflowRepository,
)


class MarketingWorkflowService:
    """Coordinate policy without owning referenced marketing lifecycles."""

    def __init__(
        self,
        repository: MarketingWorkflowRepository,
        *,
        authority: WorkflowAuthority,
        artifact_availability: CanonicalArtifactAvailability | None = None,
    ) -> None:
        self.repository = repository
        self.authority = authority
        self.artifact_availability = artifact_availability

    def create(
        self,
        command: WorkflowCommand,
        *,
        campaign_plan_id: str,
        campaign_plan_version: int,
        marketing_brief_id: str | None = None,
        marketing_brief_version: int | None = None,
        predecessor_workflow_id: str | None = None,
    ) -> CommandReceipt:
        """Idempotently create one draft aggregate and return its receipt."""

        tenant_id = required_text("tenant_id", command.tenant_id)
        brand_id = required_text("brand_id", command.brand_id)
        actor_ref = opaque_actor_ref(command.actor_ref)
        if not self.authority.permits(
            actor_ref=actor_ref,
            tenant_id=tenant_id,
            brand_id=brand_id,
            action="workflow.create",
            workflow_version=1,
        ):
            raise PermissionError("workflow operation is not authorized")
        if predecessor_workflow_id and not self.authority.permits(
            actor_ref=actor_ref,
            tenant_id=tenant_id,
            brand_id=brand_id,
            action="workflow.failed_recovery",
            workflow_version=1,
        ):
            raise PermissionError("workflow operation is not authorized")
        if bool(marketing_brief_id) != (marketing_brief_version is not None):
            raise ValueError("marketing brief ID and version must be supplied together")
        now = utc_timestamp()
        workflow = MarketingWorkflow(
            workflow_id=command.workflow_id,
            tenant_id=tenant_id,
            brand_id=brand_id,
            campaign_plan=VersionedReference(
                "campaign_plan",
                campaign_plan_id,
                positive_version("campaign_plan_version", campaign_plan_version),
            ),
            marketing_brief=(
                VersionedReference(
                    "marketing_brief",
                    required_text("marketing_brief_id", marketing_brief_id or ""),
                    positive_version(
                        "marketing_brief_version", marketing_brief_version or 0
                    ),
                )
                if marketing_brief_id
                else None
            ),
            predecessor_workflow_id=predecessor_workflow_id,
            state=WorkflowState.DRAFT,
            failure_class=None,
            version=1,
            created_at=now,
            updated_at=now,
        )
        safe_command: dict[str, object] = {
            "schema_version": command.safe_command_schema_version,
            "operation": "create_workflow",
            "campaign_plan": workflow.campaign_plan.to_dict(),
        }
        if workflow.marketing_brief:
            safe_command["marketing_brief"] = workflow.marketing_brief.to_dict()
        if predecessor_workflow_id:
            safe_command["predecessor_workflow_id"] = predecessor_workflow_id
        creation_command = replace(
            command,
            command_kind="create_workflow",
            expected_workflow_version=1,
            safe_command=safe_command,
        )
        return self.repository.create(creation_command, workflow)

    def recover_failed(
        self, command: WorkflowCommand, failed: MarketingWorkflow
    ) -> CommandReceipt:
        """Create a new aggregate; never revive the failed predecessor."""

        if failed.state is not WorkflowState.FAILED:
            raise ValueError("only a failed workflow can be a recovery predecessor")
        return self.create(
            command,
            campaign_plan_id=failed.campaign_plan.id,
            campaign_plan_version=failed.campaign_plan.version,
            marketing_brief_id=(
                failed.marketing_brief.id if failed.marketing_brief else None
            ),
            marketing_brief_version=(
                failed.marketing_brief.version if failed.marketing_brief else None
            ),
            predecessor_workflow_id=failed.workflow_id,
        )

    def transition(
        self,
        command: WorkflowCommand,
        *,
        target_state: WorkflowState,
        action: str = "internal_planning",
        failure_class: FailureClass | None = None,
        successor_workflow_id: str | None = None,
        artifact_ref: CanonicalArtifactReference | None = None,
    ) -> CommandReceipt:
        """Apply the accepted default-deny matrix through one atomic command."""

        action = required_text("action", action)
        safe_command: dict[str, object] = {
            "schema_version": command.safe_command_schema_version,
            "operation": "transition",
            "target_state": target_state.value,
            "action": action,
        }
        if failure_class is not None:
            safe_command["failure_class"] = failure_class.value
        if successor_workflow_id is not None:
            safe_command["successor_workflow_id"] = successor_workflow_id
        if artifact_ref is not None:
            safe_command["artifact_ref"] = artifact_ref.to_dict()
        command = replace(
            command,
            command_kind="transition",
            safe_command=safe_command,
        )

        def evaluate(workflow: MarketingWorkflow) -> CommandEvaluation:
            denied = self._base_command_denial(command, workflow, "workflow.transition")
            if denied:
                return denied
            if action not in ORDINARY_ACTIONS and action not in HIGH_IMPACT_ACTIONS:
                return self._rejected(
                    FailureClass.POLICY_BLOCKED, "action_unclassified"
                )
            if action in HIGH_IMPACT_ACTIONS:
                approval = self.repository.approved_for(
                    tenant_id=workflow.tenant_id,
                    brand_id=workflow.brand_id,
                    workflow_id=workflow.workflow_id,
                    workflow_version=workflow.version,
                    action=action,
                )
                if approval is None:
                    return self._rejected(
                        FailureClass.POLICY_BLOCKED, "approval_required"
                    )
            if target_state is WorkflowState.APPROVED:
                approval = self.repository.approved_for(
                    tenant_id=workflow.tenant_id,
                    brand_id=workflow.brand_id,
                    workflow_id=workflow.workflow_id,
                    workflow_version=workflow.version,
                    action=action,
                )
                if approval is None:
                    return self._rejected(
                        FailureClass.POLICY_BLOCKED, "approval_required"
                    )
            if workflow.state in TERMINAL_STATES:
                return self._rejected(FailureClass.VALIDATION_FAILED, "terminal_state")
            allowed = ALLOWED_TRANSITIONS[workflow.state]
            if workflow.state is WorkflowState.BLOCKED:
                allowed = allowed | (
                    frozenset({workflow.blocked_resume_state})
                    if workflow.blocked_resume_state
                    else frozenset()
                )
                if target_state is workflow.blocked_resume_state:
                    if not self.authority.permits(
                        actor_ref=command.actor_ref,
                        tenant_id=command.tenant_id,
                        brand_id=command.brand_id,
                        action="workflow.manual_recovery",
                        workflow_version=workflow.version,
                    ):
                        return self._rejected(
                            FailureClass.AUTH_REQUIRED, "manual_recovery_not_authorized"
                        )
            if target_state not in allowed:
                return self._rejected(
                    FailureClass.VALIDATION_FAILED, "transition_not_allowed"
                )
            if target_state is WorkflowState.SUPERSEDED and not successor_workflow_id:
                return self._rejected(
                    FailureClass.VALIDATION_FAILED, "successor_reference_required"
                )
            if (workflow.state, target_state) in EXECUTION_TRANSITIONS:
                proof_result = self._artifact_proof(
                    workflow, target_state=target_state, reference=artifact_ref
                )
                if isinstance(proof_result, CommandEvaluation):
                    return proof_result
                artifact_proof = proof_result
            else:
                artifact_proof = None
            if (
                target_state in {WorkflowState.BLOCKED, WorkflowState.FAILED}
                and failure_class is None
            ):
                return self._rejected(
                    FailureClass.VALIDATION_FAILED, "failure_class_required"
                )
            return CommandEvaluation(
                outcome=ReceiptOutcome.APPLIED,
                failure_class=None,
                reason_code="transition_applied",
                target_state=target_state,
                evidence_failure_class=(
                    failure_class
                    if target_state in {WorkflowState.BLOCKED, WorkflowState.FAILED}
                    else None
                ),
                blocked_resume_state=(
                    workflow.state if target_state is WorkflowState.BLOCKED else None
                ),
                successor_workflow_id=successor_workflow_id,
                canonical_artifact_ref=artifact_ref,
                artifact_proof=artifact_proof,
                advance_workflow_version=True,
            )

        return self.repository.execute(command, evaluate)

    def record_approval(
        self,
        command: WorkflowCommand,
        *,
        action: str,
        decision: ApprovalDecision,
        requested_by_actor_ref: str,
    ) -> CommandReceipt:
        """Append an immutable decision bound to the exact workflow version/action."""

        action = required_text("action", action)
        requester = opaque_actor_ref(requested_by_actor_ref)
        command = replace(
            command,
            command_kind="record_approval",
            safe_command={
                "schema_version": command.safe_command_schema_version,
                "operation": "record_approval",
                "action": action,
                "decision": decision.value,
                "requested_by_actor_ref": requester,
            },
        )

        def evaluate(workflow: MarketingWorkflow) -> CommandEvaluation:
            denied = self._base_command_denial(command, workflow, "workflow.approve")
            if denied:
                return denied
            if action not in HIGH_IMPACT_ACTIONS and action not in ORDINARY_ACTIONS:
                return self._rejected(
                    FailureClass.POLICY_BLOCKED, "action_unclassified"
                )
            if action in HIGH_IMPACT_ACTIONS and hmac.compare_digest(
                requester, command.actor_ref
            ):
                return self._rejected(
                    FailureClass.POLICY_BLOCKED, "separation_of_duties_required"
                )
            if (
                self.repository.approval_for(
                    tenant_id=workflow.tenant_id,
                    brand_id=workflow.brand_id,
                    workflow_id=workflow.workflow_id,
                    workflow_version=workflow.version,
                    action=action,
                )
                is not None
            ):
                return self._rejected(
                    FailureClass.CONFLICT_DETECTED,
                    "approval_binding_already_decided",
                )
            approval = WorkflowApproval(
                approval_id=f"mwa_{uuid4().hex}",
                tenant_id=workflow.tenant_id,
                brand_id=workflow.brand_id,
                workflow_id=workflow.workflow_id,
                workflow_version=workflow.version,
                action=action,
                decision=decision,
                requested_by_actor_ref=requester,
                decided_by_actor_ref=command.actor_ref,
                decided_at=utc_timestamp(),
            )
            return CommandEvaluation(
                outcome=ReceiptOutcome.APPLIED,
                failure_class=None,
                reason_code="approval_recorded",
                approval=approval,
                safe_result_refs=(
                    VersionedReference(
                        "workflow_approval", approval.approval_id, workflow.version
                    ),
                ),
            )

        return self.repository.execute(command, evaluate)

    def operator_status(
        self,
        *,
        tenant_id: str,
        brand_id: str,
        workflow_id: str,
        actor_ref: str,
        include_technical_details: bool = False,
    ) -> OperatorStatus:
        workflow = self.repository.get(
            tenant_id=tenant_id, brand_id=brand_id, workflow_id=workflow_id
        )
        if not self.authority.permits(
            actor_ref=actor_ref,
            tenant_id=tenant_id,
            brand_id=brand_id,
            action="workflow.status",
            workflow_version=workflow.version,
        ):
            raise PermissionError("workflow operation is not authorized")
        details: dict[str, object] = {}
        if include_technical_details and self.authority.permits(
            actor_ref=actor_ref,
            tenant_id=tenant_id,
            brand_id=brand_id,
            action="workflow.status.technical",
            workflow_version=workflow.version,
        ):
            details = {
                "campaign_plan_ref": workflow.campaign_plan.to_dict(),
                "marketing_brief_ref": (
                    workflow.marketing_brief.to_dict()
                    if workflow.marketing_brief
                    else None
                ),
                "blocked_resume_state": (
                    workflow.blocked_resume_state.value
                    if workflow.blocked_resume_state
                    else None
                ),
            }
        return OperatorStatus(
            workflow_id=workflow.workflow_id,
            state=workflow.state,
            workflow_version=workflow.version,
            next_action=self._next_action(workflow),
            blocked_reason=workflow.failure_class,
            retry_available=False,
            required_approval=(
                "workflow_action_approval"
                if workflow.state is WorkflowState.AWAITING_APPROVAL
                else None
            ),
            evidence_available=True,
            technical_details=details,
        )

    def _base_command_denial(
        self,
        command: WorkflowCommand,
        workflow: MarketingWorkflow,
        authority_action: str,
    ) -> CommandEvaluation | None:
        if command.expected_workflow_version != workflow.version:
            return self._rejected(FailureClass.CONFLICT_DETECTED, "version_conflict")
        if not self.authority.permits(
            actor_ref=command.actor_ref,
            tenant_id=command.tenant_id,
            brand_id=command.brand_id,
            action=authority_action,
            workflow_version=workflow.version,
        ):
            return self._rejected(FailureClass.AUTH_REQUIRED, "authorization_required")
        return None

    def _artifact_proof(
        self,
        workflow: MarketingWorkflow,
        *,
        target_state: WorkflowState,
        reference: CanonicalArtifactReference | None,
    ) -> CommandEvaluation | ArtifactProof:
        if reference is None or self.artifact_availability is None:
            return self._rejected(
                FailureClass.POLICY_BLOCKED, "artifact_proof_unavailable"
            )
        if (
            reference.tenant_id != workflow.tenant_id
            or reference.brand_id != workflow.brand_id
        ):
            return self._rejected(
                FailureClass.AUTH_REQUIRED, "artifact_proof_unavailable"
            )
        proof = self.artifact_availability.prove(
            tenant_id=workflow.tenant_id,
            brand_id=workflow.brand_id,
            reference=reference,
        )
        if proof is None or proof.reference != reference:
            return self._rejected(
                FailureClass.POLICY_BLOCKED, "artifact_proof_unavailable"
            )
        if target_state is WorkflowState.COMPLETED:
            if (
                proof.availability is not ArtifactAvailability.PERSISTED
                or not proof.content_sha256
            ):
                return self._rejected(
                    FailureClass.POLICY_BLOCKED, "persisted_artifact_proof_required"
                )
        elif proof.availability not in {
            ArtifactAvailability.RESERVED,
            ArtifactAvailability.PERSISTED,
        }:
            return self._rejected(
                FailureClass.POLICY_BLOCKED, "artifact_proof_unavailable"
            )
        return proof

    @staticmethod
    def _rejected(failure: FailureClass, reason: str) -> CommandEvaluation:
        return CommandEvaluation(
            outcome=ReceiptOutcome.REJECTED,
            failure_class=failure,
            reason_code=reason,
        )

    @staticmethod
    def _next_action(workflow: MarketingWorkflow) -> str | None:
        return {
            WorkflowState.DRAFT: "complete_plan",
            WorkflowState.PLANNED: "request_approval",
            WorkflowState.AWAITING_APPROVAL: "decide_approval",
            WorkflowState.APPROVED: "confirm_artifact_persistence",
            WorkflowState.RUNNING: "complete_or_block",
            WorkflowState.BLOCKED: "manual_intervention",
        }.get(workflow.state)
