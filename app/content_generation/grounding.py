"""Construction and fail-closed validation for canonical grounding snapshots."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Sequence
from typing import Any

from app.marketing_workflow.canonical import canonical_json_bytes

from .models import (
    GROUNDING_CANONICALIZATION_VERSION,
    GROUNDING_DOMAIN,
    GROUNDING_SCHEMA_VERSION,
    MAX_GROUNDING_SNAPSHOT_BYTES,
    GroundingSnapshot,
    SourceLifecycle,
    SourceReference,
)


class GroundingError(ValueError):
    """Safe machine-readable grounding failure."""

    def __init__(self, code: str, message: str = "Grounding validation failed") -> None:
        self.code = code
        self.safe_message = message
        super().__init__(message)


class GroundingValidator:
    """Validate immutable material without revealing inaccessible resources."""

    def validate(
        self,
        snapshot: GroundingSnapshot,
        *,
        tenant_id: str,
        brand_id: str,
    ) -> GroundingSnapshot:
        if not isinstance(snapshot, GroundingSnapshot):
            raise GroundingError("malformed_material")
        if snapshot.tenant_id != tenant_id or snapshot.brand_id != brand_id:
            raise GroundingError("resource_unavailable")
        self._validate_sources(
            snapshot.source_refs, tenant_id=tenant_id, brand_id=brand_id
        )
        self._validate_digest(snapshot)
        return snapshot

    def load(
        self,
        material: bytes,
        *,
        expected_digest: str,
        tenant_id: str,
        brand_id: str,
    ) -> GroundingSnapshot:
        if not isinstance(material, bytes):
            raise GroundingError("malformed_material")
        if len(material) > MAX_GROUNDING_SNAPSHOT_BYTES:
            raise GroundingError("snapshot_oversized")
        if not isinstance(expected_digest, str) or len(expected_digest) != 64:
            raise GroundingError("digest_invalid")
        try:
            payload = json.loads(material.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            raise GroundingError("malformed_material") from None
        if not isinstance(payload, dict):
            raise GroundingError("malformed_material")
        if payload.get("schema_version") != GROUNDING_SCHEMA_VERSION:
            raise GroundingError("unsupported_schema_version")
        if (
            payload.get("canonicalization_version")
            != GROUNDING_CANONICALIZATION_VERSION
        ):
            raise GroundingError("unsupported_schema_version")
        if payload.get("record_kind") != "grounding_snapshot":
            raise GroundingError("malformed_material")
        try:
            source_refs = tuple(
                SourceReference(**item) for item in payload["source_refs"]
            )
            snapshot = GroundingSnapshot.create(
                generation_identity=payload["generation_identity"],
                tenant_id=payload["tenant_id"],
                brand_id=payload["brand_id"],
                captured_at=payload["captured_at"],
                selected_fields=payload["selected_fields"],
                source_refs=source_refs,
                schema_version=payload["schema_version"],
            )
        except GroundingError:
            raise
        except (KeyError, TypeError, ValueError):
            raise GroundingError("malformed_material") from None
        if snapshot.canonical_bytes != material:
            raise GroundingError("digest_invalid")
        if snapshot.digest != expected_digest:
            raise GroundingError("digest_invalid")
        return self.validate(snapshot, tenant_id=tenant_id, brand_id=brand_id)

    @staticmethod
    def _validate_sources(
        source_refs: Sequence[SourceReference],
        *,
        tenant_id: str,
        brand_id: str,
    ) -> None:
        identities: set[tuple[str, str, int]] = set()
        for reference in source_refs:
            if reference.tenant_id != tenant_id or reference.brand_id != brand_id:
                raise GroundingError("resource_unavailable")
            identity = (reference.source_type, reference.source_id, reference.version)
            if identity in identities:
                raise GroundingError("resource_unavailable")
            identities.add(identity)
            if reference.lifecycle is not SourceLifecycle.APPROVED:
                raise GroundingError("resource_unavailable")
        if not any(
            reference.source_type == "campaign_plan" for reference in source_refs
        ):
            raise GroundingError("resource_unavailable")

    @staticmethod
    def _validate_digest(snapshot: GroundingSnapshot) -> None:
        expected = hashlib.sha256(
            GROUNDING_DOMAIN.encode("ascii")
            + b"\n"
            + canonical_json_bytes(snapshot._envelope())
        ).hexdigest()
        if expected != snapshot.digest:
            raise GroundingError("digest_invalid")


def build_grounding_snapshot(**kwargs: Any) -> GroundingSnapshot:
    """Build and validate one immutable snapshot without external calls."""

    try:
        snapshot = GroundingSnapshot.create(**kwargs)
        return GroundingValidator().validate(
            snapshot,
            tenant_id=kwargs["tenant_id"],
            brand_id=kwargs["brand_id"],
        )
    except GroundingError:
        raise
    except (TypeError, ValueError) as error:
        message = str(error)
        if "schema version" in message:
            code = "unsupported_schema_version"
        elif "size" in message:
            code = "snapshot_oversized"
        elif "instruction" in message:
            code = "untrusted_source_instructions"
        else:
            code = "invalid_snapshot"
        raise GroundingError(code) from error


def load_grounding_snapshot(
    material: bytes,
    *,
    expected_digest: str,
    tenant_id: str,
    brand_id: str,
) -> GroundingSnapshot:
    return GroundingValidator().load(
        material,
        expected_digest=expected_digest,
        tenant_id=tenant_id,
        brand_id=brand_id,
    )
