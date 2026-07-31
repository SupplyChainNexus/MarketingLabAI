"""Tenant and brand-ownership database migrations."""

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


def apply_brand_ownership_migration(
    connection: sqlite3.Connection,
) -> None:
    """Attach every brand to a valid tenant."""

    columns = {
        str(row["name"])
        for row in connection.execute("PRAGMA table_info(brands)").fetchall()
    }

    if "tenant_id" not in columns:
        connection.execute("""
            ALTER TABLE brands
            ADD COLUMN tenant_id TEXT
                NOT NULL
                DEFAULT 'default'
            """)

    connection.execute(
        """
        UPDATE brands
        SET tenant_id = ?
        WHERE tenant_id IS NULL
           OR TRIM(tenant_id) = ''
        """,
        (DEFAULT_TENANT_ID,),
    )

    connection.execute("""
        CREATE INDEX IF NOT EXISTS idx_brands_tenant
        ON brands(tenant_id)
        """)

    connection.executescript("""
        CREATE TRIGGER IF NOT EXISTS
            validate_brand_tenant_insert
        BEFORE INSERT ON brands
        WHEN NOT EXISTS (
            SELECT 1
            FROM tenants
            WHERE tenant_id = NEW.tenant_id
        )
        BEGIN
            SELECT RAISE(
                ABORT,
                'Unknown tenant_id'
            );
        END;

        CREATE TRIGGER IF NOT EXISTS
            validate_brand_tenant_update
        BEFORE UPDATE OF tenant_id ON brands
        WHEN NOT EXISTS (
            SELECT 1
            FROM tenants
            WHERE tenant_id = NEW.tenant_id
        )
        BEGIN
            SELECT RAISE(
                ABORT,
                'Unknown tenant_id'
            );
        END;
        """)

    connection.execute("""
        INSERT OR IGNORE INTO schema_migrations (
            version,
            description,
            applied_at
        )
        VALUES (
            5,
            'Add tenant ownership to brands',
            strftime('%Y-%m-%dT%H:%M:%fZ', 'now')
        )
        """)
