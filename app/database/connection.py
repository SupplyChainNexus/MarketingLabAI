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

                CREATE TABLE IF NOT EXISTS product_intelligence_profiles (
                    tenant_id TEXT NOT NULL,
                    brand_id TEXT NOT NULL,
                    payload_json TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    PRIMARY KEY (tenant_id, brand_id),
                    FOREIGN KEY (tenant_id) REFERENCES tenants(tenant_id),
                    FOREIGN KEY (brand_id) REFERENCES brands(brand_id)
                        ON DELETE CASCADE
                );

                CREATE TABLE IF NOT EXISTS positioning_decisions (
                    positioning_id TEXT NOT NULL,
                    version INTEGER NOT NULL,
                    tenant_id TEXT NOT NULL,
                    brand_id TEXT NOT NULL,
                    target_kind TEXT NOT NULL,
                    target_id TEXT NOT NULL,
                    product_id TEXT NOT NULL,
                    status TEXT NOT NULL,
                    payload_json TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    approved_at TEXT,
                    PRIMARY KEY (tenant_id, positioning_id, version),
                    FOREIGN KEY (tenant_id) REFERENCES tenants(tenant_id),
                    FOREIGN KEY (brand_id) REFERENCES brands(brand_id)
                        ON DELETE CASCADE
                );

                CREATE INDEX IF NOT EXISTS idx_positioning_tenant_brand
                    ON positioning_decisions(tenant_id, brand_id);

                CREATE INDEX IF NOT EXISTS idx_positioning_target
                    ON positioning_decisions(
                        tenant_id, brand_id, target_kind, target_id
                    );

                CREATE INDEX IF NOT EXISTS idx_positioning_status
                    ON positioning_decisions(tenant_id, status);

                CREATE TABLE IF NOT EXISTS strategy_decisions (
                    strategy_id TEXT NOT NULL,
                    version INTEGER NOT NULL,
                    tenant_id TEXT NOT NULL,
                    brand_id TEXT NOT NULL,
                    positioning_id TEXT NOT NULL,
                    positioning_version INTEGER NOT NULL,
                    status TEXT NOT NULL,
                    payload_json TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    approved_at TEXT,
                    PRIMARY KEY (tenant_id, strategy_id, version),
                    FOREIGN KEY (tenant_id) REFERENCES tenants(tenant_id),
                    FOREIGN KEY (brand_id) REFERENCES brands(brand_id)
                        ON DELETE CASCADE
                );

                CREATE INDEX IF NOT EXISTS idx_strategy_tenant_brand
                    ON strategy_decisions(tenant_id, brand_id);

                CREATE INDEX IF NOT EXISTS idx_strategy_positioning
                    ON strategy_decisions(
                        tenant_id, positioning_id, positioning_version
                    );

                CREATE INDEX IF NOT EXISTS idx_strategy_status
                    ON strategy_decisions(tenant_id, status);

                CREATE TABLE IF NOT EXISTS tenant_memberships (
                    provider TEXT NOT NULL,
                    subject_id TEXT NOT NULL,
                    tenant_id TEXT NOT NULL,
                    role TEXT NOT NULL,
                    active INTEGER NOT NULL DEFAULT 1,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    PRIMARY KEY (provider, subject_id, tenant_id),
                    FOREIGN KEY (tenant_id) REFERENCES tenants(tenant_id)
                        ON DELETE CASCADE
                );

                CREATE INDEX IF NOT EXISTS idx_tenant_memberships_tenant
                    ON tenant_memberships(tenant_id, active);

                CREATE TABLE IF NOT EXISTS authorization_audit_events (
                    event_id TEXT PRIMARY KEY,
                    tenant_id TEXT NOT NULL,
                    subject_id TEXT NOT NULL,
                    provider TEXT NOT NULL,
                    action TEXT NOT NULL,
                    resource_type TEXT NOT NULL,
                    resource_id TEXT NOT NULL,
                    outcome TEXT NOT NULL,
                    occurred_at TEXT NOT NULL,
                    metadata_json TEXT NOT NULL DEFAULT '{}'
                );

                CREATE INDEX IF NOT EXISTS idx_authorization_audit_tenant
                    ON authorization_audit_events(tenant_id, occurred_at);

                CREATE TABLE IF NOT EXISTS api_idempotency_records (
                    tenant_id TEXT NOT NULL,
                    provider TEXT NOT NULL,
                    subject_id TEXT NOT NULL,
                    operation TEXT NOT NULL,
                    idempotency_key TEXT NOT NULL,
                    request_hash TEXT NOT NULL,
                    response_status INTEGER NOT NULL,
                    response_json TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    PRIMARY KEY (
                        tenant_id, provider, subject_id,
                        operation, idempotency_key
                    ),
                    FOREIGN KEY (tenant_id)
                        REFERENCES tenants(tenant_id)
                        ON DELETE CASCADE
                );

                CREATE TABLE IF NOT EXISTS pilot_sessions (
                    token_hash TEXT PRIMARY KEY,
                    csrf_hash TEXT NOT NULL,
                    provider TEXT NOT NULL,
                    subject_id TEXT NOT NULL,
                    tenant_id TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    expires_at TEXT NOT NULL,
                    revoked_at TEXT,
                    FOREIGN KEY (tenant_id) REFERENCES tenants(tenant_id)
                        ON DELETE CASCADE
                );

                CREATE INDEX IF NOT EXISTS idx_pilot_sessions_expiry
                    ON pilot_sessions(expires_at, revoked_at);

                CREATE TABLE IF NOT EXISTS pilot_privacy_acceptances (
                    tenant_id TEXT NOT NULL,
                    provider TEXT NOT NULL,
                    subject_id TEXT NOT NULL,
                    notice_version TEXT NOT NULL,
                    boundary_version TEXT NOT NULL,
                    accepted_at TEXT NOT NULL,
                    PRIMARY KEY (
                        tenant_id, provider, subject_id,
                        notice_version, boundary_version
                    ),
                    FOREIGN KEY (tenant_id) REFERENCES tenants(tenant_id)
                        ON DELETE CASCADE
                );

                CREATE INDEX IF NOT EXISTS idx_privacy_acceptance_tenant
                    ON pilot_privacy_acceptances(tenant_id, accepted_at);

                CREATE TABLE IF NOT EXISTS pilot_readiness_evidence (
                    evidence_id TEXT PRIMARY KEY,
                    check_name TEXT NOT NULL,
                    environment TEXT NOT NULL,
                    commit_sha TEXT NOT NULL,
                    operator_id TEXT NOT NULL,
                    passed INTEGER NOT NULL,
                    evidence_reference TEXT NOT NULL,
                    observed_at TEXT NOT NULL,
                    expires_at TEXT NOT NULL,
                    failure_classification TEXT NOT NULL DEFAULT '',
                    remediation TEXT NOT NULL DEFAULT '',
                    created_at TEXT NOT NULL
                );

                CREATE INDEX IF NOT EXISTS idx_readiness_evidence_lookup
                    ON pilot_readiness_evidence(
                        check_name, environment, commit_sha, observed_at
                    );

                CREATE TABLE IF NOT EXISTS pilot_activation_events (
                    event_id TEXT PRIMARY KEY,
                    decision_id TEXT NOT NULL,
                    tenant_id TEXT NOT NULL,
                    partner_name TEXT NOT NULL,
                    stage TEXT NOT NULL,
                    founder_id TEXT NOT NULL,
                    environment TEXT NOT NULL,
                    commit_sha TEXT NOT NULL,
                    allowed_categories_json TEXT NOT NULL DEFAULT '[]',
                    starts_at TEXT NOT NULL,
                    expires_at TEXT NOT NULL,
                    action TEXT NOT NULL,
                    reason TEXT NOT NULL DEFAULT '',
                    created_at TEXT NOT NULL,
                    FOREIGN KEY (tenant_id) REFERENCES tenants(tenant_id)
                        ON DELETE CASCADE
                );

                CREATE INDEX IF NOT EXISTS idx_activation_tenant_created
                    ON pilot_activation_events(tenant_id, created_at);

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

                CREATE TABLE IF NOT EXISTS marketing_workflows (
                    workflow_id TEXT NOT NULL,
                    tenant_id TEXT NOT NULL,
                    brand_id TEXT NOT NULL,
                    campaign_plan_id TEXT NOT NULL,
                    campaign_plan_version INTEGER NOT NULL,
                    marketing_brief_id TEXT,
                    marketing_brief_version INTEGER,
                    predecessor_workflow_id TEXT,
                    successor_workflow_id TEXT,
                    state TEXT NOT NULL,
                    failure_class TEXT,
                    version INTEGER NOT NULL,
                    blocked_resume_state TEXT,
                    canonical_artifact_ref_json TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    PRIMARY KEY (tenant_id, brand_id, workflow_id),
                    FOREIGN KEY (tenant_id) REFERENCES tenants(tenant_id),
                    FOREIGN KEY (brand_id) REFERENCES brands(brand_id)
                        ON DELETE CASCADE
                );

                CREATE INDEX IF NOT EXISTS idx_marketing_workflows_state
                    ON marketing_workflows(tenant_id, brand_id, state);

                CREATE UNIQUE INDEX IF NOT EXISTS
                    idx_marketing_workflows_recovery_predecessor
                    ON marketing_workflows(
                        tenant_id, brand_id, predecessor_workflow_id
                    )
                    WHERE predecessor_workflow_id IS NOT NULL;

                CREATE TABLE IF NOT EXISTS workflow_command_receipts (
                    receipt_id TEXT PRIMARY KEY,
                    tenant_id TEXT NOT NULL,
                    brand_id TEXT NOT NULL,
                    workflow_id TEXT NOT NULL,
                    command_kind TEXT NOT NULL,
                    idempotency_key_sha256 TEXT NOT NULL,
                    request_hash TEXT NOT NULL,
                    receipt_hash TEXT NOT NULL,
                    outcome TEXT NOT NULL,
                    canonical_json TEXT NOT NULL,
                    recorded_at TEXT NOT NULL,
                    FOREIGN KEY (tenant_id, brand_id, workflow_id)
                        REFERENCES marketing_workflows(
                            tenant_id, brand_id, workflow_id
                        )
                );

                CREATE INDEX IF NOT EXISTS idx_workflow_receipts_scope
                    ON workflow_command_receipts(
                        tenant_id, brand_id, workflow_id,
                        command_kind, idempotency_key_sha256
                    );

                CREATE TABLE IF NOT EXISTS workflow_idempotency_scopes (
                    tenant_id TEXT NOT NULL,
                    brand_id TEXT NOT NULL,
                    workflow_id TEXT NOT NULL,
                    command_kind TEXT NOT NULL,
                    idempotency_key_sha256 TEXT NOT NULL,
                    request_hash TEXT NOT NULL,
                    original_receipt_id TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    PRIMARY KEY (
                        tenant_id, brand_id, workflow_id,
                        command_kind, idempotency_key_sha256
                    ),
                    FOREIGN KEY (original_receipt_id)
                        REFERENCES workflow_command_receipts(receipt_id),
                    FOREIGN KEY (tenant_id, brand_id, workflow_id)
                        REFERENCES marketing_workflows(
                            tenant_id, brand_id, workflow_id
                        )
                );

                CREATE TABLE IF NOT EXISTS workflow_approvals (
                    approval_id TEXT PRIMARY KEY,
                    tenant_id TEXT NOT NULL,
                    brand_id TEXT NOT NULL,
                    workflow_id TEXT NOT NULL,
                    workflow_version INTEGER NOT NULL,
                    action TEXT NOT NULL,
                    decision TEXT NOT NULL,
                    requested_by_actor_ref TEXT NOT NULL,
                    decided_by_actor_ref TEXT NOT NULL,
                    decided_at TEXT NOT NULL,
                    canonical_json TEXT NOT NULL,
                    UNIQUE (
                        tenant_id, brand_id, workflow_id,
                        workflow_version, action
                    ),
                    FOREIGN KEY (tenant_id, brand_id, workflow_id)
                        REFERENCES marketing_workflows(
                            tenant_id, brand_id, workflow_id
                        )
                );

                CREATE INDEX IF NOT EXISTS idx_workflow_approvals_binding
                    ON workflow_approvals(
                        tenant_id, brand_id, workflow_id,
                        workflow_version, action
                    );

                CREATE TABLE IF NOT EXISTS workflow_evidence (
                    evidence_id TEXT PRIMARY KEY,
                    tenant_id TEXT NOT NULL,
                    brand_id TEXT NOT NULL,
                    workflow_id TEXT NOT NULL,
                    workflow_version INTEGER NOT NULL,
                    sequence INTEGER NOT NULL,
                    predecessor_sha256 TEXT NOT NULL,
                    evidence_sha256 TEXT NOT NULL,
                    canonical_json TEXT NOT NULL,
                    occurred_at TEXT NOT NULL,
                    UNIQUE (tenant_id, brand_id, workflow_id, sequence),
                    FOREIGN KEY (tenant_id, brand_id, workflow_id)
                        REFERENCES marketing_workflows(
                            tenant_id, brand_id, workflow_id
                        )
                );

                CREATE INDEX IF NOT EXISTS idx_workflow_evidence_chain
                    ON workflow_evidence(
                        tenant_id, brand_id, workflow_id, sequence
                    );

                CREATE TABLE IF NOT EXISTS workflow_artifact_proofs (
                    proof_id TEXT PRIMARY KEY,
                    tenant_id TEXT NOT NULL,
                    brand_id TEXT NOT NULL,
                    workflow_id TEXT NOT NULL,
                    workflow_version INTEGER NOT NULL,
                    command_receipt_id TEXT NOT NULL,
                    evidence_id TEXT NOT NULL,
                    availability TEXT NOT NULL,
                    artifact_id TEXT NOT NULL,
                    artifact_version INTEGER NOT NULL,
                    repository_revision TEXT NOT NULL,
                    content_sha256 TEXT,
                    proved_at TEXT NOT NULL,
                    canonical_json TEXT NOT NULL,
                    UNIQUE (command_receipt_id),
                    UNIQUE (evidence_id),
                    FOREIGN KEY (tenant_id, brand_id, workflow_id)
                        REFERENCES marketing_workflows(
                            tenant_id, brand_id, workflow_id
                        ),
                    FOREIGN KEY (command_receipt_id)
                        REFERENCES workflow_command_receipts(receipt_id),
                    FOREIGN KEY (evidence_id)
                        REFERENCES workflow_evidence(evidence_id)
                );

                CREATE INDEX IF NOT EXISTS idx_workflow_artifact_proof_scope
                    ON workflow_artifact_proofs(
                        tenant_id, brand_id, workflow_id, workflow_version
                    );

                CREATE TABLE IF NOT EXISTS workflow_recovery_scopes (
                    tenant_id TEXT NOT NULL,
                    brand_id TEXT NOT NULL,
                    predecessor_workflow_id TEXT NOT NULL,
                    successor_workflow_id TEXT NOT NULL,
                    request_hash TEXT NOT NULL,
                    original_receipt_id TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    PRIMARY KEY (
                        tenant_id, brand_id, predecessor_workflow_id
                    ),
                    UNIQUE (tenant_id, brand_id, successor_workflow_id),
                    FOREIGN KEY (
                        tenant_id, brand_id, predecessor_workflow_id
                    ) REFERENCES marketing_workflows(
                        tenant_id, brand_id, workflow_id
                    ),
                    FOREIGN KEY (
                        tenant_id, brand_id, successor_workflow_id
                    ) REFERENCES marketing_workflows(
                        tenant_id, brand_id, workflow_id
                    ),
                    FOREIGN KEY (original_receipt_id)
                        REFERENCES workflow_command_receipts(receipt_id)
                );

                CREATE TABLE IF NOT EXISTS workflow_recovery_conflict_scopes (
                    tenant_id TEXT NOT NULL,
                    brand_id TEXT NOT NULL,
                    predecessor_workflow_id TEXT NOT NULL,
                    request_workflow_id TEXT NOT NULL,
                    command_kind TEXT NOT NULL,
                    idempotency_key_sha256 TEXT NOT NULL,
                    request_hash TEXT NOT NULL,
                    authoritative_workflow_id TEXT NOT NULL,
                    authoritative_receipt_id TEXT NOT NULL,
                    conflict_receipt_id TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    PRIMARY KEY (
                        tenant_id, brand_id, request_workflow_id,
                        command_kind, idempotency_key_sha256
                    ),
                    FOREIGN KEY (
                        tenant_id, brand_id, predecessor_workflow_id
                    ) REFERENCES marketing_workflows(
                        tenant_id, brand_id, workflow_id
                    ),
                    FOREIGN KEY (
                        tenant_id, brand_id, authoritative_workflow_id
                    ) REFERENCES marketing_workflows(
                        tenant_id, brand_id, workflow_id
                    ),
                    FOREIGN KEY (authoritative_receipt_id)
                        REFERENCES workflow_command_receipts(receipt_id),
                    FOREIGN KEY (conflict_receipt_id)
                        REFERENCES workflow_command_receipts(receipt_id)
                );

                CREATE TABLE IF NOT EXISTS workflow_recovery_conflict_replays (
                    tenant_id TEXT NOT NULL,
                    brand_id TEXT NOT NULL,
                    request_workflow_id TEXT NOT NULL,
                    command_kind TEXT NOT NULL,
                    idempotency_key_sha256 TEXT NOT NULL,
                    request_hash TEXT NOT NULL,
                    requested_predecessor_workflow_id TEXT NOT NULL,
                    conflict_receipt_id TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    PRIMARY KEY (
                        tenant_id, brand_id, request_workflow_id,
                        command_kind, idempotency_key_sha256, request_hash
                    ),
                    FOREIGN KEY (
                        tenant_id, brand_id, request_workflow_id,
                        command_kind, idempotency_key_sha256
                    ) REFERENCES workflow_recovery_conflict_scopes(
                        tenant_id, brand_id, request_workflow_id,
                        command_kind, idempotency_key_sha256
                    ),
                    FOREIGN KEY (
                        tenant_id, brand_id, requested_predecessor_workflow_id
                    ) REFERENCES marketing_workflows(
                        tenant_id, brand_id, workflow_id
                    ),
                    FOREIGN KEY (conflict_receipt_id)
                        REFERENCES workflow_command_receipts(receipt_id)
                );

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
                    version, description, applied_at
                ) VALUES (
                    18,
                    'Add durable marketing workflow foundation',
                    strftime('%Y-%m-%dT%H:%M:%fZ', 'now')
                )
                """)

            connection.execute("""
                INSERT OR IGNORE INTO schema_migrations (
                    version, description, applied_at
                ) VALUES (
                    17,
                    'Add immutable pilot readiness evidence',
                    strftime('%Y-%m-%dT%H:%M:%fZ', 'now')
                )
                """)

            connection.execute("""
                INSERT OR IGNORE INTO schema_migrations (
                    version, description, applied_at
                ) VALUES (
                    16,
                    'Add versioned pilot privacy acceptance evidence',
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
                    15,
                    'Add versioned Marketing Strategy Intelligence decisions',
                    strftime('%Y-%m-%dT%H:%M:%fZ', 'now')
                )
                """)

            connection.execute("""
                INSERT OR IGNORE INTO schema_migrations (
                    version, description, applied_at
                ) VALUES (
                    13,
                    'Add revocable pilot sessions',
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

            connection.execute("""
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
                """)

            connection.execute("""
                INSERT OR IGNORE INTO schema_migrations (
                    version, description, applied_at
                ) VALUES (
                    11,
                    'Add identity memberships and authorization audit',
                    strftime('%Y-%m-%dT%H:%M:%fZ', 'now')
                )
                """)

            connection.execute("""
                INSERT OR IGNORE INTO schema_migrations (
                    version, description, applied_at
                ) VALUES (
                    12,
                    'Add pilot API idempotency records',
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
                    10,
                    'Add verified Product Intelligence profiles',
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
                    9,
                    'Add versioned campaign plans',
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
                    14,
                    'Add versioned Positioning Intelligence decisions',
                    strftime('%Y-%m-%dT%H:%M:%fZ', 'now')
                )
                """)

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
