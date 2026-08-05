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
