"""Focused tests for the Commit B API-orchestration persistence boundary."""

from __future__ import annotations

import hashlib
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from app.database.connection import SQLiteDatabase
from app.marketing_workflow.canonical import canonical_json_bytes, utc_timestamp
from app.marketing_workflow.orchestration import (
    OperationClaimConflictError,
    OrchestrationConflictError,
    OrchestrationOptimisticConflictError,
    OrchestrationProgress,
    OrchestrationWorkflowConflictError,
    WorkflowApiOperationClaimRepository,
    WorkflowApiOrchestrationRepository,
)


class WorkflowApiOrchestrationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.database = SQLiteDatabase(Path(self.temp.name) / "workflow.db")
        self.database.initialise()
        with self.database.transaction() as connection:
            connection.execute(
                """
                INSERT INTO brands (
                    brand_id, tenant_id, name, payload_json, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                ("brand-one", "default", "Brand One", "{}", "now", "now"),
            )
            connection.execute(
                """
                INSERT INTO marketing_workflows (
                    workflow_id, tenant_id, brand_id, campaign_plan_id,
                    campaign_plan_version, state, version, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    "mwf_demo",
                    "default",
                    "brand-one",
                    "plan-one",
                    1,
                    "draft",
                    1,
                    "now",
                    "now",
                ),
            )
        self.repository = WorkflowApiOrchestrationRepository(self.database)
        self.operation_repository = WorkflowApiOperationClaimRepository(self.database)
        self.request_hash = hashlib.sha256(b"request-one").hexdigest()
        self.key_digest = hashlib.sha256(b"client-key-one").hexdigest()
        self.plan = self._plan()

    def tearDown(self) -> None:
        self.temp.cleanup()

    def _plan(self, *, workflow_id: str = "mwf_demo") -> dict:
        requested_at = "2026-08-23T10:00:00.000000Z"
        return {
            "record_kind": "workflow_orchestration_plan",
            "orchestration_plan_version": 1,
            "canonicalization_version": "MLAI-CJ-2",
            "mlai_cj_schema_version": 2,
            "safe_command_schema_version": 1,
            "tenant_id": "default",
            "brand_id": "brand-one",
            "actor_ref": "act_operator",
            "operation": "planning_to_approval",
            "workflow_id": workflow_id,
            "client_key_digest": self.key_digest,
            "requested_at": requested_at,
            "commands": [
                {
                    "request_id": "req_create",
                    "command_kind": "create_workflow",
                    "command_key_digest": hashlib.sha256(b"command-one").hexdigest(),
                    "requested_at": requested_at,
                    "expected_workflow_version": 1,
                    "safe_command": {
                        "campaign_plan_id": "plan-one",
                        "campaign_plan_version": 1,
                    },
                }
            ],
        }

    def _claim(
        self, *, orchestration_id: str = "orch-one", workflow_id: str = "mwf_demo"
    ):
        return self.repository.claim(
            orchestration_id=orchestration_id,
            tenant_id="default",
            brand_id="brand-one",
            actor_ref="act_operator",
            operation="planning_to_approval",
            client_key_digest=self.key_digest,
            workflow_id=workflow_id,
            request_hash=self.request_hash,
            command_plan=self._plan(workflow_id=workflow_id),
            created_at="2026-08-23T10:00:00.000000Z",
        )

    def test_migration_21_and_manifest_are_ready(self) -> None:
        self.assertTrue(self.database.schema_is_ready())
        with self.database.connection() as connection:
            migration = connection.execute(
                "SELECT description FROM schema_migrations WHERE version = 21"
            ).fetchone()
            self.assertEqual(
                migration["description"],
                "Add metadata-first Campaign Asset provenance persistence",
            )

    def test_claim_replay_and_changed_input_conflict(self) -> None:
        first = self._claim()
        replay = self._claim()
        self.assertTrue(first.created)
        self.assertTrue(replay.replay)
        self.assertEqual(
            first.record.command_plan_sha256, replay.record.command_plan_sha256
        )

        changed = self._plan()
        changed["commands"][0]["safe_command"]["campaign_plan_version"] = 2
        with self.assertRaises(OrchestrationConflictError):
            self.repository.claim(
                orchestration_id="orch-two",
                tenant_id="default",
                brand_id="brand-one",
                actor_ref="act_operator",
                operation="planning_to_approval",
                client_key_digest=self.key_digest,
                workflow_id="mwf_demo",
                request_hash=hashlib.sha256(b"request-two").hexdigest(),
                command_plan=changed,
                created_at="2026-08-23T10:00:01.000000Z",
            )

    def test_workflow_reservation_conflict_is_deterministic(self) -> None:
        self._claim()
        other_key = hashlib.sha256(b"client-key-two").hexdigest()
        other_plan = self._plan()
        other_plan["client_key_digest"] = other_key
        other_plan["actor_ref"] = "act_other"
        with self.assertRaises(OrchestrationWorkflowConflictError):
            self.repository.claim(
                orchestration_id="orch-two",
                tenant_id="default",
                brand_id="brand-one",
                actor_ref="act_other",
                operation="planning_to_approval",
                client_key_digest=other_key,
                workflow_id="mwf_demo",
                request_hash=hashlib.sha256(b"request-two").hexdigest(),
                command_plan=other_plan,
                created_at="2026-08-23T10:00:01.000000Z",
            )

    def test_concurrent_first_submissions_have_one_authoritative_claim(self) -> None:
        def submit(index: int):
            try:
                return self._claim(orchestration_id=f"orch-{index}")
            except Exception as error:  # pragma: no cover - asserted below
                return error

        with ThreadPoolExecutor(max_workers=2) as executor:
            results = list(executor.map(submit, (1, 2)))
        self.assertEqual(sum(isinstance(item, Exception) for item in results), 0)
        self.assertEqual(sum(item.created for item in results), 1)
        self.assertEqual(sum(item.replay for item in results), 1)
        with self.database.connection() as connection:
            count = connection.execute(
                "SELECT COUNT(*) AS count FROM workflow_api_orchestrations"
            ).fetchone()["count"]
        self.assertEqual(count, 1)

    def test_progress_is_monotonic_and_optimistic(self) -> None:
        claim = self._claim().record
        advanced = self.repository.advance(
            orchestration_id=claim.orchestration_id,
            expected_version=1,
            progress_state=OrchestrationProgress.WORKFLOW_CREATED,
            updated_at=utc_timestamp(),
        )
        self.assertEqual(advanced.progress_ordinal, 1)
        with self.assertRaises(OrchestrationOptimisticConflictError):
            self.repository.advance(
                orchestration_id=claim.orchestration_id,
                expected_version=1,
                progress_state=OrchestrationProgress.PLANNED,
                updated_at=utc_timestamp(),
            )
        with self.assertRaises(ValueError):
            self.repository.advance(
                orchestration_id=claim.orchestration_id,
                expected_version=2,
                progress_state=OrchestrationProgress.CLAIMED,
                updated_at=utc_timestamp(),
            )
        with self.assertRaises(ValueError):
            self.repository.advance(
                orchestration_id=claim.orchestration_id,
                expected_version=2,
                progress_state=OrchestrationProgress.APPROVED,
                updated_at=utc_timestamp(),
            )

    def test_crash_recovery_preserves_claim_and_approval_transition_gap(self) -> None:
        claim = self._claim().record
        self.assertEqual(claim.progress_state, OrchestrationProgress.CLAIMED)
        created = self.repository.advance(
            orchestration_id=claim.orchestration_id,
            expected_version=1,
            progress_state=OrchestrationProgress.WORKFLOW_CREATED,
            updated_at=utc_timestamp(),
        )
        planned = self.repository.advance(
            orchestration_id=claim.orchestration_id,
            expected_version=created.version,
            progress_state=OrchestrationProgress.PLANNED,
            updated_at=utc_timestamp(),
        )
        awaiting = self.repository.advance(
            orchestration_id=claim.orchestration_id,
            expected_version=planned.version,
            progress_state=OrchestrationProgress.AWAITING_APPROVAL,
            updated_at=utc_timestamp(),
        )
        recorded = self.repository.advance(
            orchestration_id=claim.orchestration_id,
            expected_version=awaiting.version,
            progress_state=OrchestrationProgress.APPROVAL_RECORDED,
            updated_at=utc_timestamp(),
        )
        final = self.repository.advance(
            orchestration_id=claim.orchestration_id,
            expected_version=recorded.version,
            progress_state=OrchestrationProgress.APPROVED,
            updated_at=utc_timestamp(),
            final_response={"state": "approved", "next_action": None},
            final_response_status=200,
            completed_at=utc_timestamp(),
        )
        self.assertEqual(final.progress_state, OrchestrationProgress.APPROVED)
        self.assertIsNotNone(final.final_response_sha256)

    def test_persistence_is_privacy_safe_and_not_cascading(self) -> None:
        claim = self._claim().record
        self.assertNotIn("client-key-one", claim.command_plan_json)
        self.assertNotIn("session", claim.command_plan_json)
        with self.database.connection() as connection:
            foreign_keys = connection.execute(
                "PRAGMA foreign_key_list('workflow_api_orchestrations')"
            ).fetchall()
            self.assertTrue(foreign_keys)
            self.assertTrue(all(row[6] == "NO ACTION" for row in foreign_keys))
            self.assertEqual(
                connection.execute(
                    "SELECT COUNT(*) FROM workflow_api_orchestrations"
                ).fetchone()[0],
                1,
            )

    def test_command_plan_digest_is_canonical(self) -> None:
        claim = self._claim().record
        self.assertEqual(
            claim.command_plan_sha256,
            hashlib.sha256(
                b"earthonox/mlai-033.2/orchestration-plan/v1\n"
                + canonical_json_bytes(self.plan)
            ).hexdigest(),
        )

    def test_operation_claim_replay_conflict_and_immutable_material(self) -> None:
        parent = self._claim().record
        first = self.operation_repository.claim(
            operation_claim_id="operation-one",
            parent_orchestration_id=parent.orchestration_id,
            tenant_id="default",
            brand_id="brand-one",
            actor_ref="act_operator",
            operation="planning_to_approval",
            client_key_digest=self.key_digest,
            workflow_id="mwf_demo",
            request_hash=self.request_hash,
            command_plan=self.plan,
            created_at="2026-08-23T10:00:00.000000Z",
        )
        replay = self.operation_repository.claim(
            operation_claim_id="operation-two",
            parent_orchestration_id=parent.orchestration_id,
            tenant_id="default",
            brand_id="brand-one",
            actor_ref="act_operator",
            operation="planning_to_approval",
            client_key_digest=self.key_digest,
            workflow_id="mwf_demo",
            request_hash=self.request_hash,
            command_plan=self.plan,
            created_at="2026-08-23T10:00:01.000000Z",
        )
        self.assertTrue(first.created)
        self.assertTrue(replay.replay)
        self.assertEqual(
            first.record.command_plan_json, replay.record.command_plan_json
        )
        self.assertEqual(
            first.record.command_plan_sha256, replay.record.command_plan_sha256
        )
        changed = self._plan()
        changed["commands"][0]["safe_command"]["campaign_plan_version"] = 2
        with self.assertRaises(OperationClaimConflictError):
            self.operation_repository.claim(
                operation_claim_id="operation-three",
                parent_orchestration_id=parent.orchestration_id,
                tenant_id="default",
                brand_id="brand-one",
                actor_ref="act_operator",
                operation="planning_to_approval",
                client_key_digest=self.key_digest,
                workflow_id="mwf_demo",
                request_hash=hashlib.sha256(b"changed").hexdigest(),
                command_plan=changed,
                created_at="2026-08-23T10:00:02.000000Z",
            )

    def test_operation_claim_progress_and_final_response_are_optimistic(self) -> None:
        parent = self._claim().record
        claim = self.operation_repository.claim(
            operation_claim_id="operation-one",
            parent_orchestration_id=parent.orchestration_id,
            tenant_id="default",
            brand_id="brand-one",
            actor_ref="act_operator",
            operation="planning_to_approval",
            client_key_digest=self.key_digest,
            workflow_id="mwf_demo",
            request_hash=self.request_hash,
            command_plan=self.plan,
            created_at="2026-08-23T10:00:00.000000Z",
        ).record
        advanced = self.operation_repository.advance(
            operation_claim_id=claim.operation_claim_id,
            expected_version=1,
            progress_state=OrchestrationProgress.WORKFLOW_CREATED,
            updated_at="2026-08-23T10:00:01.000000Z",
        )
        self.assertEqual(advanced.progress_ordinal, 1)
        with self.assertRaises(OrchestrationOptimisticConflictError):
            self.operation_repository.advance(
                operation_claim_id=claim.operation_claim_id,
                expected_version=1,
                progress_state=OrchestrationProgress.PLANNED,
                updated_at="2026-08-23T10:00:02.000000Z",
            )
        final = self.operation_repository.advance(
            operation_claim_id=claim.operation_claim_id,
            expected_version=2,
            progress_state=OrchestrationProgress.CONFLICT_DETECTED,
            updated_at="2026-08-23T10:00:03.000000Z",
            final_response={"status": "conflict_detected"},
            final_response_status=409,
            completed_at="2026-08-23T10:00:03.000000Z",
        )
        self.assertEqual(final.final_response_status, 409)
        self.assertIsNotNone(final.final_response_sha256)

    def test_operation_claim_is_concurrency_safe_and_non_cascading(self) -> None:
        parent = self._claim().record

        def submit(index: int):
            try:
                return self.operation_repository.claim(
                    operation_claim_id=f"operation-{index}",
                    parent_orchestration_id=parent.orchestration_id,
                    tenant_id="default",
                    brand_id="brand-one",
                    actor_ref="act_operator",
                    operation="planning_to_approval",
                    client_key_digest=self.key_digest,
                    workflow_id="mwf_demo",
                    request_hash=self.request_hash,
                    command_plan=self.plan,
                    created_at="2026-08-23T10:00:00.000000Z",
                )
            except Exception as error:  # pragma: no cover - asserted below
                return error

        with ThreadPoolExecutor(max_workers=2) as executor:
            results = list(executor.map(submit, (1, 2)))
        self.assertEqual(sum(isinstance(item, Exception) for item in results), 0)
        self.assertEqual(sum(item.created for item in results), 1)
        self.assertEqual(sum(item.replay for item in results), 1)
        with self.database.connection() as connection:
            self.assertEqual(
                connection.execute(
                    "SELECT COUNT(*) FROM workflow_api_operation_claims"
                ).fetchone()[0],
                1,
            )
            if type(self.database) is SQLiteDatabase:
                foreign_keys = connection.execute(
                    "PRAGMA foreign_key_list('workflow_api_operation_claims')"
                ).fetchall()
                self.assertTrue(foreign_keys)
                self.assertTrue(all(row[6] == "NO ACTION" for row in foreign_keys))
            else:
                foreign_keys = connection.execute("""
                    SELECT rc.delete_rule, rc.update_rule
                    FROM information_schema.table_constraints AS tc
                    JOIN information_schema.referential_constraints AS rc
                      ON tc.constraint_schema = rc.constraint_schema
                     AND tc.constraint_name = rc.constraint_name
                    WHERE tc.table_schema = current_schema()
                      AND tc.table_name = 'workflow_api_operation_claims'
                      AND tc.constraint_type = 'FOREIGN KEY'
                    """).fetchall()
                self.assertTrue(foreign_keys)
                self.assertTrue(
                    all(
                        row[0] == "NO ACTION" and row[1] == "NO ACTION"
                        for row in foreign_keys
                    )
                )


if __name__ == "__main__":
    unittest.main()
