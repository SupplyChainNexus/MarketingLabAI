"""Metadata-first persistence for Campaign Assets and generation provenance."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any, Mapping

from app.database.connection import SQLiteDatabase

_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_ASSET_STATES = frozenset(
    {
        "requested",
        "grounded",
        "generated",
        "reviewable",
        "approved",
        "validation_failed",
        "rejected",
        "superseded",
    }
)
_ATTEMPT_STATES = frozenset(
    {"requested", "grounded", "generated", "reviewable", "validation_failed", "failed"}
)
_OUTCOMES = frozenset({"approved", "review_required", "blocked"})
_SOURCE_REFERENCE_KEYS = frozenset(
    {
        "source_id",
        "source_type",
        "version",
        "digest",
        "lifecycle_state",
        "privacy_classification",
    }
)
_SOURCE_REQUIRED_KEYS = frozenset(
    {"source_id", "version", "digest", "lifecycle_state", "privacy_classification"}
)
_FINDING_KEYS = frozenset({"code", "category", "severity", "field", "claim_id"})
_EVIDENCE_STATES = frozenset({"approved", "revoked", "superseded", "expired"})


def _text(name: str, value: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} is required")
    return value.strip()


def _version(name: str, value: int) -> int:
    if type(value) is not int or value < 1:
        raise ValueError(f"{name} must be a positive integer")
    return value


def _digest(name: str, value: str) -> str:
    selected = _text(name, value)
    if not _SHA256.fullmatch(selected):
        raise ValueError(f"{name} must be lowercase SHA-256 hexadecimal")
    return selected


def _json(name: str, value: Mapping[str, Any] | list[Any]) -> str:
    if not isinstance(value, (Mapping, list)):
        raise TypeError(f"{name} must be a JSON object or array")
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _metadata_text(name: str, value: Any, *, maximum: int = 256) -> str:
    if not isinstance(value, str) or not value or len(value) > maximum:
        raise ValueError(f"{name} must be a bounded metadata string")
    if any(ord(character) < 32 or character.isspace() for character in value):
        raise ValueError(f"{name} contains control content")
    return value


def _source_references(value: tuple[Mapping[str, Any], ...]) -> list[dict[str, Any]]:
    normalized: list[dict[str, Any]] = []
    for index, reference in enumerate(value):
        if not isinstance(reference, Mapping):
            raise TypeError(f"source_references[{index}] must be an object")
        keys = set(reference)
        if not keys.issubset(_SOURCE_REFERENCE_KEYS):
            raise ValueError("source_references contains unsupported metadata")
        if not _SOURCE_REQUIRED_KEYS.issubset(keys):
            raise ValueError("source_references is missing required metadata")
        item = {
            "source_id": _metadata_text("source_id", reference["source_id"]),
            "version": _version("source version", reference["version"]),
            "digest": _digest("source digest", reference["digest"]),
            "lifecycle_state": _metadata_text(
                "source lifecycle state", reference["lifecycle_state"], maximum=32
            ),
            "privacy_classification": _metadata_text(
                "source privacy classification",
                reference["privacy_classification"],
                maximum=64,
            ),
        }
        if item["lifecycle_state"] not in _EVIDENCE_STATES:
            raise ValueError("source lifecycle state is unsupported")
        if "source_type" in reference:
            item["source_type"] = _metadata_text(
                "source type", reference["source_type"], maximum=64
            )
        normalized.append(item)
    return normalized


def _safe_findings(value: tuple[Mapping[str, Any], ...]) -> list[dict[str, str]]:
    normalized: list[dict[str, str]] = []
    for index, finding in enumerate(value):
        if not isinstance(finding, Mapping):
            raise TypeError(f"safe_findings[{index}] must be an object")
        keys = set(finding)
        if not keys.issubset(_FINDING_KEYS) or "code" not in keys:
            raise ValueError("safe_findings contains unsupported metadata")
        normalized.append(
            {key: _metadata_text(key, finding[key]) for key in sorted(keys)}
        )
    return normalized


@dataclass(frozen=True, slots=True)
class AssetRevisionRecord:
    tenant_id: str
    brand_id: str
    asset_id: str
    revision: int
    generation_identity: str
    request_id: str
    snapshot_digest: str
    snapshot_schema_version: int
    snapshot_canonicalization_version: str
    source_references: tuple[Mapping[str, Any], ...]
    output_digest: str
    output_reference: str
    validation_outcome: str
    policy_pack_name: str
    policy_pack_version: int
    policy_pack_digest: str
    safe_findings: tuple[Mapping[str, Any], ...]
    provider_name: str | None = None
    model_name: str | None = None
    model_version: str | None = None
    workflow_id: str | None = None
    workflow_version: int | None = None
    approval_id: str | None = None
    rejection_receipt_id: str | None = None
    parent_revision: int | None = None
    created_at: str = ""

    def __post_init__(self) -> None:
        for name in (
            "tenant_id",
            "brand_id",
            "asset_id",
            "generation_identity",
            "request_id",
        ):
            object.__setattr__(self, name, _text(name, getattr(self, name)))
        object.__setattr__(self, "revision", _version("revision", self.revision))
        object.__setattr__(
            self, "snapshot_digest", _digest("snapshot_digest", self.snapshot_digest)
        )
        object.__setattr__(
            self, "output_digest", _digest("output_digest", self.output_digest)
        )
        object.__setattr__(
            self,
            "policy_pack_digest",
            _digest("policy_pack_digest", self.policy_pack_digest),
        )
        object.__setattr__(
            self,
            "snapshot_schema_version",
            _version("snapshot_schema_version", self.snapshot_schema_version),
        )
        object.__setattr__(
            self,
            "policy_pack_version",
            _version("policy_pack_version", self.policy_pack_version),
        )
        object.__setattr__(
            self,
            "snapshot_canonicalization_version",
            _text(
                "snapshot_canonicalization_version",
                self.snapshot_canonicalization_version,
            ),
        )
        object.__setattr__(
            self, "output_reference", _text("output_reference", self.output_reference)
        )
        object.__setattr__(
            self, "policy_pack_name", _text("policy_pack_name", self.policy_pack_name)
        )
        if self.validation_outcome not in _OUTCOMES:
            raise ValueError("validation_outcome is unsupported")
        if self.workflow_version is not None:
            object.__setattr__(
                self,
                "workflow_version",
                _version("workflow_version", self.workflow_version),
            )
        if self.parent_revision is not None:
            object.__setattr__(
                self,
                "parent_revision",
                _version("parent_revision", self.parent_revision),
            )
        object.__setattr__(
            self,
            "source_references",
            tuple(_source_references(tuple(self.source_references))),
        )
        object.__setattr__(
            self, "safe_findings", tuple(_safe_findings(tuple(self.safe_findings)))
        )
        object.__setattr__(self, "created_at", _text("created_at", self.created_at))


@dataclass(frozen=True, slots=True)
class GenerationAttemptRecord:
    attempt_id: str
    tenant_id: str
    brand_id: str
    asset_id: str
    revision: int
    operation_claim_id: str
    generation_identity: str
    request_id: str
    attempt_state: str
    snapshot_digest: str
    created_at: str
    updated_at: str
    output_digest: str | None = None
    validation_outcome: str | None = None
    policy_pack_name: str | None = None
    policy_pack_version: int | None = None
    policy_pack_digest: str | None = None
    provider_name: str | None = None
    model_name: str | None = None
    model_version: str | None = None
    failure_class: str | None = None

    def __post_init__(self) -> None:
        for name in (
            "attempt_id",
            "tenant_id",
            "brand_id",
            "asset_id",
            "operation_claim_id",
            "generation_identity",
            "request_id",
        ):
            object.__setattr__(self, name, _text(name, getattr(self, name)))
        object.__setattr__(self, "revision", _version("revision", self.revision))
        if self.attempt_state not in _ATTEMPT_STATES:
            raise ValueError("attempt_state is unsupported")
        object.__setattr__(
            self, "snapshot_digest", _digest("snapshot_digest", self.snapshot_digest)
        )
        if self.output_digest is not None:
            object.__setattr__(
                self, "output_digest", _digest("output_digest", self.output_digest)
            )
        if (
            self.validation_outcome is not None
            and self.validation_outcome not in _OUTCOMES
        ):
            raise ValueError("validation_outcome is unsupported")
        if self.policy_pack_version is not None:
            object.__setattr__(
                self,
                "policy_pack_version",
                _version("policy_pack_version", self.policy_pack_version),
            )
        if self.policy_pack_digest is not None:
            object.__setattr__(
                self,
                "policy_pack_digest",
                _digest("policy_pack_digest", self.policy_pack_digest),
            )
        object.__setattr__(self, "created_at", _text("created_at", self.created_at))
        object.__setattr__(self, "updated_at", _text("updated_at", self.updated_at))


class CampaignAssetRepository:
    """Persist Campaign Asset metadata without becoming a second lifecycle owner."""

    def __init__(self, database: SQLiteDatabase) -> None:
        self.database = database

    def create_asset(
        self,
        *,
        tenant_id: str,
        brand_id: str,
        asset_id: str,
        campaign_id: str,
        lifecycle_state: str = "requested",
        version: int = 1,
        created_at: str,
    ) -> None:
        if lifecycle_state not in _ASSET_STATES:
            raise ValueError("lifecycle_state is unsupported")
        values = (
            _text("tenant_id", tenant_id),
            _text("brand_id", brand_id),
            _text("asset_id", asset_id),
            _text("campaign_id", campaign_id),
            lifecycle_state,
            _version("version", version),
            _text("created_at", created_at),
        )
        with self.database.transaction() as connection:
            connection.execute(
                """
                INSERT INTO campaign_assets (
                    tenant_id, brand_id, asset_id, campaign_id,
                    lifecycle_state, version, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    values[0],
                    values[1],
                    values[2],
                    values[3],
                    values[4],
                    values[5],
                    values[6],
                    values[6],
                ),
            )

    def save_revision(self, revision: AssetRevisionRecord) -> None:
        source_json = _json(
            "source_references", _source_references(revision.source_references)
        )
        findings_json = _json("safe_findings", _safe_findings(revision.safe_findings))
        with self.database.transaction() as connection:
            connection.execute(
                """
                INSERT INTO campaign_asset_revisions (
                    tenant_id, brand_id, asset_id, revision, generation_identity,
                    request_id, snapshot_digest, snapshot_schema_version,
                    snapshot_canonicalization_version, source_references_json,
                    output_digest, output_reference, validation_outcome,
                    policy_pack_name, policy_pack_version, policy_pack_digest,
                    safe_findings_json, provider_name, model_name, model_version,
                    workflow_id, workflow_version, approval_id,
                    rejection_receipt_id, parent_revision, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
                          ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    revision.tenant_id,
                    revision.brand_id,
                    revision.asset_id,
                    revision.revision,
                    revision.generation_identity,
                    revision.request_id,
                    revision.snapshot_digest,
                    revision.snapshot_schema_version,
                    revision.snapshot_canonicalization_version,
                    source_json,
                    revision.output_digest,
                    revision.output_reference,
                    revision.validation_outcome,
                    revision.policy_pack_name,
                    revision.policy_pack_version,
                    revision.policy_pack_digest,
                    findings_json,
                    revision.provider_name,
                    revision.model_name,
                    revision.model_version,
                    revision.workflow_id,
                    revision.workflow_version,
                    revision.approval_id,
                    revision.rejection_receipt_id,
                    revision.parent_revision,
                    revision.created_at,
                ),
            )

    def save_attempt(self, attempt: GenerationAttemptRecord) -> None:
        with self.database.transaction() as connection:
            connection.execute(
                """
                INSERT INTO generation_attempts (
                    attempt_id, tenant_id, brand_id, asset_id, revision,
                    operation_claim_id, generation_identity, request_id,
                    attempt_state, snapshot_digest, output_digest,
                    validation_outcome, policy_pack_name, policy_pack_version,
                    policy_pack_digest, provider_name, model_name, model_version,
                    failure_class, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
                          ?, ?, ?)
                """,
                (
                    attempt.attempt_id,
                    attempt.tenant_id,
                    attempt.brand_id,
                    attempt.asset_id,
                    attempt.revision,
                    attempt.operation_claim_id,
                    attempt.generation_identity,
                    attempt.request_id,
                    attempt.attempt_state,
                    attempt.snapshot_digest,
                    attempt.output_digest,
                    attempt.validation_outcome,
                    attempt.policy_pack_name,
                    attempt.policy_pack_version,
                    attempt.policy_pack_digest,
                    attempt.provider_name,
                    attempt.model_name,
                    attempt.model_version,
                    attempt.failure_class,
                    attempt.created_at,
                    attempt.updated_at,
                ),
            )
