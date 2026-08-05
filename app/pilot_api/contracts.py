"""Transport-safe contracts for the secure pilot API."""

from __future__ import annotations

from dataclasses import asdict, dataclass
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

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
