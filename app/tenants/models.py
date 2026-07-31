"""Tenant domain models."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

DEFAULT_TENANT_ID = "default"
ACTIVE_TENANT_STATUS = "active"
INACTIVE_TENANT_STATUS = "inactive"

VALID_TENANT_STATUSES = {
    ACTIVE_TENANT_STATUS,
    INACTIVE_TENANT_STATUS,
}


@dataclass(slots=True)
class Tenant:
    """An organisation that owns one or more brands."""

    tenant_id: str
    name: str
    status: str = ACTIVE_TENANT_STATUS
    created_at: str = ""
    updated_at: str = ""

    def __post_init__(self) -> None:
        """Clean and validate tenant data."""

        self.tenant_id = self.tenant_id.strip()
        self.name = self.name.strip()
        self.status = self.status.strip().casefold()
        self.created_at = self.created_at.strip()
        self.updated_at = self.updated_at.strip()

        if not self.tenant_id:
            raise ValueError("tenant_id is required.")

        if not self.name:
            raise ValueError("Tenant name is required.")

        if self.status not in VALID_TENANT_STATUSES:
            raise ValueError("Tenant status must be either 'active' or 'inactive'.")

    @property
    def is_active(self) -> bool:
        """Return whether the tenant is active."""

        return self.status == ACTIVE_TENANT_STATUS

    def to_dict(self) -> dict[str, Any]:
        """Return a serialisable tenant representation."""

        return asdict(self)

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "Tenant":
        """Create a tenant from dictionary data."""

        if not isinstance(payload, dict):
            raise TypeError("Tenant payload must be a dictionary.")

        return cls(
            tenant_id=str(payload.get("tenant_id", "")),
            name=str(payload.get("name", "")),
            status=str(payload.get("status", ACTIVE_TENANT_STATUS)),
            created_at=str(payload.get("created_at", "")),
            updated_at=str(payload.get("updated_at", "")),
        )
