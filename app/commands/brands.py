"""Brand application commands."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.commands.base import Command
from app.database.repositories import BrandRepository
from app.events.brand_events import BrandCreatedEvent
from app.events.publisher import EventPublisher
from app.tenants.repository import TenantRepository


@dataclass(slots=True)
class CreateBrandCommand(Command[dict[str, Any]]):
    """Create a tenant-owned brand."""

    payload: dict[str, Any]
    tenant_repository: TenantRepository
    brand_repository: BrandRepository
    event_publisher: EventPublisher | None = None

    def execute(self) -> dict[str, Any]:
        """Create the brand and publish its domain event."""

        payload = dict(self.payload)

        tenant_id = str(payload.get("tenant_id", "default")).strip()

        if not self.tenant_repository.exists(tenant_id):
            raise ValueError(f"Tenant '{tenant_id}' does not exist.")

        payload["tenant_id"] = tenant_id

        self.brand_repository.save(payload)

        created_brand = self.brand_repository.get(payload["brand_id"])

        publisher = self.event_publisher or EventPublisher()
        publisher.publish(
            BrandCreatedEvent(
                tenant_id=tenant_id,
                brand_id=str(created_brand["brand_id"]),
                brand_name=str(created_brand["name"]),
            )
        )

        return created_brand
