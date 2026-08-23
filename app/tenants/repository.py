"""SQLite repository for tenants."""

from __future__ import annotations

from app.database.connection import SQLiteDatabase
from app.database.repositories import current_utc_timestamp
from app.tenants.models import Tenant


class TenantRepository:
    """Repository responsible for tenant persistence."""

    def __init__(
        self,
        database: SQLiteDatabase | None = None,
    ) -> None:
        self.database = database or SQLiteDatabase()

    def save(self, tenant: Tenant) -> None:
        """Insert or update a tenant."""

        if not isinstance(tenant, Tenant):
            raise TypeError("tenant must be a Tenant.")

        timestamp = current_utc_timestamp()
        created_at = tenant.created_at or timestamp

        with self.database.transaction() as connection:
            connection.execute(
                """
                INSERT INTO tenants (
                    tenant_id,
                    name,
                    status,
                    created_at,
                    updated_at
                )
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(tenant_id)
                DO UPDATE SET
                    name = excluded.name,
                    status = excluded.status,
                    updated_at = excluded.updated_at
                """,
                (
                    tenant.tenant_id,
                    tenant.name,
                    tenant.status,
                    created_at,
                    timestamp,
                ),
            )

        tenant.created_at = created_at
        tenant.updated_at = timestamp

    def get(self, tenant_id: str) -> Tenant:
        """Load one tenant."""

        with self.database.connection() as connection:
            row = connection.execute(
                """
                SELECT *
                FROM tenants
                WHERE tenant_id = ?
                """,
                (tenant_id,),
            ).fetchone()

        if row is None:
            raise FileNotFoundError(f"No tenant exists with ID '{tenant_id}'.")

        return Tenant.from_dict(dict(row))

    def exists(self, tenant_id: str) -> bool:
        """Return whether a tenant exists."""

        with self.database.connection() as connection:
            row = connection.execute(
                """
                SELECT 1
                FROM tenants
                WHERE tenant_id = ?
                LIMIT 1
                """,
                (tenant_id,),
            ).fetchone()

        return row is not None

    def list(self) -> list[Tenant]:
        """Return all tenants."""

        with self.database.connection() as connection:
            rows = connection.execute("""
                SELECT *
                FROM tenants
                ORDER BY tenant_id
                """).fetchall()

        return [Tenant.from_dict(dict(row)) for row in rows]

    def count(self) -> int:
        """Return tenant count."""

        with self.database.connection() as connection:
            row = connection.execute("""
                SELECT COUNT(*) AS total
                FROM tenants
                """).fetchone()

        return int(row["total"]) if row else 0
