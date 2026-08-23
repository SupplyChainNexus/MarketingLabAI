"""Focused MLAI-033.1 durable workflow foundation tests."""

from __future__ import annotations

import json
import sqlite3
import tempfile
import threading
import unittest
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from pathlib import Path

from app.database.connection import SQLiteDatabase
from app.database.postgresql import build_postgresql_schema, compile_postgresql_sql
from app.marketing_workflow.canonical import (
    MLAI_CJ_1,
    MLAI_CJ_2,
    canonical_json,
    deterministic_actor_ref,
    deterministic_command_key_digest,
    deterministic_subcommand_request_id,
    deterministic_workflow_id,
    idempotency_key_sha256,
    record_sha256,
    utc_timestamp,
    validate_client_idempotency_key,
)
from app.marketing_workflow.models import (
    ApprovalDecision,
    ArtifactAvailability,
    ArtifactProof,
    CanonicalArtifactReference,
    FailureClass,
    ReceiptOutcome,
    WorkflowCommand,
    WorkflowState,
)
from app.marketing_workflow.repository import (
    GENESIS_PREDECESSOR,
    MarketingWorkflowRepository,
    WorkflowAccessDeniedError,
)
from app.marketing_workflow.service import MarketingWorkflowService


class _AllowAuthority:
    def permits(self, **_kwargs) -> bool:
        return True


class _ArtifactAvailability:
    def __init__(self) -> None:
        self.proof: ArtifactProof | None = None

    def prove(self, **_kwargs) -> ArtifactProof | None:
        return self.proof


class _GatedConnection:
    def __init__(self, connection, gate: "_TransactionGate") -> None:
        self._connection = connection
        self._gate = gate

    def execute(self, sql, parameters=()):
        return self._gate.execute(self._connection, sql, parameters)

    def __getattr__(self, name):
        return getattr(self._connection, name)


class _SuccessfulNoOp:
    rowcount = 1


class _TransactionGate:
    """Expose deterministic contention at one exact workflow-row lock."""

    def __init__(
        self,
        database: SQLiteDatabase,
        *,
        held_workflow_id: str,
        failed_predecessor_lock: bool = False,
    ) -> None:
        self.database = database
        self.held_workflow_id = held_workflow_id
        self.failed_predecessor_lock = failed_predecessor_lock
        self.roles = threading.local()
        self.contender_connection_ready = threading.Event()
        self.holder_acquired = threading.Event()
        self.contender_reached = threading.Event()
        self.contender_acquired = threading.Event()
        self.release_holder = threading.Event()

    @contextmanager
    def transaction(self):
        connection = self.database.connect()
        try:
            connection.execute("BEGIN")
            if self.roles.role == "contender":
                self.contender_connection_ready.set()
                if not self.holder_acquired.wait(timeout=5):
                    raise TimeoutError("holder did not acquire the target row lock")
            elif not self.contender_connection_ready.wait(timeout=5):
                raise TimeoutError("contender did not open its SQLite connection")
            yield _GatedConnection(connection, self)
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    def __getattr__(self, name):
        return getattr(self.database, name)

    def execute(self, connection, sql, parameters):
        normalized = " ".join(sql.split())
        role = self.roles.role
        if (
            role == "contender"
            and self.failed_predecessor_lock
            and "UPDATE brands SET brand_id = brand_id" in normalized
        ):
            return _SuccessfulNoOp()
        is_target_lock = (
            "UPDATE marketing_workflows SET version = version" in normalized
            and self.held_workflow_id in parameters
            and (
                not self.failed_predecessor_lock or "AND state = 'failed'" in normalized
            )
        )
        if role == "contender" and is_target_lock:
            self.contender_reached.set()
        result = connection.execute(sql, parameters)
        if role == "holder" and is_target_lock:
            self.holder_acquired.set()
            if not self.release_holder.wait(timeout=5):
                raise TimeoutError("timed out while holding workflow contention gate")
        elif role == "contender" and is_target_lock:
            self.contender_acquired.set()
        return result

    def enter(self, role: str) -> None:
        """Bind a worker role before it enters the instrumented transaction."""

        self.roles.role = role


class MarketingWorkflowFoundationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.database = SQLiteDatabase(
            Path(self.temporary_directory.name) / "workflow.sqlite3"
        )
        self.database.initialise()
        with self.database.transaction() as connection:
            connection.execute(
                """
                INSERT INTO brands (
                    brand_id, name, payload_json, created_at, updated_at, tenant_id
                ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                ("brand-1", "Brand One", "{}", "now", "now", "default"),
            )
            connection.execute(
                """
                INSERT INTO campaign_plans (
                    campaign_id, version, tenant_id, brand_id, name, status,
                    payload_json, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    "plan-1",
                    1,
                    "default",
                    "brand-1",
                    "Plan One",
                    "draft",
                    "{}",
                    "now",
                    "now",
                ),
            )
        self.artifacts = _ArtifactAvailability()
        self.repository = MarketingWorkflowRepository(self.database)
        self.service = MarketingWorkflowService(
            self.repository,
            authority=_AllowAuthority(),
            artifact_availability=self.artifacts,
        )
        self.command_index = 0

    def tearDown(self) -> None:
        self.temporary_directory.cleanup()

    def _command(
        self,
        workflow_id: str,
        *,
        version: int = 1,
        key: str | None = None,
        actor: str = "actor:operator",
    ) -> WorkflowCommand:
        self.command_index += 1
        return WorkflowCommand(
            request_id=f"request-{self.command_index}",
            tenant_id="default",
            brand_id="brand-1",
            workflow_id=workflow_id,
            expected_workflow_version=version,
            command_kind="pending",
            caller_idempotency_key=key or f"key-{self.command_index}",
            actor_ref=actor,
            requested_at=utc_timestamp(),
            safe_command={},
        )

    def _create(self, workflow_id: str, *, key: str | None = None):
        return self.service.create(
            self._command(workflow_id, key=key),
            campaign_plan_id="plan-1",
            campaign_plan_version=1,
        )

    def _transition(
        self,
        workflow_id: str,
        version: int,
        target: WorkflowState,
        *,
        key: str | None = None,
        failure: FailureClass | None = None,
        artifact_ref: CanonicalArtifactReference | None = None,
    ):
        return self.service.transition(
            self._command(workflow_id, version=version, key=key),
            target_state=target,
            failure_class=failure,
            artifact_ref=artifact_ref,
        )

    def _failed_workflow(self, workflow_id: str):
        self._create(workflow_id)
        self._transition(workflow_id, 1, WorkflowState.PLANNED)
        self._transition(
            workflow_id,
            2,
            WorkflowState.BLOCKED,
            failure=FailureClass.PROVIDER_ERROR,
        )
        self._transition(
            workflow_id,
            3,
            WorkflowState.FAILED,
            failure=FailureClass.PROVIDER_ERROR,
        )
        return self.repository.get(
            tenant_id="default", brand_id="brand-1", workflow_id=workflow_id
        )

    def test_schema_versions_are_strict_and_dispatch_is_versioned(self) -> None:
        for invalid in (True, False, "2", 2.0, None, object()):
            envelope = {
                "canonicalization_version": MLAI_CJ_2,
                "schema_version": invalid,
                "record_kind": "command_request",
            }
            with self.subTest(value=invalid), self.assertRaises(ValueError):
                record_sha256("command_request", envelope)
            with self.subTest(key_value=invalid), self.assertRaises(ValueError):
                idempotency_key_sha256("key", schema_version=invalid)

        version_one = {
            "canonicalization_version": MLAI_CJ_1,
            "schema_version": 1,
            "record_kind": "command_request",
            "workflow_id": "legacy-workflow",
        }
        version_two = {
            "canonicalization_version": MLAI_CJ_2,
            "schema_version": 2,
            "record_kind": "command_request",
            "request_workflow_id": "workflow-2",
        }
        self.assertEqual(len(record_sha256("command_request", version_one)), 64)
        self.assertEqual(len(record_sha256("command_request", version_two)), 64)
        with self.assertRaises(ValueError):
            record_sha256(
                "command_request",
                {**version_two, "schema_version": 1},
            )
        with self.assertRaises(ValueError):
            self.repository._receipt_from_envelope(
                {
                    "canonicalization_version": MLAI_CJ_2,
                    "schema_version": True,
                    "record_kind": "command_receipt",
                },
                "{}",
                "0" * 64,
            )

        golden_envelope = {
            "canonicalization_version": MLAI_CJ_1,
            "record_kind": "command_request",
            "schema_version": 1,
            "workflow_id": "legacy-workflow",
        }
        self.assertEqual(
            canonical_json(golden_envelope),
            '{"canonicalization_version":"MLAI-CJ-1","record_kind":'
            '"command_request","schema_version":1,"workflow_id":'
            '"legacy-workflow"}',
        )
        self.assertEqual(
            record_sha256("command_request", golden_envelope),
            "6ad2fdf41500a0141fb687f85653cbe6d4da1a138e5766a3eed8ff9358acb0e9",
        )

    def test_mlai_033_2_identity_derivations_have_frozen_vectors(self) -> None:
        client_key = "client-key-0123456789abcdef"
        client_digest = idempotency_key_sha256(client_key)
        self.assertEqual(
            client_digest,
            "72f08398b1dc93426bc383f54115c462b51f804fe4e7be63a7a39c3591f12388",
        )
        self.assertEqual(
            deterministic_workflow_id(
                tenant_id="tenant_demo",
                brand_id="brand_demo",
                actor_ref="act_demo",
                operation="planning_to_approval",
                client_key_digest=client_digest,
            ),
            "mwf_96fed3b7e6a95c30a0f6198dbdf14c63",
        )
        self.assertEqual(
            deterministic_actor_ref(
                provider="identity_provider", subject_id="subject_demo"
            ),
            "act_0800e4ab912d3675c21049a58c88ddf6",
        )
        self.assertEqual(
            deterministic_subcommand_request_id(
                orchestration_id="orch_demo",
                ordinal=1,
                command_kind="create_workflow",
            ),
            "req_f1229366dc43c4c8d5cb7460aa7720ed",
        )
        self.assertEqual(
            deterministic_command_key_digest(
                client_key_digest=client_digest,
                ordinal=1,
                command_kind="create_workflow",
            ),
            "34732600cc0600ffcfea37b98a2b4dd198ec5d92f1139db8125f4a370d9c3e3d",
        )

    def test_client_key_validation_is_strict_without_changing_legacy_keys(self) -> None:
        self.assertEqual(
            validate_client_idempotency_key("client-key-0123456789abcdef"),
            "client-key-0123456789abcdef",
        )
        for invalid in (
            "short",
            "client key with spaces 0123456789",
            "client-key-0123456789abcdef/",
            "x" * 257,
            None,
            True,
        ):
            with (
                self.subTest(value=invalid),
                self.assertRaises((TypeError, ValueError)),
            ):
                validate_client_idempotency_key(invalid)
        self.assertEqual(idempotency_key_sha256("key"), idempotency_key_sha256("key"))

    def test_identity_inputs_are_privacy_safe_and_deterministic(self) -> None:
        workflow = deterministic_workflow_id(
            tenant_id="tenant_demo",
            brand_id="brand_demo",
            actor_ref="act_demo",
            operation="planning_to_approval",
            client_key_digest="a" * 64,
        )
        self.assertTrue(workflow.startswith("mwf_"))
        self.assertEqual(len(workflow), 36)
        self.assertNotIn("tenant_demo", workflow)
        actor = deterministic_actor_ref(
            provider="identity_provider", subject_id="subject_sensitive"
        )
        self.assertNotIn("identity_provider", actor)
        self.assertNotIn("subject_sensitive", actor)

    def test_creation_request_receipt_hashing_and_exact_replay(self) -> None:
        command = self._command("workflow-create", key="create-key")
        request_command = WorkflowCommand(
            request_id=command.request_id,
            tenant_id=command.tenant_id,
            brand_id=command.brand_id,
            workflow_id=command.workflow_id,
            expected_workflow_version=1,
            command_kind="create_workflow",
            caller_idempotency_key=command.caller_idempotency_key,
            actor_ref=command.actor_ref,
            requested_at=command.requested_at,
            safe_command={
                "schema_version": 1,
                "operation": "create_workflow",
                "campaign_plan": {
                    "kind": "campaign_plan",
                    "id": "plan-1",
                    "version": 1,
                },
            },
        )
        request_envelope, _key_digest = self.repository._request_envelope(
            request_command
        )
        receipt = self.service.create(
            command,
            campaign_plan_id="plan-1",
            campaign_plan_version=1,
        )
        replay = self.service.create(
            command,
            campaign_plan_id="plan-1",
            campaign_plan_version=1,
        )
        envelope = json.loads(receipt.canonical_json)

        self.assertEqual(receipt.canonicalization_version, MLAI_CJ_2)
        self.assertEqual(receipt.schema_version, 2)
        self.assertEqual(
            receipt.request_hash,
            record_sha256("command_request", request_envelope),
        )
        self.assertEqual(receipt.canonical_json, replay.canonical_json)
        self.assertEqual(receipt.receipt_sha256, replay.receipt_sha256)
        self.assertEqual(
            receipt.receipt_sha256, record_sha256("command_receipt", envelope)
        )
        self.assertEqual(canonical_json(envelope), receipt.canonical_json)

    def test_transition_idempotency_and_evidence_hash_linking(self) -> None:
        self._create("workflow-transition")
        command = self._command("workflow-transition", version=1, key="transition-key")
        first = self.service.transition(command, target_state=WorkflowState.PLANNED)
        replay = self.service.transition(command, target_state=WorkflowState.PLANNED)
        evidence = self.repository.list_evidence(
            tenant_id="default",
            brand_id="brand-1",
            workflow_id="workflow-transition",
        )

        self.assertEqual(first.receipt_id, replay.receipt_id)
        self.assertEqual([item.sequence for item in evidence], [1, 2])
        self.assertEqual(evidence[0].predecessor_sha256, GENESIS_PREDECESSOR)
        self.assertEqual(evidence[1].predecessor_sha256, evidence[0].evidence_sha256)

    def test_recovery_uniqueness_and_per_hash_conflict_replay(self) -> None:
        failed = self._failed_workflow("failed-1")
        applied = self.service.recover_failed(
            self._command("successor-b", key="recover-b"), failed
        )
        request_a = self._command("successor-a", key="recover-a")
        conflict = self.service.recover_failed(request_a, failed)
        replay = self.service.recover_failed(request_a, failed)

        self.assertEqual(applied.outcome, ReceiptOutcome.APPLIED)
        self.assertEqual(conflict.outcome, ReceiptOutcome.CONFLICT_DETECTED)
        self.assertEqual(conflict.request_workflow_id, "successor-a")
        self.assertEqual(conflict.authoritative_workflow_id, "successor-b")
        self.assertEqual(
            conflict.workflow_version_before, conflict.workflow_version_after
        )
        self.assertEqual(conflict.receipt_id, replay.receipt_id)
        self.assertEqual(
            [(item.kind, item.version) for item in conflict.safe_result_refs],
            [("command_receipt", 1), ("workflow", 1)],
        )
        with self.database.connection() as connection:
            successors = connection.execute(
                """
                SELECT COUNT(*) FROM marketing_workflows
                WHERE predecessor_workflow_id = ?
                """,
                (failed.workflow_id,),
            ).fetchone()[0]
        self.assertEqual(successors, 1)

    def test_changed_predecessor_has_one_durable_conflict_per_hash(self) -> None:
        failed_one = self._failed_workflow("failed-one")
        failed_two = self._failed_workflow("failed-two")
        self.service.recover_failed(
            self._command("successor-b", key="recover-b"), failed_one
        )
        command_a = self._command("successor-a", key="authority-a")
        first = self.service.recover_failed(command_a, failed_one)
        changed = self.service.recover_failed(command_a, failed_two)
        changed_replay = self.service.recover_failed(command_a, failed_two)

        self.assertEqual(changed.outcome, ReceiptOutcome.CONFLICT_DETECTED)
        self.assertEqual(changed.authoritative_workflow_id, "successor-b")
        self.assertNotEqual(first.request_hash, changed.request_hash)
        self.assertEqual(changed.receipt_id, changed_replay.receipt_id)
        with self.database.connection() as connection:
            replay_count = connection.execute(
                """
                SELECT COUNT(*) FROM workflow_recovery_conflict_replays
                WHERE request_workflow_id = ?
                """,
                ("successor-a",),
            ).fetchone()[0]
        self.assertEqual(replay_count, 2)

    def test_concurrent_recovery_creates_one_successor(self) -> None:
        failed = self._failed_workflow("failed-concurrent")
        commands = {
            "holder": self._command("successor-1", key="key-successor-1"),
            "contender": self._command("successor-2", key="key-successor-2"),
        }
        gate = _TransactionGate(
            self.database,
            held_workflow_id=failed.workflow_id,
            failed_predecessor_lock=True,
        )
        self.repository.database = gate

        def recover(role: str):
            gate.enter(role)
            return self.service.recover_failed(commands[role], failed)

        executor = ThreadPoolExecutor(max_workers=2)
        try:
            holder = executor.submit(recover, "holder")
            contender = executor.submit(recover, "contender")
            self.assertTrue(gate.holder_acquired.wait(timeout=5))
            try:
                self.assertTrue(gate.contender_reached.wait(timeout=5))
            finally:
                gate.release_holder.set()
            receipts = (holder.result(timeout=5), contender.result(timeout=5))
            self.assertTrue(gate.contender_acquired.is_set())
        finally:
            gate.release_holder.set()
            executor.shutdown(wait=True, cancel_futures=True)
            self.repository.database = self.database

        self.assertEqual(
            sorted(item.outcome for item in receipts),
            [ReceiptOutcome.APPLIED, ReceiptOutcome.CONFLICT_DETECTED],
        )
        with self.database.connection() as connection:
            count = connection.execute(
                "SELECT COUNT(*) FROM marketing_workflows WHERE predecessor_workflow_id = ?",
                (failed.workflow_id,),
            ).fetchone()[0]
        self.assertEqual(count, 1)
        loser = next(
            item
            for item in receipts
            if item.outcome is ReceiptOutcome.CONFLICT_DETECTED
        )
        evidence_before = self.repository.list_evidence(
            tenant_id="default",
            brand_id="brand-1",
            workflow_id=loser.authoritative_workflow_id,
        )
        with self.database.connection() as connection:
            receipt_count_before = connection.execute(
                """
                SELECT COUNT(*) FROM workflow_command_receipts
                WHERE workflow_id = ?
                """,
                (loser.authoritative_workflow_id,),
            ).fetchone()[0]
        replay = self.service.recover_failed(commands["contender"], failed)
        evidence_after = self.repository.list_evidence(
            tenant_id="default",
            brand_id="brand-1",
            workflow_id=loser.authoritative_workflow_id,
        )
        with self.database.connection() as connection:
            receipt_count_after = connection.execute(
                """
                SELECT COUNT(*) FROM workflow_command_receipts
                WHERE workflow_id = ?
                """,
                (loser.authoritative_workflow_id,),
            ).fetchone()[0]
        self.assertEqual(replay.receipt_id, loser.receipt_id)
        self.assertEqual(replay.canonical_json, loser.canonical_json)
        self.assertEqual(replay.receipt_sha256, loser.receipt_sha256)
        self.assertEqual(receipt_count_after, receipt_count_before)
        self.assertEqual(evidence_after, evidence_before)

    def test_authoritative_lock_serializes_transition_and_conflict_evidence(
        self,
    ) -> None:
        failed = self._failed_workflow("failed-lock")
        self.service.recover_failed(
            self._command("successor-lock-b", key="recover-lock-b"), failed
        )
        conflict_command = self._command("successor-lock-a", key="recover-lock-a")
        transition_command = self._command(
            "successor-lock-b", version=1, key="advance-b"
        )
        gate = _TransactionGate(self.database, held_workflow_id="successor-lock-b")
        self.repository.database = gate

        def conflict():
            gate.enter("holder")
            return self.service.recover_failed(conflict_command, failed)

        def transition():
            gate.enter("contender")
            return self.service.transition(
                transition_command, target_state=WorkflowState.PLANNED
            )

        executor = ThreadPoolExecutor(max_workers=2)
        try:
            conflict_future = executor.submit(conflict)
            transition_future = executor.submit(transition)
            self.assertTrue(gate.holder_acquired.wait(timeout=5))
            try:
                self.assertTrue(gate.contender_reached.wait(timeout=5))
            finally:
                gate.release_holder.set()
            receipts = (
                conflict_future.result(timeout=5),
                transition_future.result(timeout=5),
            )
            self.assertTrue(gate.contender_acquired.is_set())
        finally:
            gate.release_holder.set()
            executor.shutdown(wait=True, cancel_futures=True)
            self.repository.database = self.database

        self.assertEqual(receipts[0].outcome, ReceiptOutcome.CONFLICT_DETECTED)
        self.assertEqual(
            receipts[0].workflow_version_before, receipts[0].workflow_version_after
        )
        self.assertEqual(receipts[0].workflow_version_before, 1)
        self.assertEqual(receipts[1].workflow_version_before, 1)
        self.assertEqual(receipts[1].workflow_version_after, 2)
        evidence = self.repository.list_evidence(
            tenant_id="default", brand_id="brand-1", workflow_id="successor-lock-b"
        )
        self.assertEqual(
            [item.sequence for item in evidence], list(range(1, len(evidence) + 1))
        )
        self.assertEqual(
            len({item.evidence_sha256 for item in evidence}), len(evidence)
        )
        with self.database.connection() as connection:
            receipt_count_before = connection.execute(
                """
                SELECT COUNT(*) FROM workflow_command_receipts
                WHERE workflow_id = ?
                """,
                ("successor-lock-b",),
            ).fetchone()[0]
        replay = self.service.recover_failed(conflict_command, failed)
        replay_evidence = self.repository.list_evidence(
            tenant_id="default", brand_id="brand-1", workflow_id="successor-lock-b"
        )
        with self.database.connection() as connection:
            receipt_count_after = connection.execute(
                """
                SELECT COUNT(*) FROM workflow_command_receipts
                WHERE workflow_id = ?
                """,
                ("successor-lock-b",),
            ).fetchone()[0]
        self.assertEqual(replay.receipt_id, receipts[0].receipt_id)
        self.assertEqual(replay.canonical_json, receipts[0].canonical_json)
        self.assertEqual(replay.receipt_sha256, receipts[0].receipt_sha256)
        self.assertEqual(receipt_count_after, receipt_count_before)
        self.assertEqual(replay_evidence, evidence)

    def test_artifact_proof_fails_closed_then_persists(self) -> None:
        workflow_id = "workflow-artifact"
        self._create(workflow_id)
        self._transition(workflow_id, 1, WorkflowState.PLANNED)
        self._transition(workflow_id, 2, WorkflowState.AWAITING_APPROVAL)
        approval_command = self._command(workflow_id, version=3)
        self.service.record_approval(
            approval_command,
            action="internal_planning",
            decision=ApprovalDecision.APPROVED,
            requested_by_actor_ref="actor:requester",
        )
        self._transition(workflow_id, 3, WorkflowState.APPROVED)
        reference = CanonicalArtifactReference(
            tenant_id="default",
            brand_id="brand-1",
            artifact_id="artifact-1",
            artifact_version=1,
            repository_revision="revision-1",
        )
        denied = self._transition(
            workflow_id, 4, WorkflowState.RUNNING, artifact_ref=reference
        )
        self.assertEqual(denied.failure_class, FailureClass.POLICY_BLOCKED)
        self.artifacts.proof = ArtifactProof(ArtifactAvailability.RESERVED, reference)
        applied = self._transition(
            workflow_id, 4, WorkflowState.RUNNING, artifact_ref=reference
        )
        self.assertEqual(applied.outcome, ReceiptOutcome.APPLIED)
        with self.database.connection() as connection:
            count = connection.execute(
                "SELECT COUNT(*) FROM workflow_artifact_proofs WHERE workflow_id = ?",
                (workflow_id,),
            ).fetchone()[0]
        self.assertEqual(count, 1)

    def test_approval_uniqueness_and_high_impact_separation(self) -> None:
        workflow_id = "workflow-approval"
        self._create(workflow_id)
        separated = self.service.record_approval(
            self._command(workflow_id, actor="actor:decider"),
            action="paid_action",
            decision=ApprovalDecision.APPROVED,
            requested_by_actor_ref="actor:requester",
        )
        duplicate = self.service.record_approval(
            self._command(workflow_id, key="duplicate", actor="actor:other"),
            action="paid_action",
            decision=ApprovalDecision.REJECTED,
            requested_by_actor_ref="actor:requester",
        )
        denied = self.service.record_approval(
            self._command(workflow_id, key="same-actor", actor="actor:same"),
            action="publishing",
            decision=ApprovalDecision.APPROVED,
            requested_by_actor_ref="actor:same",
        )

        self.assertEqual(separated.outcome, ReceiptOutcome.APPLIED)
        self.assertEqual(duplicate.failure_class, FailureClass.CONFLICT_DETECTED)
        self.assertEqual(denied.failure_class, FailureClass.POLICY_BLOCKED)
        with self.database.connection() as connection:
            count = connection.execute(
                "SELECT COUNT(*) FROM workflow_approvals WHERE workflow_id = ?",
                (workflow_id,),
            ).fetchone()[0]
        self.assertEqual(count, 1)

    def test_tenant_non_disclosure_and_retention_protection(self) -> None:
        workflow_id = "workflow-retention"
        self._create(workflow_id)
        with self.assertRaises(WorkflowAccessDeniedError):
            self.repository.get(
                tenant_id="other", brand_id="brand-1", workflow_id=workflow_id
            )
        with self.assertRaises(WorkflowAccessDeniedError):
            self.repository.get(
                tenant_id="default", brand_id="other", workflow_id=workflow_id
            )
        with self.assertRaises(sqlite3.IntegrityError):
            with self.database.transaction() as connection:
                connection.execute(
                    "DELETE FROM marketing_workflows WHERE workflow_id = ?",
                    (workflow_id,),
                )

    def test_postgresql_schema_and_lock_sql_are_compatible(self) -> None:
        schema = "\n".join(build_postgresql_schema())
        self.assertIn("CREATE TABLE IF NOT EXISTS marketing_workflows", schema)
        self.assertIn(
            "CREATE TABLE IF NOT EXISTS workflow_recovery_conflict_replays", schema
        )
        compiled = compile_postgresql_sql("""
            UPDATE marketing_workflows SET version = version
            WHERE tenant_id = ? AND brand_id = ? AND workflow_id = ?
            """)
        self.assertEqual(compiled.count("%s"), 3)


if __name__ == "__main__":
    unittest.main()
