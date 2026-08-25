"""Focused tests for Migration 21 metadata-first asset persistence."""

from __future__ import annotations

import hashlib
import json
import sqlite3
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path

from app.campaign_planner.asset_repository import (
    AssetRevisionRecord,
    CampaignAssetRepository,
    GenerationAttemptRecord,
)
from app.database.connection import SQLiteDatabase


class CampaignAssetPersistenceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.database = SQLiteDatabase(Path(self.tempdir.name) / "assets.db")
        self.database.initialise()
        self.repository = CampaignAssetRepository(self.database)
        self._seed_scope()

    def tearDown(self) -> None:
        self.tempdir.cleanup()

    def _seed_scope(self) -> None:
        with self.database.transaction() as connection:
            connection.execute(
                """
                INSERT INTO brands (
                    brand_id, tenant_id, name, payload_json,
                    created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                ("brand-a", "default", "Brand A", "{}", "2026-01-01", "2026-01-01"),
            )
            connection.execute(
                """
                INSERT INTO marketing_workflows (
                    workflow_id, tenant_id, brand_id, campaign_plan_id,
                    campaign_plan_version, state, version, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    "mwf_asset",
                    "default",
                    "brand-a",
                    "campaign-1",
                    1,
                    "draft",
                    1,
                    "2026-01-01",
                    "2026-01-01",
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
                    "orch_asset",
                    "default",
                    "brand-a",
                    "act_operator",
                    "planning_to_approval",
                    "a" * 64,
                    "mwf_asset",
                    "b" * 64,
                    "{}",
                    "c" * 64,
                    "claimed",
                    0,
                    1,
                    "2026-01-01",
                    "2026-01-01",
                ),
            )
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
                    "claim_asset",
                    "orch_asset",
                    "default",
                    "brand-a",
                    "act_operator",
                    "planning_to_approval",
                    "d" * 64,
                    "mwf_asset",
                    "e" * 64,
                    "{}",
                    "f" * 64,
                    "claimed",
                    0,
                    1,
                    "2026-01-01",
                    "2026-01-01",
                ),
            )

    @staticmethod
    def _digest(value: str) -> str:
        return hashlib.sha256(value.encode("utf-8")).hexdigest()

    def _revision(
        self, revision: int = 1, generation: str = "gen-1"
    ) -> AssetRevisionRecord:
        return AssetRevisionRecord(
            tenant_id="default",
            brand_id="brand-a",
            asset_id="asset-1",
            revision=revision,
            generation_identity=generation,
            request_id=f"req-{revision}",
            snapshot_digest=self._digest("snapshot"),
            snapshot_schema_version=1,
            snapshot_canonicalization_version="MLAI-CJ-1",
            source_references=(
                {
                    "source_id": "product-1",
                    "source_type": "product",
                    "version": 2,
                    "digest": self._digest("product"),
                    "lifecycle_state": "approved",
                    "privacy_classification": "internal",
                },
            ),
            output_digest=self._digest("output"),
            output_reference="asset-output://asset-1/revision-1",
            validation_outcome="review_required",
            policy_pack_name="c5-phase-b",
            policy_pack_version=1,
            policy_pack_digest=self._digest("policy"),
            safe_findings=({"code": "review_required"},),
            workflow_id="mwf_asset",
            workflow_version=1,
            created_at="2026-01-01T00:00:00.000000Z",
        )

    def test_asset_revision_and_generation_attempt_are_tenant_bound(self) -> None:
        self.repository.create_asset(
            tenant_id="default",
            brand_id="brand-a",
            asset_id="asset-1",
            campaign_id="campaign-1",
            created_at="2026-01-01",
        )
        self.repository.save_revision(self._revision())
        self.repository.save_attempt(
            GenerationAttemptRecord(
                attempt_id="attempt-1",
                tenant_id="default",
                brand_id="brand-a",
                asset_id="asset-1",
                revision=1,
                operation_claim_id="claim_asset",
                generation_identity="gen-1",
                request_id="req-1",
                attempt_state="reviewable",
                snapshot_digest=self._digest("snapshot"),
                created_at="2026-01-01",
                updated_at="2026-01-01",
                validation_outcome="review_required",
            )
        )
        with self.database.observation_connection() as connection:
            revision = connection.execute(
                "SELECT source_references_json, output_reference FROM campaign_asset_revisions"
            ).fetchone()
            attempt = connection.execute(
                "SELECT operation_claim_id, generation_identity FROM generation_attempts"
            ).fetchone()
        self.assertEqual(
            json.loads(revision["source_references_json"])[0]["source_id"], "product-1"
        )
        self.assertNotIn("raw", revision["source_references_json"])
        self.assertEqual(attempt["operation_claim_id"], "claim_asset")

    def test_generation_identity_and_claim_are_unique(self) -> None:
        self.repository.create_asset(
            tenant_id="default",
            brand_id="brand-a",
            asset_id="asset-1",
            campaign_id="campaign-1",
            created_at="2026-01-01",
        )
        self.repository.save_revision(self._revision())
        with self.assertRaises(sqlite3.IntegrityError):
            self.repository.save_revision(
                self._revision(revision=2, generation="gen-1")
            )

    def test_revision_lineage_is_immutable_and_no_cascade_deletion(self) -> None:
        self.repository.create_asset(
            tenant_id="default",
            brand_id="brand-a",
            asset_id="asset-1",
            campaign_id="campaign-1",
            created_at="2026-01-01",
        )
        self.repository.save_revision(self._revision())
        child = replace(
            self._revision(revision=2, generation="gen-2"), parent_revision=1
        )
        self.repository.save_revision(child)
        with self.database.transaction() as connection:
            with self.assertRaises(sqlite3.IntegrityError):
                connection.execute(
                    "DELETE FROM campaign_assets WHERE tenant_id = ? AND brand_id = ? AND asset_id = ?",
                    ("default", "brand-a", "asset-1"),
                )

    def test_revision_lineage_cannot_point_forward(self) -> None:
        self.repository.create_asset(
            tenant_id="default",
            brand_id="brand-a",
            asset_id="asset-1",
            campaign_id="campaign-1",
            created_at="2026-01-01",
        )
        with self.assertRaises(sqlite3.IntegrityError):
            self.repository.save_revision(replace(self._revision(), parent_revision=2))

    def test_invalid_metadata_is_rejected_before_persistence(self) -> None:
        with self.assertRaises(ValueError):
            AssetRevisionRecord(
                tenant_id="default",
                brand_id="brand-a",
                asset_id="asset-1",
                revision=1,
                generation_identity="gen",
                request_id="req",
                snapshot_digest="z" * 64,
                snapshot_schema_version=1,
                snapshot_canonicalization_version="MLAI-CJ-1",
                source_references=(),
                output_digest="a" * 64,
                output_reference="ref",
                validation_outcome="approved",
                policy_pack_name="pack",
                policy_pack_version=1,
                policy_pack_digest="b" * 64,
                safe_findings=(),
                created_at="2026-01-01",
            )

    def test_raw_and_unknown_source_metadata_are_rejected(self) -> None:
        for reference in (
            {
                "source_id": "x",
                "version": 1,
                "digest": "a" * 64,
                "lifecycle_state": "approved",
                "privacy_classification": "internal",
                "prompt": "raw instruction",
            },
            {
                "source_id": "x",
                "version": 1,
                "digest": "a" * 64,
                "lifecycle_state": "approved",
                "privacy_classification": "internal",
                "customer_content": "unnecessary content",
            },
        ):
            with self.assertRaises(ValueError):
                replace(self._revision(), source_references=(reference,))
        with self.assertRaises(ValueError):
            replace(
                self._revision(),
                safe_findings=({"code": "x", "raw_content": "secret"},),
            )

    def test_direct_revision_update_and_delete_are_rejected(self) -> None:
        self.repository.create_asset(
            tenant_id="default",
            brand_id="brand-a",
            asset_id="asset-1",
            campaign_id="campaign-1",
            created_at="2026-01-01",
        )
        self.repository.save_revision(self._revision())
        with self.database.transaction() as connection:
            with self.assertRaises(sqlite3.IntegrityError):
                connection.execute(
                    "UPDATE campaign_asset_revisions SET output_reference = ?",
                    ("changed",),
                )
        with self.database.transaction() as connection:
            with self.assertRaises(sqlite3.IntegrityError):
                connection.execute("DELETE FROM campaign_asset_revisions")
        with self.database.observation_connection() as connection:
            row = connection.execute(
                "SELECT output_reference FROM campaign_asset_revisions"
            ).fetchone()
        self.assertEqual(row["output_reference"], "asset-output://asset-1/revision-1")


if __name__ == "__main__":
    unittest.main()
