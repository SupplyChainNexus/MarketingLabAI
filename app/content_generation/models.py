"""Immutable, provider-neutral models for grounding provenance."""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from enum import StrEnum
from typing import Any, Mapping

from app.marketing_workflow.canonical import (
    assert_privacy_safe,
    canonical_json_bytes,
    validate_timestamp,
)

GROUNDING_SCHEMA_VERSION = 1
GROUNDING_CANONICALIZATION_VERSION = "MLAI-GS-1"
GROUNDING_DOMAIN = "earthonox/mlai-033.3/grounding-snapshot/MLAI-GS-1"
MAX_GROUNDING_SNAPSHOT_BYTES = 64 * 1024

SELECTED_FIELD_ALLOWLIST = frozenset(
    {
        "audience",
        "call_to_action",
        "channels",
        "constraints",
        "content_type",
        "deliverables",
        "key_message",
        "objective",
        "offer",
        "positioning_summary",
        "preferred_language",
        "prohibited_language",
        "required_language",
        "strategy_summary",
        "success_metrics",
        "tone",
    }
)
REQUIRED_SELECTED_FIELDS = frozenset(
    {"audience", "channels", "content_type", "objective"}
)
ORDERED_ARRAY_FIELDS = frozenset(
    {
        "channels",
        "constraints",
        "deliverables",
        "preferred_language",
        "prohibited_language",
        "required_language",
        "success_metrics",
    }
)
ALLOWED_SOURCE_TYPES = frozenset(
    {
        "audience",
        "campaign_plan",
        "customer_segment",
        "marketing_brief",
        "offer",
        "positioning",
        "product",
        "strategy",
        "voice",
    }
)
_DIGEST_PATTERN = re.compile(r"^[0-9a-f]{64}$")
_IDENTITY_PATTERN = re.compile(r"^[A-Za-z0-9._:-]{1,256}$")
_INSTRUCTION_MARKERS = re.compile(
    r"(?:<\|\s*(?:system|developer|assistant|tool)\s*\|>|"
    r"\b(?:ignore|disregard)\s+(?:all\s+)?(?:previous|prior)\s+instructions\b|"
    r"\b(?:system|developer|assistant|tool)\s*:\s*|"
    r"\b(?:jailbreak|prompt injection|reveal (?:the )?prompt)\b)",
    re.IGNORECASE,
)


class SourceLifecycle(StrEnum):
    """Lifecycle states for evidence references."""

    DRAFT = "draft"
    APPROVED = "approved"
    REVOKED = "revoked"
    SUPERSEDED = "superseded"
    EXPIRED = "expired"


class PrivacyClassification(StrEnum):
    """Privacy classification carried with safe source references."""

    PUBLIC = "public"
    INTERNAL = "internal"
    CONFIDENTIAL = "confidential"
    RESTRICTED = "restricted"


def _required_identity(value: str, field_name: str) -> str:
    if not isinstance(value, str):
        raise TypeError(f"{field_name} must be a string")
    cleaned = value.strip()
    if not _IDENTITY_PATTERN.fullmatch(cleaned):
        raise ValueError(f"{field_name} must be a bounded non-empty identifier")
    return cleaned


def _required_version(value: int, field_name: str) -> int:
    if type(value) is not int or value < 1:
        raise TypeError(f"{field_name} must be a positive integer")
    return value


@dataclass(frozen=True, slots=True)
class SourceReference:
    """Safe, content-free reference to an authoritative source record."""

    source_type: str
    source_id: str
    tenant_id: str
    brand_id: str
    version: int
    digest: str
    lifecycle: SourceLifecycle | str
    privacy_classification: PrivacyClassification | str

    def __post_init__(self) -> None:
        source_type = _required_identity(self.source_type, "source_type")
        if source_type not in ALLOWED_SOURCE_TYPES:
            raise ValueError("source_type is not supported")
        object.__setattr__(self, "source_type", source_type)
        object.__setattr__(
            self, "source_id", _required_identity(self.source_id, "source_id")
        )
        object.__setattr__(
            self, "tenant_id", _required_identity(self.tenant_id, "tenant_id")
        )
        object.__setattr__(
            self, "brand_id", _required_identity(self.brand_id, "brand_id")
        )
        object.__setattr__(self, "version", _required_version(self.version, "version"))
        if not isinstance(self.digest, str) or not _DIGEST_PATTERN.fullmatch(
            self.digest
        ):
            raise ValueError("digest must be lowercase SHA-256 hexadecimal")
        object.__setattr__(self, "lifecycle", SourceLifecycle(self.lifecycle))
        object.__setattr__(
            self,
            "privacy_classification",
            PrivacyClassification(self.privacy_classification),
        )

    def to_canonical(self) -> dict[str, Any]:
        return {
            "brand_id": self.brand_id,
            "digest": self.digest,
            "lifecycle": self.lifecycle.value,
            "privacy_classification": self.privacy_classification.value,
            "source_id": self.source_id,
            "source_type": self.source_type,
            "tenant_id": self.tenant_id,
            "version": self.version,
        }


@dataclass(frozen=True, slots=True)
class GroundingSnapshot:
    """Immutable canonical material used for one generation request."""

    generation_identity: str
    tenant_id: str
    brand_id: str
    captured_at: str
    selected_fields: Mapping[str, Any]
    source_refs: tuple[SourceReference, ...]
    schema_version: int = GROUNDING_SCHEMA_VERSION
    _canonical_bytes: bytes = b""
    _digest: str = ""

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "generation_identity",
            _required_identity(self.generation_identity, "generation_identity"),
        )
        object.__setattr__(
            self, "tenant_id", _required_identity(self.tenant_id, "tenant_id")
        )
        object.__setattr__(
            self, "brand_id", _required_identity(self.brand_id, "brand_id")
        )
        object.__setattr__(self, "captured_at", validate_timestamp(self.captured_at))
        object.__setattr__(
            self,
            "schema_version",
            _required_version(self.schema_version, "schema_version"),
        )
        if self.schema_version != GROUNDING_SCHEMA_VERSION:
            raise ValueError("unsupported grounding schema version")
        if not isinstance(self.selected_fields, Mapping):
            raise TypeError("selected_fields must be an object")
        selected = dict(self.selected_fields)
        unknown = set(selected) - SELECTED_FIELD_ALLOWLIST
        if unknown:
            raise ValueError("selected_fields contains unsupported fields")
        missing = REQUIRED_SELECTED_FIELDS - set(selected)
        if missing:
            raise ValueError("selected_fields is missing required fields")
        assert_privacy_safe(selected)
        _validate_selected_values(selected)
        object.__setattr__(self, "selected_fields", selected)
        refs = tuple(self.source_refs)
        if not refs or any(not isinstance(item, SourceReference) for item in refs):
            raise TypeError("source_refs must contain SourceReference values")
        object.__setattr__(self, "source_refs", refs)
        canonical = self._envelope()
        encoded = canonical_json_bytes(canonical)
        if len(encoded) > MAX_GROUNDING_SNAPSHOT_BYTES:
            raise ValueError("grounding snapshot exceeds maximum serialized size")
        digest = hashlib.sha256(
            GROUNDING_DOMAIN.encode("ascii") + b"\n" + encoded
        ).hexdigest()
        if self._canonical_bytes and self._canonical_bytes != encoded:
            raise ValueError("canonical snapshot bytes are immutable")
        if self._digest and self._digest != digest:
            raise ValueError("canonical snapshot digest is immutable")
        object.__setattr__(self, "_canonical_bytes", encoded)
        object.__setattr__(self, "_digest", digest)

    @classmethod
    def create(
        cls,
        *,
        generation_identity: str,
        tenant_id: str,
        brand_id: str,
        captured_at: str,
        selected_fields: Mapping[str, Any],
        source_refs: tuple[SourceReference, ...] | list[SourceReference],
        schema_version: int = GROUNDING_SCHEMA_VERSION,
    ) -> "GroundingSnapshot":
        return cls(
            generation_identity=generation_identity,
            tenant_id=tenant_id,
            brand_id=brand_id,
            captured_at=captured_at,
            selected_fields=selected_fields,
            source_refs=tuple(source_refs),
            schema_version=schema_version,
        )

    @property
    def canonical_bytes(self) -> bytes:
        return self._canonical_bytes

    @property
    def digest(self) -> str:
        return self._digest

    def replay_bytes(self) -> bytes:
        """Return the exact stored material for replay."""

        return self._canonical_bytes

    def regenerate(
        self, *, generation_identity: str, captured_at: str
    ) -> "GroundingSnapshot":
        """Create distinct material for deliberate regeneration."""

        if generation_identity == self.generation_identity:
            raise ValueError("regeneration requires a new generation identity")
        return type(self).create(
            generation_identity=generation_identity,
            tenant_id=self.tenant_id,
            brand_id=self.brand_id,
            captured_at=captured_at,
            selected_fields=self.selected_fields,
            source_refs=self.source_refs,
            schema_version=self.schema_version,
        )

    def _envelope(self) -> dict[str, Any]:
        ordered_refs = sorted(
            (reference.to_canonical() for reference in self.source_refs),
            key=lambda item: (
                item["source_type"],
                item["source_id"],
                item["version"],
                item["digest"],
            ),
        )
        return {
            "brand_id": self.brand_id,
            "captured_at": self.captured_at,
            "canonicalization_version": GROUNDING_CANONICALIZATION_VERSION,
            "generation_identity": self.generation_identity,
            "record_kind": "grounding_snapshot",
            "schema_version": self.schema_version,
            "selected_fields": self.selected_fields,
            "source_refs": ordered_refs,
            "tenant_id": self.tenant_id,
        }


def _validate_selected_values(
    values: Mapping[str, Any], *, field_name: str = "selected_fields"
) -> None:
    for key, value in values.items():
        if value is None:
            raise ValueError(f"{field_name}.{key} must be omitted rather than null")
        if isinstance(value, str):
            if _INSTRUCTION_MARKERS.search(value):
                raise ValueError(
                    "untrusted source content contains instruction material"
                )
        elif isinstance(value, Mapping):
            _validate_selected_values(value, field_name=f"{field_name}.{key}")
        elif isinstance(value, list | tuple):
            for item in value:
                if item is None:
                    raise ValueError(f"{field_name}.{key} must omit null array items")
                if isinstance(item, str) and _INSTRUCTION_MARKERS.search(item):
                    raise ValueError(
                        "untrusted source content contains instruction material"
                    )
                if isinstance(item, Mapping):
                    _validate_selected_values(item, field_name=f"{field_name}.{key}")
        elif isinstance(value, bool):
            continue
        elif type(value) is int:
            if abs(value) > 9_007_199_254_740_991:
                raise ValueError("numeric values must use the safe integer range")
        else:
            raise TypeError(f"{field_name}.{key} has an unsupported value type")
