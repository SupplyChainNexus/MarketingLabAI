"""Transport-safe contracts for the secure pilot API."""

from __future__ import annotations

import base64
import hashlib
import json
from dataclasses import dataclass
from typing import Any


def required_text(value: str, name: str) -> str:
    if not isinstance(value, str):
        raise TypeError(f"{name} must be a string.")
    value = value.strip()
    if not value:
        raise ValueError(f"{name} is required.")
    return value


@dataclass(slots=True, frozen=True)
class ContextRequest:
    brand_id: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "brand_id", required_text(self.brand_id, "brand_id"))


@dataclass(slots=True, frozen=True)
class WorkflowReviewRequest:
    brand_id: str
    campaign_id: str
    brief_id: str

    def __post_init__(self) -> None:
        for name in ("brand_id", "campaign_id", "brief_id"):
            object.__setattr__(self, name, required_text(getattr(self, name), name))


@dataclass(slots=True, frozen=True)
class DesignPartnerReadinessRequest:
    partner_name: str
    evidence: dict[str, bool]

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "partner_name", required_text(self.partner_name, "partner_name")
        )
        if not isinstance(self.evidence, dict):
            raise TypeError("evidence must be an object.")


@dataclass(slots=True, frozen=True)
class DesignPartnerAcceptanceRequest:
    partner_name: str

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "partner_name", required_text(self.partner_name, "partner_name")
        )


@dataclass(slots=True, frozen=True)
class DesignPartnerSignupRequest:
    partner_name: str
    invitation_code: str
    privacy_notice_accepted: bool
    synthetic_data_boundary_accepted: bool
    privacy_notice_version: str = "pilot-privacy-notice-v1"
    data_boundary_version: str = "synthetic-data-boundary-v1"

    def __post_init__(self) -> None:
        for name in ("partner_name", "invitation_code"):
            object.__setattr__(self, name, required_text(getattr(self, name), name))
        for name in (
            "privacy_notice_accepted",
            "synthetic_data_boundary_accepted",
        ):
            if not isinstance(getattr(self, name), bool):
                raise TypeError(f"{name} must be a boolean.")
        for name in ("privacy_notice_version", "data_boundary_version"):
            object.__setattr__(self, name, required_text(getattr(self, name), name))


@dataclass(slots=True, frozen=True)
class DataBoundaryRequest:
    category: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "category", required_text(self.category, "category"))


@dataclass(slots=True, frozen=True)
class OnboardingRequest:
    brand_id: str
    business: dict[str, Any]
    customer: dict[str, Any]
    product: dict[str, Any]

    def __post_init__(self) -> None:
        object.__setattr__(self, "brand_id", required_text(self.brand_id, "brand_id"))
        for name in ("business", "customer", "product"):
            if not isinstance(getattr(self, name), dict):
                raise TypeError(f"{name} must be an object.")
        for name in ("segment_id", "name", "evidence_source"):
            required_text(self.customer.get(name, ""), f"customer.{name}")
        for name in ("product_id", "name", "product_type", "evidence_source"):
            required_text(self.product.get(name, ""), f"product.{name}")
        if self.product["product_type"] not in {"product", "service"}:
            raise ValueError("product.product_type must be product or service.")
        for section, names in (
            (self.business, ("geographic_markets", "business_goals")),
            (
                self.product,
                ("features", "benefits", "limitations", "prohibited_claims"),
            ),
        ):
            for name in names:
                if name in section and (
                    not isinstance(section[name], list)
                    or any(not isinstance(item, str) for item in section[name])
                ):
                    raise TypeError(f"{name} must be a list of strings.")


@dataclass(slots=True, frozen=True)
class GenerationRequest:
    brand_id: str
    campaign_id: str
    campaign_version: int
    brief_id: str
    brief_version: int
    task: str
    instructions: str = ""

    def __post_init__(self) -> None:
        object.__setattr__(self, "brand_id", required_text(self.brand_id, "brand_id"))
        object.__setattr__(
            self, "campaign_id", required_text(self.campaign_id, "campaign_id")
        )
        object.__setattr__(self, "brief_id", required_text(self.brief_id, "brief_id"))
        for name in ("campaign_version", "brief_version"):
            value = getattr(self, name)
            if isinstance(value, bool) or not isinstance(value, int):
                raise TypeError(f"{name} must be an integer.")
            if value < 1:
                raise ValueError(f"{name} must be at least 1.")
        object.__setattr__(self, "task", required_text(self.task, "task"))
        if not isinstance(self.instructions, str):
            raise TypeError("instructions must be a string.")
        object.__setattr__(self, "instructions", self.instructions.strip())


@dataclass(slots=True, frozen=True)
class ApprovalRequest:
    expected_version: int

    def __post_init__(self) -> None:
        if isinstance(self.expected_version, bool) or not isinstance(
            self.expected_version, int
        ):
            raise TypeError("expected_version must be an integer.")
        if self.expected_version < 1:
            raise ValueError("expected_version must be at least 1.")


@dataclass(slots=True, frozen=True)
class WorkflowCreateRequest:
    """Exact immutable references used to create and plan a workflow."""

    brand_id: str
    campaign_plan_id: str
    campaign_plan_version: int
    marketing_brief_id: str | None = None
    marketing_brief_version: int | None = None

    def __post_init__(self) -> None:
        for name in ("brand_id", "campaign_plan_id"):
            object.__setattr__(self, name, required_text(getattr(self, name), name))
        for name in ("campaign_plan_version", "marketing_brief_version"):
            value = getattr(self, name)
            if value is not None and (type(value) is not int or value < 1):
                raise TypeError(f"{name} must be a positive integer.")
        if bool(self.marketing_brief_id) != (self.marketing_brief_version is not None):
            raise ValueError(
                "marketing_brief_id and marketing_brief_version must be supplied together."
            )
        if self.marketing_brief_id is not None:
            object.__setattr__(
                self,
                "marketing_brief_id",
                required_text(self.marketing_brief_id, "marketing_brief_id"),
            )


@dataclass(slots=True, frozen=True)
class WorkflowCommandRequest:
    expected_version: int

    def __post_init__(self) -> None:
        if type(self.expected_version) is not int or self.expected_version < 1:
            raise TypeError("expected_version must be a positive integer.")


@dataclass(slots=True, frozen=True)
class WorkflowApprovalDecisionRequest:
    expected_version: int
    decision: str

    def __post_init__(self) -> None:
        if type(self.expected_version) is not int or self.expected_version < 1:
            raise TypeError("expected_version must be a positive integer.")
        object.__setattr__(self, "decision", required_text(self.decision, "decision"))
        if self.decision not in {"approved", "rejected"}:
            raise ValueError("decision must be approved or rejected.")


@dataclass(slots=True, frozen=True)
class CampaignRevisionRequest:
    expected_version: int
    changes: dict[str, Any]

    def __post_init__(self) -> None:
        _revision_values(
            self.expected_version,
            self.changes,
            {"name", "owner", "notes", "positioning_id", "positioning_version"},
        )


@dataclass(slots=True, frozen=True)
class BriefRevisionRequest:
    expected_version: int
    changes: dict[str, Any]

    def __post_init__(self) -> None:
        _revision_values(
            self.expected_version,
            self.changes,
            {
                "name",
                "objective",
                "audience",
                "offer",
                "key_message",
                "call_to_action",
                "channels",
                "deliverables",
                "constraints",
                "success_metrics",
                "assumptions",
                "notes",
                "positioning_id",
                "positioning_version",
            },
        )


def _revision_values(expected_version: int, changes: dict, allowed: set[str]) -> None:
    ApprovalRequest(expected_version)
    if not isinstance(changes, dict):
        raise TypeError("changes must be an object.")
    if not changes:
        raise ValueError("changes must include at least one revision.")
    unsupported = set(changes) - allowed
    if unsupported:
        raise ValueError(
            f"Unsupported revision fields: {', '.join(sorted(unsupported))}."
        )


@dataclass(slots=True, frozen=True)
class ExportRequest:
    resource_type: str
    resource_id: str

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "resource_type", required_text(self.resource_type, "resource_type")
        )
        object.__setattr__(
            self, "resource_id", required_text(self.resource_id, "resource_id")
        )


@dataclass(slots=True, frozen=True)
class ApiResponse:
    status: int
    data: dict[str, Any]
    replayed: bool = False
    headers: tuple[tuple[str, str], ...] = ()
    body_bytes: bytes | None = None
    replay_marker_in_body: bool = True

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "data": self.data,
            "replayed": self.replayed,
        }


def _canonical_http_json(value: dict[str, Any]) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        allow_nan=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def workflow_response(status: int, data: dict[str, Any], *, replayed: bool = False):
    """Build a transport-stable workflow response without a replay body marker."""

    if type(status) is not int or not 100 <= status <= 599:
        raise ValueError("status must be an HTTP status")
    body = _canonical_http_json({"data": data})
    headers = (
        ("Content-Type", "application/json; charset=utf-8"),
        ("Content-Length", str(len(body))),
    )
    return ApiResponse(
        status=status,
        data=data,
        replayed=replayed,
        headers=headers,
        body_bytes=body,
        replay_marker_in_body=False,
    )


def workflow_response_envelope(response: ApiResponse) -> dict[str, Any]:
    """Return the complete canonical response envelope and its body digest."""

    if response.body_bytes is None or response.replay_marker_in_body:
        raise ValueError("workflow response must have stable body bytes")
    body_digest = hashlib.sha256(response.body_bytes).hexdigest()
    envelope = {
        "response_envelope_version": 1,
        "status": response.status,
        "headers": [[name, value] for name, value in response.headers],
        "body_utf8_b64": base64.b64encode(response.body_bytes).decode("ascii"),
        "body_sha256": body_digest,
    }
    envelope["envelope_sha256"] = hashlib.sha256(
        _canonical_http_json(envelope)
    ).hexdigest()
    return envelope


def workflow_response_from_envelope(
    envelope: dict[str, Any], *, replayed: bool = True
) -> ApiResponse:
    """Validate and reconstruct a persisted workflow response exactly."""

    if envelope.get("response_envelope_version") != 1:
        raise ValueError("unsupported workflow response envelope version")
    status = envelope.get("status")
    headers = envelope.get("headers")
    encoded_body = envelope.get("body_utf8_b64")
    body_digest = envelope.get("body_sha256")
    envelope_digest = envelope.get("envelope_sha256")
    if (
        type(status) is not int
        or not 100 <= status <= 599
        or not isinstance(headers, list)
        or not isinstance(encoded_body, str)
        or not isinstance(body_digest, str)
        or not isinstance(envelope_digest, str)
    ):
        raise ValueError("invalid workflow response envelope")
    if any(
        not isinstance(item, list)
        or len(item) != 2
        or not all(isinstance(value, str) for value in item)
        for item in headers
    ):
        raise ValueError("invalid workflow response headers")
    try:
        body = base64.b64decode(encoded_body.encode("ascii"), validate=True)
    except (ValueError, UnicodeEncodeError) as error:
        raise ValueError("invalid workflow response body encoding") from error
    if hashlib.sha256(body).hexdigest() != body_digest:
        raise ValueError("workflow response body digest mismatch")
    unsigned = dict(envelope)
    unsigned.pop("envelope_sha256", None)
    if hashlib.sha256(_canonical_http_json(unsigned)).hexdigest() != envelope_digest:
        raise ValueError("workflow response envelope digest mismatch")
    try:
        payload = json.loads(body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ValueError(
            "workflow response body is not canonical UTF-8 JSON"
        ) from error
    if not isinstance(payload, dict) or set(payload) != {"data"}:
        raise ValueError("workflow response body shape is invalid")
    return ApiResponse(
        status=status,
        data=payload["data"],
        replayed=replayed,
        headers=tuple((item[0], item[1]) for item in headers),
        body_bytes=body,
        replay_marker_in_body=False,
    )
