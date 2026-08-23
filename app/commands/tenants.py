"""Tenant application commands."""

from __future__ import annotations

from dataclasses import dataclass

from app.commands.base import Command
from app.database import SQLiteDatabase, bootstrap_database
from app.tenants.models import ACTIVE_TENANT_STATUS, Tenant
from app.tenants.repository import TenantRepository


@dataclass(slots=True)
class CreateTenantCommand(Command[Tenant]):
    """Create and persist a new tenant."""

    tenant_id: str
    name: str
    status: str = ACTIVE_TENANT_STATUS
    repository: TenantRepository | None = None

    def execute(self) -> Tenant:
        """Validate and create the tenant."""

        repository = self.repository
        if repository is None:
            repository = TenantRepository(bootstrap_database(SQLiteDatabase()))

        tenant = Tenant(
            tenant_id=self.tenant_id,
            name=self.name,
            status=self.status,
        )

        if repository.exists(tenant.tenant_id):
            raise ValueError(
                f"A tenant with ID '{tenant.tenant_id}' " "already exists."
            )

        repository.save(tenant)
        return tenant
