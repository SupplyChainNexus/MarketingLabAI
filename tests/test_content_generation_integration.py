"""Focused C5 Campaign Asset generation/review integration tests."""

from __future__ import annotations

import tempfile
import unittest
from dataclasses import replace
from pathlib import Path

from app.application import CanonicalApplication
from app.content_generation import (
    ClaimConfidence,
    ClaimKind,
    ClaimRisk,
    GeneratedOutput,
    GenerationBoundaryError,
    GenerationRequest,
    GroundedClaim,
    GroundingAnchor,
    PolicyPack,
    SourceLifecycle,
    SourceReference,
    build_grounding_snapshot,
)
from app.content_generation.integration import GovernedGenerationService
from app.database.connection import SQLiteDatabase
from app.marketing_workflow.canonical import canonical_json

NOW = "2026-08-26T10:00:00.000000Z"


class MemoryOutputStore:
    def __init__(self) -> None:
        self.values: dict[str, str] = {}

    def save(self, content: str, **identity: object) -> str:
        reference = (
            f"asset-output://{identity['asset_id']}/revision-{identity['revision']}"
        )
        if reference in self.values:
            raise RuntimeError("immutable output already exists")
        self.values[reference] = content
        return reference

    def load(self, reference: str) -> str | None:
        return self.values.get(reference)


class CountingGenerator:
    def __init__(self) -> None:
        self.calls = 0

    def __call__(self, _snapshot) -> GeneratedOutput:
        self.calls += 1
        return GeneratedOutput(
            "Subject: Operational growth review for Operations leaders. "
            "Improve qualified enquiries.",
            provider_name="provider-neutral-test",
            model_name="model-test",
            model_version="1",
        )


class ContentGenerationIntegrationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        database = SQLiteDatabase(Path(self.temp.name) / "c5.db")
        self.application = CanonicalApplication.build(database)
        self._seed_scope()
        self.store = MemoryOutputStore()
        self.generator = CountingGenerator()
        self.service = self.application.build_governed_generation_service(
            output_store=self.store, generator=self.generator
        )
        self.policy = PolicyPack.v1(effective_date="2026-08-26")
        self.sources = self._sources()

    def tearDown(self) -> None:
        self.temp.cleanup()

    def _seed_scope(self) -> None:
        with self.application.database.transaction() as connection:
            connection.execute(
                "INSERT INTO brands (brand_id, tenant_id, name, payload_json, "
                "created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?)",
                ("brand-a", "default", "Brand A", "{}", NOW, NOW),
            )
            connection.execute(
                """
                INSERT INTO marketing_workflows (
                    workflow_id, tenant_id, brand_id, campaign_plan_id,
                    campaign_plan_version, state, version, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    "workflow-1",
                    "default",
                    "brand-a",
                    "campaign-1",
                    1,
                    "draft",
                    1,
                    NOW,
                    NOW,
                ),
            )
            connection.execute(
                """
                INSERT INTO workflow_api_orchestrations (
                    orchestration_id, tenant_id, brand_id, actor_ref, operation,
                    client_key_digest, workflow_id, request_hash,
                    command_plan_json, command_plan_sha256, progress_state,
                    progress_ordinal, version, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    "orch-1",
                    "default",
                    "brand-a",
                    "act_operator",
                    "generation",
                    "a" * 64,
                    "workflow-1",
                    "b" * 64,
                    "{}",
                    "c" * 64,
                    "claimed",
                    0,
                    1,
                    NOW,
                    NOW,
                ),
            )
            for ordinal in (1, 2):
                connection.execute(
                    """
                    INSERT INTO workflow_api_operation_claims (
                        operation_claim_id, parent_orchestration_id, tenant_id,
                        brand_id, actor_ref, operation, client_key_digest,
                        workflow_id, request_hash, command_plan_json,
                        command_plan_sha256, progress_state, progress_ordinal,
                        version, created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        f"claim-{ordinal}",
                        "orch-1",
                        "default",
                        "brand-a",
                        "act_operator",
                        f"generation-{ordinal}",
                        str(ordinal) * 64,
                        "workflow-1",
                        "d" * 64,
                        "{}",
                        "e" * 64,
                        "claimed",
                        0,
                        1,
                        NOW,
                        NOW,
                    ),
                )

    @staticmethod
    def _sources() -> tuple[SourceReference, ...]:
        return tuple(
            SourceReference(
                source_type=source_type,
                source_id=f"{source_type}-1",
                tenant_id="default",
                brand_id="brand-a",
                version=1,
                digest=character * 64,
                lifecycle=SourceLifecycle.APPROVED,
                privacy_classification="internal",
            )
            for source_type, character in (
                ("campaign_plan", "a"),
                ("product", "b"),
                ("positioning", "c"),
            )
        )

    def _request(
        self,
        *,
        revision: int = 1,
        request_id: str = "request-1",
        generation_identity: str = "generation-1",
        claim_id: str = "claim-1",
        parent_revision: int | None = None,
    ) -> GenerationRequest:
        snapshot = build_grounding_snapshot(
            generation_identity=generation_identity,
            tenant_id="default",
            brand_id="brand-a",
            captured_at=NOW,
            selected_fields={
                "objective": "Increase qualified enquiries",
                "audience": "Operations leaders",
                "channels": ["email"],
                "content_type": "campaign_email",
                "offer": "Operational growth review",
            },
            source_refs=self.sources,
        )
        anchors = tuple(
            GroundingAnchor(text=text, source=source)
            for text, source in zip(
                (
                    "Operations leaders",
                    "Operational growth review",
                    "qualified enquiries",
                ),
                self.sources,
            )
        )
        claims = (
            GroundedClaim(
                claim_id="claim-content-1",
                text="Improve qualified enquiries",
                kind=ClaimKind.DIRECT,
                confidence=ClaimConfidence.SUPPORTED,
                risk=ClaimRisk.NORMAL,
                evidence=self.sources,
            ),
        )
        return GenerationRequest(
            tenant_id="default",
            brand_id="brand-a",
            campaign_id="campaign-1",
            asset_id="asset-1",
            revision=revision,
            request_id=request_id,
            generation_identity=generation_identity,
            operation_claim_id=claim_id,
            workflow_id="workflow-1",
            workflow_version=1,
            snapshot_bytes=snapshot.canonical_bytes,
            snapshot_digest=snapshot.digest,
            channel="email",
            content_type="campaign_email",
            anchors=anchors,
            claims=claims,
            policy=self.policy,
            created_at=NOW,
            attempt_id=f"attempt-{revision}",
            parent_revision=parent_revision,
        )

    def test_generation_persists_reviewable_metadata_and_exact_replay(self) -> None:
        request = self._request()
        first = self.service.generate(request)
        replay = self.service.generate(request)
        self.assertFalse(first.replay)
        self.assertTrue(replay.replay)
        self.assertEqual(first.content, replay.content)
        self.assertEqual(self.generator.calls, 1)
        self.assertEqual(first.revision.validation_outcome, "approved")
        self.assertEqual(first.revision.snapshot_digest, request.snapshot_digest)
        with self.application.database.observation_connection() as connection:
            source_json = connection.execute(
                "SELECT source_references_json FROM campaign_asset_revisions"
            ).fetchone()["source_references_json"]
        self.assertNotIn("selected_fields", source_json)
        self.assertNotIn("Operational growth review", source_json)

    def test_regeneration_requires_new_identity_and_creates_successor(self) -> None:
        self.service.generate(self._request())
        second = self.service.generate(
            self._request(
                revision=2,
                request_id="request-2",
                generation_identity="generation-2",
                claim_id="claim-2",
                parent_revision=1,
            )
        )
        self.assertEqual(second.revision.parent_revision, 1)
        self.assertEqual(second.revision.revision, 2)
        self.assertEqual(self.generator.calls, 2)
        with self.assertRaises(GenerationBoundaryError):
            self.service.generate(replace(self._request(), snapshot_digest="f" * 64))
        self.assertEqual(self.generator.calls, 2)

    def test_cross_scope_and_digest_invalid_state_fail_without_invocation(self) -> None:
        request = self._request()
        with self.assertRaises(GenerationBoundaryError):
            self.service.generate(replace(request, brand_id="other-brand"))
        self.assertEqual(self.generator.calls, 0)
        self.service.generate(request)
        self.store.values["asset-output://asset-1/revision-1"] = "tampered"
        with self.assertRaises(GenerationBoundaryError):
            self.service.generate(request)
        self.assertEqual(self.generator.calls, 1)

    def test_approval_revalidates_policy_output_sources_and_workflow_authority(
        self,
    ) -> None:
        self.service.generate(self._request())
        with self.assertRaises(GenerationBoundaryError):
            self.service.approve(
                tenant_id="default",
                brand_id="brand-a",
                asset_id="asset-1",
                revision=1,
                policy=self.policy,
                current_sources=self.sources,
                updated_at=NOW,
            )
        with self.application.database.transaction() as connection:
            connection.execute(
                """
                INSERT INTO workflow_approvals (
                    approval_id, tenant_id, brand_id, workflow_id,
                    workflow_version, action, decision,
                    requested_by_actor_ref, decided_by_actor_ref, decided_at,
                    canonical_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    "approval-1",
                    "default",
                    "brand-a",
                    "workflow-1",
                    1,
                    GovernedGenerationService.APPROVAL_ACTION,
                    "approved",
                    "act_requester",
                    "act_approver",
                    NOW,
                    canonical_json({"approval_id": "approval-1"}),
                ),
            )
        stale = replace(self.sources[0], lifecycle=SourceLifecycle.REVOKED)
        with self.assertRaises(GenerationBoundaryError):
            self.service.approve(
                tenant_id="default",
                brand_id="brand-a",
                asset_id="asset-1",
                revision=1,
                policy=self.policy,
                current_sources=(stale, *self.sources[1:]),
                updated_at=NOW,
            )
        self.service.approve(
            tenant_id="default",
            brand_id="brand-a",
            asset_id="asset-1",
            revision=1,
            policy=self.policy,
            current_sources=self.sources,
            updated_at=NOW,
        )
        self.assertEqual(
            self.application.campaign_assets.asset_state(
                tenant_id="default", brand_id="brand-a", asset_id="asset-1"
            )[0],
            "approved",
        )


if __name__ == "__main__":
    unittest.main()
