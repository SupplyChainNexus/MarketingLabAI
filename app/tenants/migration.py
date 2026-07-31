"""Tenant database migration support."""

from __future__ import annotations

import sqlite3

from app.tenants.models import DEFAULT_TENANT_ID


def apply_tenant_migration(
    connection: sqlite3.Connection,
) -> None:
    """Create tenant persistence and the default tenant."""

    connection.execute("""
        CREATE TABLE IF NOT EXISTS tenants (
            tenant_id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            status TEXT NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
        """)

    connection.execute(
        """
        INSERT OR IGNORE INTO tenants (
            tenant_id,
            name,
            status,
            created_at,
            updated_at
        )
        VALUES (
            ?,
            'Default Tenant',
            'active',
            strftime('%Y-%m-%dT%H:%M:%fZ', 'now'),
            strftime('%Y-%m-%dT%H:%M:%fZ', 'now')
        )
        """,
        (DEFAULT_TENANT_ID,),
    )

    connection.execute("""
        INSERT OR IGNORE INTO schema_migrations (
            version,
            description,
            applied_at
        )
        VALUES (
            4,
            'Add tenant persistence foundation',
            strftime('%Y-%m-%dT%H:%M:%fZ', 'now')
        )
        """)
