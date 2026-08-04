"""SQLite connection management for MarketingLabAI."""

from __future__ import annotations

import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

from app.tenants.migration import (
    apply_brand_ownership_migration,
    apply_tenant_migration,
)


class SQLiteDatabase:
    """Manage SQLite connections and database initialisation."""

    def __init__(
        self,
        database_path: str | Path = "database/marketinglabai.db",
    ) -> None:
        self.database_path = Path(database_path)
        self.database_path.parent.mkdir(parents=True, exist_ok=True)

    def connect(self) -> sqlite3.Connection:
        """Create and return a configured SQLite connection."""

        connection = sqlite3.connect(
            self.database_path,
            timeout=30,
        )
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute("PRAGMA journal_mode = WAL")
        connection.execute("PRAGMA synchronous = NORMAL")
        connection.execute("PRAGMA busy_timeout = 30000")

        return connection

    @contextmanager
    def connection(self) -> Iterator[sqlite3.Connection]:
        """Provide a connection that is always closed after use."""

        connection = self.connect()

        try:
            yield connection
        finally:
            connection.close()

    @contextmanager
    def transaction(self) -> Iterator[sqlite3.Connection]:
        """Provide a transaction with commit, rollback, and guaranteed close."""

        connection = self.connect()

        try:
            connection.execute("BEGIN")
            yield connection
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    def initialise(self) -> None:
        """Create all current database tables and indexes."""

        with self.transaction() as connection:
            connection.executescript("""
                CREATE TABLE IF NOT EXISTS schema_migrations (
                    version INTEGER PRIMARY KEY,
                    description TEXT NOT NULL,
                    applied_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS brands (
                    brand_id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    industry TEXT NOT NULL DEFAULT '',
                    description TEXT NOT NULL DEFAULT '',
                    target_audience_json TEXT NOT NULL DEFAULT '[]',
                    products_json TEXT NOT NULL DEFAULT '[]',
                    values_json TEXT NOT NULL DEFAULT '[]',
                    website TEXT NOT NULL DEFAULT '',
                    payload_json TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS business_intelligence_profiles (
                    brand_id TEXT PRIMARY KEY,
                    revenue_model TEXT NOT NULL DEFAULT '',
                    average_order_value REAL,
                    gross_margin_percent REAL,
                    customer_lifetime_value REAL,
                    customer_acquisition_cost REAL,
                    sales_cycle_days INTEGER,
                    monthly_marketing_budget REAL,
                    team_size INTEGER,
                    sales_channels_json TEXT NOT NULL DEFAULT '[]',
                    geographic_markets_json TEXT NOT NULL DEFAULT '[]',
                    capacity_constraints_json TEXT NOT NULL DEFAULT '[]',
                    seasonality_json TEXT NOT NULL DEFAULT '[]',
                    competitors_json TEXT NOT NULL DEFAULT '[]',
                    business_goals_json TEXT NOT NULL DEFAULT '[]',
                    payload_json TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    FOREIGN KEY (brand_id)
                        REFERENCES brands(brand_id)
                        ON DELETE CASCADE
                );

                CREATE TABLE IF NOT EXISTS customer_intelligence_profiles (
                    brand_id TEXT PRIMARY KEY,
                    summary TEXT NOT NULL DEFAULT '',
                    primary_segment_id TEXT NOT NULL DEFAULT '',
                    segments_json TEXT NOT NULL DEFAULT '[]',
                    ideal_customer_profiles_json TEXT NOT NULL DEFAULT '[]',
                    personas_json TEXT NOT NULL DEFAULT '[]',
                    payload_json TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    FOREIGN KEY (brand_id)
                        REFERENCES brands(brand_id)
                        ON DELETE CASCADE
                );

                CREATE TABLE IF NOT EXISTS compliance_rules (
                    rule_id TEXT NOT NULL,
                    version INTEGER NOT NULL,
                    brand_id TEXT NOT NULL,
                    name TEXT NOT NULL,
                    category TEXT NOT NULL DEFAULT '',
                    severity TEXT NOT NULL,
                    evaluation_method TEXT NOT NULL,
                    enabled INTEGER NOT NULL DEFAULT 1,
                    evidence_required INTEGER NOT NULL DEFAULT 0,
                    payload_json TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    PRIMARY KEY (rule_id, version),
                    FOREIGN KEY (brand_id)
                        REFERENCES brands(brand_id)
                        ON DELETE CASCADE
                );


                CREATE TABLE IF NOT EXISTS prompt_packs (
                    prompt_pack_id TEXT NOT NULL,
                    version INTEGER NOT NULL,
                    tenant_id TEXT NOT NULL,
                    brand_id TEXT,
                    name TEXT NOT NULL,
                    task_type TEXT NOT NULL,
                    channel TEXT NOT NULL DEFAULT '',
                    enabled INTEGER NOT NULL DEFAULT 1,
                    payload_json TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    PRIMARY KEY (prompt_pack_id, version),
                    FOREIGN KEY (tenant_id)
                        REFERENCES tenants(tenant_id)
                        ON DELETE CASCADE,
                    FOREIGN KEY (brand_id)
                        REFERENCES brands(brand_id)
                        ON DELETE CASCADE
                );

                CREATE TABLE IF NOT EXISTS memory_events (
                    memory_id TEXT PRIMARY KEY,
                    brand_id TEXT NOT NULL,
                    event_type TEXT NOT NULL,
                    source TEXT NOT NULL,
                    summary TEXT NOT NULL,
                    payload_json TEXT NOT NULL DEFAULT '{}',
                    created_at TEXT NOT NULL,
                    FOREIGN KEY (brand_id)
                        REFERENCES brands(brand_id)
                        ON DELETE CASCADE
                );

                CREATE TABLE IF NOT EXISTS data_migration_log (
                    migration_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    source_type TEXT NOT NULL,
                    source_path TEXT NOT NULL,
                    record_id TEXT NOT NULL,
                    status TEXT NOT NULL,
                    message TEXT NOT NULL DEFAULT '',
                    migrated_at TEXT NOT NULL
                );

                CREATE INDEX IF NOT EXISTS idx_brands_name
                    ON brands(name);

                CREATE INDEX IF NOT EXISTS idx_brands_industry
                    ON brands(industry);

                CREATE INDEX IF NOT EXISTS
                    idx_business_intelligence_revenue_model
                    ON business_intelligence_profiles(revenue_model);

                CREATE INDEX IF NOT EXISTS
                    idx_customer_intelligence_primary_segment
                    ON customer_intelligence_profiles(primary_segment_id);

                CREATE INDEX IF NOT EXISTS idx_compliance_rules_brand
                    ON compliance_rules(brand_id);

                CREATE INDEX IF NOT EXISTS idx_compliance_rules_enabled
                    ON compliance_rules(brand_id, enabled);


                CREATE TABLE IF NOT EXISTS marketing_briefs (
                    brief_id TEXT NOT NULL,
                    version INTEGER NOT NULL,
                    tenant_id TEXT NOT NULL,
                    brand_id TEXT NOT NULL,
                    name TEXT NOT NULL,
                    status TEXT NOT NULL,
                    payload_json TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    PRIMARY KEY (brief_id, version),
                    FOREIGN KEY (tenant_id)
                        REFERENCES tenants(tenant_id),
                    FOREIGN KEY (brand_id)
                        REFERENCES brands(brand_id)
                        ON DELETE CASCADE
                );

                CREATE INDEX IF NOT EXISTS idx_marketing_briefs_tenant
                    ON marketing_briefs(tenant_id);

                CREATE INDEX IF NOT EXISTS idx_marketing_briefs_brand
                    ON marketing_briefs(tenant_id, brand_id);

                CREATE INDEX IF NOT EXISTS idx_marketing_briefs_status
                    ON marketing_briefs(tenant_id, status);

                CREATE TABLE IF NOT EXISTS campaign_plans (
                    campaign_id TEXT NOT NULL,
                    version INTEGER NOT NULL,
                    tenant_id TEXT NOT NULL,
                    brand_id TEXT NOT NULL,
                    name TEXT NOT NULL,
                    status TEXT NOT NULL,
                    payload_json TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    PRIMARY KEY (campaign_id, version),
                    FOREIGN KEY (tenant_id)
                        REFERENCES tenants(tenant_id),
                    FOREIGN KEY (brand_id)
                        REFERENCES brands(brand_id)
                        ON DELETE CASCADE
                );

                CREATE INDEX IF NOT EXISTS idx_campaign_plans_tenant
                    ON campaign_plans(tenant_id);

                CREATE INDEX IF NOT EXISTS idx_campaign_plans_brand
                    ON campaign_plans(tenant_id, brand_id);

                CREATE INDEX IF NOT EXISTS idx_campaign_plans_status
                    ON campaign_plans(tenant_id, status);

                CREATE INDEX IF NOT EXISTS idx_prompt_packs_tenant
                    ON prompt_packs(tenant_id);

                CREATE INDEX IF NOT EXISTS idx_prompt_packs_brand
                    ON prompt_packs(brand_id);

                CREATE INDEX IF NOT EXISTS idx_prompt_packs_task_type
                    ON prompt_packs(tenant_id, task_type);

                CREATE INDEX IF NOT EXISTS idx_prompt_packs_channel
                    ON prompt_packs(tenant_id, channel);

                CREATE INDEX IF NOT EXISTS idx_prompt_packs_enabled
                    ON prompt_packs(tenant_id, enabled);

                CREATE INDEX IF NOT EXISTS idx_memory_events_brand
                    ON memory_events(brand_id);

                CREATE INDEX IF NOT EXISTS idx_memory_events_type
                    ON memory_events(brand_id, event_type);

                CREATE INDEX IF NOT EXISTS idx_memory_events_created
                    ON memory_events(brand_id, created_at);

                CREATE INDEX IF NOT EXISTS idx_data_migration_log_record
                    ON data_migration_log(source_type, record_id);
                """)

            apply_tenant_migration(connection)
            apply_brand_ownership_migration(connection)

            connection.execute("""
                INSERT OR IGNORE INTO schema_migrations (
                    version,
                    description,
                    applied_at
                )
                VALUES (
                    2,
                    'Add versioned compliance rules',
                    strftime('%Y-%m-%dT%H:%M:%fZ', 'now')
                )
                """)

            connection.execute("""
                INSERT OR IGNORE INTO schema_migrations (
                    version,
                    description,
                    applied_at
                )
                VALUES (
                    3,
                    'Add institutional memory events',
                    strftime('%Y-%m-%dT%H:%M:%fZ', 'now')
                )
                """)

            connection.execute("""
                INSERT OR IGNORE INTO schema_migrations (
                    version,
                    description,
                    applied_at
                )
                VALUES (
                    6,
                    'Add versioned prompt packs',
                    strftime('%Y-%m-%dT%H:%M:%fZ', 'now')
                )
                """)

            connection.execute("""
                INSERT OR IGNORE INTO schema_migrations (
                    version,
                    description,
                    applied_at
                )
                VALUES (
                    7,
                    'Add Customer Intelligence profiles',
                    strftime('%Y-%m-%dT%H:%M:%fZ', 'now')
                )
                """)

            connection.execute("""
                INSERT OR IGNORE INTO schema_migrations (
                    version,
                    description,
                    applied_at
                )
                VALUES (
                    1,
                    'Initial MarketingLabAI relational schema',
                    strftime('%Y-%m-%dT%H:%M:%fZ', 'now')
                )
                """)

            connection.execute(
                """
                INSERT OR IGNORE INTO schema_migrations (
                    version,
                    description,
                    applied_at
                )
                VALUES (
                    8,
                    'Add versioned marketing briefs',
                    strftime('%Y-%m-%dT%H:%M:%fZ', 'now')
                )
                """
            )

            connection.execute(
                """
                INSERT OR IGNORE INTO schema_migrations (
                    version,
                    description,
                    applied_at
                )
                VALUES (
                    9,
                    'Add versioned campaign plans',
                    strftime('%Y-%m-%dT%H:%M:%fZ', 'now')
                )
                """
            )

    def table_names(self) -> list[str]:
        """Return application table names."""

        with self.connection() as connection:
            rows = connection.execute("""
                SELECT name
                FROM sqlite_master
                WHERE type = 'table'
                  AND name NOT LIKE 'sqlite_%'
                ORDER BY name
                """).fetchall()

        return [str(row["name"]) for row in rows]

    def integrity_check(self) -> str:
        """Run SQLite's built-in database integrity check."""

        with self.connection() as connection:
            row = connection.execute("PRAGMA integrity_check").fetchone()

        if row is None:
            raise RuntimeError("SQLite did not return an integrity result.")

        return str(row[0])

    def checkpoint(self) -> None:
        """Checkpoint and truncate SQLite's write-ahead log."""

        with self.connection() as connection:
            connection.execute("PRAGMA wal_checkpoint(TRUNCATE)").fetchone()
