"""SQLite membership and authorization-audit persistence."""

from __future__ import annotations

import json
from uuid import uuid4

from app.database.connection import SQLiteDatabase
from app.identity.models import AuthorizationAuditEvent, TenantMembership

MEMBERSHIP_SESSION_INVALIDATION_SQL = """
    UPDATE pilot_sessions SET revoked_at =
        strftime('%Y-%m-%dT%H:%M:%fZ', 'now')
    WHERE provider = ? AND subject_id = ? AND tenant_id = ?
      AND revoked_at IS NULL
"""


class IdentityRepository:
    def __init__(self, database: SQLiteDatabase | None = None) -> None:
        self.database = database or SQLiteDatabase()

    def save_membership(self, membership: TenantMembership) -> None:
        if not isinstance(membership, TenantMembership):
            raise TypeError("membership must be a TenantMembership.")
        with self.database.connection() as connection:
            tenant = connection.execute(
                "SELECT 1 FROM tenants WHERE tenant_id = ? AND status = 'active'",
                (membership.tenant_id,),
            ).fetchone()
        if tenant is None:
            raise ValueError("Membership tenant must exist and be active.")
        with self.database.transaction() as connection:
            previous = connection.execute(
                """
                SELECT role, active FROM tenant_memberships
                WHERE provider = ? AND subject_id = ? AND tenant_id = ?
                """,
                (
                    membership.provider,
                    membership.subject_id,
                    membership.tenant_id,
                ),
            ).fetchone()
            connection.execute(
                """
                INSERT INTO tenant_memberships
                    (provider, subject_id, tenant_id, role, active, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, strftime('%Y-%m-%dT%H:%M:%fZ', 'now'),
                        strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
                ON CONFLICT(provider, subject_id, tenant_id) DO UPDATE SET
                    role = excluded.role,
                    active = excluded.active,
                    updated_at = excluded.updated_at
                """,
                (
                    membership.provider,
                    membership.subject_id,
                    membership.tenant_id,
                    membership.role.value,
                    int(membership.active),
                ),
            )
            changed = previous is not None and (
                str(previous["role"]) != membership.role.value
                or bool(previous["active"]) != membership.active
            )
            if changed:
                invalidated = connection.execute(
                    MEMBERSHIP_SESSION_INVALIDATION_SQL,
                    (
                        membership.provider,
                        membership.subject_id,
                        membership.tenant_id,
                    ),
                )
                connection.execute(
                    """
                    INSERT INTO authorization_audit_events
                        (event_id, tenant_id, subject_id, provider, action,
                         resource_type, resource_id, outcome, occurred_at,
                         metadata_json)
                    VALUES (?, ?, ?, ?, 'membership_session_invalidate',
                            'pilot_session', ?, 'allowed',
                            strftime('%Y-%m-%dT%H:%M:%fZ', 'now'), ?)
                    """,
                    (
                        str(uuid4()),
                        membership.tenant_id,
                        membership.subject_id,
                        membership.provider,
                        membership.tenant_id,
                        json.dumps(
                            {
                                "affected_sessions": int(invalidated.rowcount),
                                "reason": "membership_role_or_active_change",
                            },
                            sort_keys=True,
                        ),
                    ),
                )

    def get_membership(
        self, *, provider: str, subject_id: str, tenant_id: str
    ) -> TenantMembership | None:
        with self.database.connection() as connection:
            row = connection.execute(
                """
                SELECT provider, subject_id, tenant_id, role, active
                FROM tenant_memberships
                WHERE provider = ? AND subject_id = ? AND tenant_id = ?
                """,
                (provider, subject_id, tenant_id),
            ).fetchone()
        if row is None:
            return None
        return TenantMembership(
            provider=str(row["provider"]),
            subject_id=str(row["subject_id"]),
            tenant_id=str(row["tenant_id"]),
            role=str(row["role"]),
            active=bool(row["active"]),
        )

    def save_audit_event(
        self, event: AuthorizationAuditEvent, *, connection=None
    ) -> None:
        if not isinstance(event, AuthorizationAuditEvent):
            raise TypeError("event must be an AuthorizationAuditEvent.")
        if connection is not None:
            self._insert_audit_event(connection, event)
            return
        with self.database.transaction() as selected_connection:
            self._insert_audit_event(selected_connection, event)

    @staticmethod
    def _insert_audit_event(connection, event: AuthorizationAuditEvent) -> None:
        connection.execute(
            """
            INSERT INTO authorization_audit_events
                (event_id, tenant_id, subject_id, provider, action,
                 resource_type, resource_id, outcome, occurred_at, metadata_json)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                event.event_id,
                event.tenant_id,
                event.subject_id,
                event.provider,
                event.action,
                event.resource_type,
                event.resource_id,
                event.outcome,
                event.occurred_at,
                json.dumps(event.metadata, ensure_ascii=False, sort_keys=True),
            ),
        )

    def list_audit_events(self, *, tenant_id: str) -> list[AuthorizationAuditEvent]:
        with self.database.connection() as connection:
            rows = connection.execute(
                """
                SELECT * FROM authorization_audit_events
                WHERE tenant_id = ? ORDER BY occurred_at, event_id
                """,
                (tenant_id,),
            ).fetchall()
        return [
            AuthorizationAuditEvent(
                event_id=str(row["event_id"]),
                tenant_id=str(row["tenant_id"]),
                subject_id=str(row["subject_id"]),
                provider=str(row["provider"]),
                action=str(row["action"]),
                resource_type=str(row["resource_type"]),
                resource_id=str(row["resource_id"]),
                outcome=str(row["outcome"]),
                occurred_at=str(row["occurred_at"]),
                metadata=json.loads(str(row["metadata_json"])),
            )
            for row in rows
        ]
