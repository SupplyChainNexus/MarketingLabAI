"""Brand domain events."""

from __future__ import annotations

from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Any, Mapping

from app.events.models import DomainEvent


@dataclass(frozen=True, slots=True, kw_only=True)
class BrandCreatedEvent(DomainEvent):
    """Record that a tenant-owned brand was created."""

    tenant_id: str
    brand_name: str

    event_type: str = field(
        default="brand.created",
        init=False,
    )
    source: str = field(
        default="CreateBrandCommand",
        init=False,
    )
    summary: str = field(
        default="",
        init=False,
    )
    payload: Mapping[str, Any] = field(
        default_factory=dict,
        init=False,
    )

    def __post_init__(self) -> None:
        tenant_id = self.tenant_id.strip()
        brand_name = self.brand_name.strip()

        if not tenant_id:
            raise ValueError("tenant_id is required.")

        if not brand_name:
            raise ValueError("brand_name is required.")

        object.__setattr__(self, "tenant_id", tenant_id)
        object.__setattr__(self, "brand_name", brand_name)
        object.__setattr__(
            self,
            "summary",
            f"Brand '{brand_name}' was created.",
        )
        object.__setattr__(
            self,
            "payload",
            MappingProxyType(
                {
                    "tenant_id": tenant_id,
                    "brand_name": brand_name,
                }
            ),
        )

        super().__post_init__()
