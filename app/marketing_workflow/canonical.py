"""Versioned MLAI-CJ canonical JSON and domain-separated hashing."""

from __future__ import annotations

import hashlib
import json
import re
import unicodedata
from collections.abc import Mapping, Sequence
from datetime import UTC, datetime
from typing import Any

MLAI_CJ_1 = "MLAI-CJ-1"
MLAI_CJ_2 = "MLAI-CJ-2"
MLAI_CJ_1_SCHEMA_VERSION = 1
MLAI_CJ_2_SCHEMA_VERSION = 2
CANONICALIZATION_VERSION = MLAI_CJ_2
SCHEMA_VERSION = MLAI_CJ_2_SCHEMA_VERSION
SAFE_INTEGER_MAX = 9_007_199_254_740_991
TIMESTAMP_FORMAT = "%Y-%m-%dT%H:%M:%S.%fZ"

RECORD_DOMAINS = {
    (MLAI_CJ_1, 1, "command_request"): "earthonox/mlai-033.1/command-request/MLAI-CJ-1",
    (MLAI_CJ_1, 1, "command_receipt"): "earthonox/mlai-033.1/command-receipt/MLAI-CJ-1",
    (
        MLAI_CJ_1,
        1,
        "workflow_evidence",
    ): "earthonox/mlai-033.1/workflow-evidence/MLAI-CJ-1",
    (MLAI_CJ_2, 2, "command_request"): "earthonox/mlai-033.1/command-request/MLAI-CJ-2",
    (MLAI_CJ_2, 2, "command_receipt"): "earthonox/mlai-033.1/command-receipt/MLAI-CJ-2",
}
IDEMPOTENCY_DOMAINS = {
    (MLAI_CJ_1, 1): "earthonox/mlai-033.1/idempotency-key/MLAI-CJ-1",
    (MLAI_CJ_2, 2): "earthonox/mlai-033.1/idempotency-key/MLAI-CJ-2",
}
IDENTITY_DOMAINS = {
    "workflow": "earthonox/mlai-033.2/workflow-id/v1",
    "actor": "earthonox/mlai-033.2/actor-ref/v1",
    "request": "earthonox/mlai-033.2/subcommand-request/v1",
    "command_key": "earthonox/mlai-033.2/subcommand-idempotency/v1",
}
CLIENT_KEY_MIN_BYTES = 22
CLIENT_KEY_MAX_BYTES = 256
CLIENT_KEY_PATTERN = re.compile(r"^[A-Za-z0-9._~-]+$")
SENSITIVE_FIELD_MARKERS = frozenset(
    {
        "access_token",
        "api_key",
        "authorization",
        "binary_content",
        "contact_detail",
        "cookie",
        "credential",
        "csrf",
        "customer_content",
        "email",
        "identity_token",
        "password",
        "phone",
        "prompt",
        "provider_payload",
        "refresh_token",
        "request_payload",
        "response_payload",
        "session",
    }
)


def utc_timestamp(value: datetime | None = None) -> str:
    """Return the exact six-digit UTC timestamp required by MLAI-CJ-1."""

    selected = value or datetime.now(UTC)
    if selected.tzinfo is None:
        raise ValueError("timestamp must be timezone-aware")
    return selected.astimezone(UTC).strftime(TIMESTAMP_FORMAT)


def validate_timestamp(value: str) -> str:
    """Validate and return an exact MLAI-CJ-1 timestamp."""

    if not isinstance(value, str):
        raise TypeError("timestamp must be a string")
    try:
        parsed = datetime.strptime(value, TIMESTAMP_FORMAT).replace(tzinfo=UTC)
    except ValueError as error:
        raise ValueError("timestamp must use YYYY-MM-DDTHH:MM:SS.ffffffZ") from error
    if utc_timestamp(parsed) != value:
        raise ValueError("timestamp is not canonical")
    return value


def _nfc(value: str) -> str:
    normalized = unicodedata.normalize("NFC", value)
    if any(0xD800 <= ord(character) <= 0xDFFF for character in normalized):
        raise ValueError("lone UTF-16 surrogates are forbidden")
    return normalized


def _utf16_key(value: str) -> bytes:
    return value.encode("utf-16-be")


def _normalize(value: Any) -> Any:
    if value is None or isinstance(value, bool):
        return value
    if isinstance(value, int):
        if isinstance(value, bool) or abs(value) > SAFE_INTEGER_MAX:
            raise ValueError("JSON integers must be within the I-JSON safe range")
        return value
    if isinstance(value, float):
        raise TypeError("binary floating-point values are forbidden")
    if isinstance(value, str):
        return _nfc(value)
    if isinstance(value, Mapping):
        normalized_items: dict[str, Any] = {}
        for key, item in value.items():
            if not isinstance(key, str):
                raise TypeError("canonical object keys must be strings")
            normalized_key = _nfc(key)
            if normalized_key in normalized_items:
                raise ValueError("duplicate object key after NFC normalization")
            normalized_items[normalized_key] = _normalize(item)
        return {
            key: normalized_items[key]
            for key in sorted(normalized_items, key=_utf16_key)
        }
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return [_normalize(item) for item in value]
    raise TypeError(f"unsupported canonical JSON value: {type(value).__name__}")


def canonical_json_bytes(value: Mapping[str, Any]) -> bytes:
    """Return deterministic MLAI-CJ-1 bytes for one JSON object."""

    normalized = _normalize(value)
    if not isinstance(normalized, dict):
        raise TypeError("canonical envelope must be an object")
    encoded = json.dumps(
        normalized,
        ensure_ascii=False,
        allow_nan=False,
        separators=(",", ":"),
    )
    return encoded.encode("utf-8")


def canonical_json(value: Mapping[str, Any]) -> str:
    return canonical_json_bytes(value).decode("utf-8")


def assert_privacy_safe(value: Any) -> None:
    """Reject fields whose names denote material excluded by MLAI-CJ-1."""

    if isinstance(value, Mapping):
        for key, item in value.items():
            normalized_key = _nfc(str(key)).casefold().replace("-", "_")
            if any(marker in normalized_key for marker in SENSITIVE_FIELD_MARKERS):
                raise ValueError("safe command contains an excluded sensitive field")
            assert_privacy_safe(item)
    elif isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        for item in value:
            assert_privacy_safe(item)


def record_sha256(record_kind: str, envelope: Mapping[str, Any]) -> str:
    """Hash an exact canonical envelope under its declared governed domain."""

    schema_version = envelope.get("schema_version")
    if type(schema_version) is not int:
        raise ValueError("schema_version must be an integer")
    pair = (
        envelope.get("canonicalization_version"),
        schema_version,
        record_kind,
    )
    try:
        domain = RECORD_DOMAINS[pair]
    except KeyError as error:
        raise ValueError("unsupported or mismatched MLAI-CJ version pair") from error
    if envelope.get("record_kind") != record_kind:
        raise ValueError("record kind does not match its hash domain")
    preimage = (
        domain.encode("utf-8")
        + b"\n"
        + record_kind.encode("ascii")
        + b"\n"
        + canonical_json_bytes(envelope)
    )
    return hashlib.sha256(preimage).hexdigest()


def idempotency_key_sha256(
    caller_key: str,
    *,
    canonicalization_version: str = MLAI_CJ_2,
    schema_version: int = MLAI_CJ_2_SCHEMA_VERSION,
) -> str:
    """Hash a bounded opaque caller key without persisting its raw bytes."""

    if not isinstance(caller_key, str):
        raise TypeError("idempotency key must be a string")
    if type(schema_version) is not int:
        raise ValueError("schema_version must be an integer")
    normalized = _nfc(caller_key)
    if not normalized or len(normalized.encode("utf-8")) > 256:
        raise ValueError("idempotency key must contain 1 to 256 UTF-8 bytes")
    try:
        domain = IDEMPOTENCY_DOMAINS[(canonicalization_version, schema_version)]
    except KeyError as error:
        raise ValueError("unsupported or mismatched MLAI-CJ version pair") from error
    return hashlib.sha256(
        domain.encode("ascii") + b"\n" + normalized.encode("utf-8")
    ).hexdigest()


def validate_client_idempotency_key(value: str) -> str:
    """Validate the new API key representation without changing legacy keys."""

    if not isinstance(value, str):
        raise TypeError("client idempotency key must be a string")
    normalized = _nfc(value)
    encoded = normalized.encode("utf-8")
    if not (
        CLIENT_KEY_MIN_BYTES <= len(encoded) <= CLIENT_KEY_MAX_BYTES
        and CLIENT_KEY_PATTERN.fullmatch(normalized)
    ):
        raise ValueError(
            "client idempotency key must be 22 to 256 URL-safe UTF-8 bytes"
        )
    return normalized


def _identity_digest(kind: str, payload: Mapping[str, Any]) -> str:
    try:
        domain = IDENTITY_DOMAINS[kind]
    except KeyError as error:
        raise ValueError("unsupported identity derivation kind") from error
    return hashlib.sha256(
        domain.encode("ascii") + b"\n" + canonical_json_bytes(payload)
    ).hexdigest()


def deterministic_workflow_id(
    *,
    tenant_id: str,
    brand_id: str,
    actor_ref: str,
    operation: str,
    client_key_digest: str,
) -> str:
    """Derive one stable, privacy-safe 128-bit workflow identity."""

    assert_privacy_safe(
        {
            "tenant_id": tenant_id,
            "brand_id": brand_id,
            "actor_ref": actor_ref,
            "operation": operation,
            "client_key_digest": client_key_digest,
        }
    )
    digest = _identity_digest(
        "workflow",
        {
            "actor_ref": _nfc(actor_ref),
            "brand_id": _nfc(brand_id),
            "client_key_digest": _nfc(client_key_digest),
            "operation": _nfc(operation),
            "tenant_id": _nfc(tenant_id),
        },
    )
    return f"mwf_{digest[:32]}"


def deterministic_actor_ref(*, provider: str, subject_id: str) -> str:
    """Derive a stable pseudonymous reference from authenticated identity."""

    digest = _identity_digest(
        "actor",
        {"provider": _nfc(provider), "subject_id": _nfc(subject_id)},
    )
    return f"act_{digest[:32]}"


def deterministic_subcommand_request_id(
    *, orchestration_id: str, ordinal: int, command_kind: str
) -> str:
    """Derive a stable request ID for one orchestration command."""

    if type(ordinal) is not int or ordinal < 1:
        raise ValueError("subcommand ordinal must be a positive integer")
    digest = _identity_digest(
        "request",
        {
            "command_kind": _nfc(command_kind),
            "ordinal": ordinal,
            "orchestration_id": _nfc(orchestration_id),
        },
    )
    return f"req_{digest[:32]}"


def deterministic_command_key_digest(
    *, client_key_digest: str, ordinal: int, command_kind: str
) -> str:
    """Derive a command-specific digest from the orchestration claim."""

    if type(ordinal) is not int or ordinal < 1:
        raise ValueError("subcommand ordinal must be a positive integer")
    return _identity_digest(
        "command_key",
        {
            "client_key_digest": _nfc(client_key_digest),
            "command_kind": _nfc(command_kind),
            "ordinal": ordinal,
        },
    )


def sanitized_sha256(value: Mapping[str, Any]) -> str:
    """Hash privacy-safe structured content without a record envelope."""

    return hashlib.sha256(canonical_json_bytes(value)).hexdigest()
