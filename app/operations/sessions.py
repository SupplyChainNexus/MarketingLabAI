"""Short-lived, revocable sessions over an external identity adapter."""

from __future__ import annotations

import hashlib
import hmac
import secrets
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Callable
from uuid import uuid4

from app.application import CanonicalApplication
from app.identity import (
    AuthenticatedPrincipal,
    AuthorizationAuditEvent,
    IdentityProviderAdapter,
)

SESSION_RENEW_CAS_SQL = """
    UPDATE pilot_sessions SET revoked_at = ?
    WHERE token_hash = ? AND csrf_hash = ? AND tenant_id = ?
      AND revoked_at IS NULL AND expires_at > ? AND created_at > ?
"""


@dataclass(slots=True, frozen=True)
class PilotSession:
    token: str
    csrf_token: str
    tenant_id: str
    expires_at: str


class PilotSessionProvider(IdentityProviderAdapter):
    """Exchange verified upstream credentials for hashed server-side sessions."""

    def __init__(
        self,
        application: CanonicalApplication,
        upstream: IdentityProviderAdapter,
        secret: str,
        *,
        idle_ttl_seconds: int = 900,
        absolute_ttl_seconds: int = 3600,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        if len(secret) < 32:
            raise ValueError("Session secret must contain at least 32 characters.")
        self.application = application
        self.upstream = upstream
        self.secret = secret.encode()
        if idle_ttl_seconds != 900 or absolute_ttl_seconds != 3600:
            raise ValueError(
                "Private-pilot sessions require 15-minute idle and 60-minute "
                "absolute expiry."
            )
        self.idle_ttl_seconds = idle_ttl_seconds
        self.absolute_ttl_seconds = absolute_ttl_seconds
        self.clock = clock or (lambda: datetime.now(UTC))

    def create(self, credential: str, tenant_id: str) -> PilotSession:
        principal = self.upstream.authenticate(credential)
        self.application.authorize(principal, tenant_id=tenant_id)
        token = secrets.token_urlsafe(32)
        csrf = secrets.token_urlsafe(24)
        created = self._now()
        expires = created + timedelta(seconds=self.idle_ttl_seconds)
        token_hash = self._hash(token)
        csrf_hash = self._hash(csrf)
        with self.application.database.transaction() as connection:
            connection.execute(
                """
                INSERT INTO pilot_sessions (
                    token_hash, csrf_hash, provider, subject_id, tenant_id,
                    created_at, expires_at, revoked_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, NULL)
                """,
                (
                    token_hash,
                    csrf_hash,
                    principal.provider,
                    principal.subject_id,
                    tenant_id,
                    created.isoformat(),
                    expires.isoformat(),
                ),
            )
            self._audit_lifecycle(
                connection=connection,
                provider=principal.provider,
                subject_id=principal.subject_id,
                tenant_id=tenant_id,
                action="session_create",
                metadata={"idle_seconds": 900, "absolute_seconds": 3600},
            )
        return PilotSession(token, csrf, tenant_id, expires.isoformat())

    def authenticate(self, credential: str) -> AuthenticatedPrincipal:
        return self.authenticate_for_tenant(credential)

    def authenticate_for_tenant(
        self, credential: str, tenant_id: str | None = None
    ) -> AuthenticatedPrincipal:
        now = self._now()
        with self.application.database.connection() as connection:
            row = connection.execute(
                """
                SELECT provider, subject_id, tenant_id FROM pilot_sessions
                WHERE token_hash = ? AND revoked_at IS NULL AND expires_at > ?
                  AND created_at > ?
                """,
                (
                    self._hash(credential),
                    now.isoformat(),
                    (now - timedelta(seconds=self.absolute_ttl_seconds)).isoformat(),
                ),
            ).fetchone()
        if row is None:
            raise PermissionError("Session is invalid or expired.")
        session_tenant = str(row["tenant_id"])
        if tenant_id is not None and session_tenant != tenant_id:
            raise PermissionError("Session is not valid for the requested tenant.")
        membership = self.application.identities.get_membership(
            provider=str(row["provider"]),
            subject_id=str(row["subject_id"]),
            tenant_id=session_tenant,
        )
        if membership is None or not membership.active:
            raise PermissionError("Session membership is inactive.")
        return AuthenticatedPrincipal(
            provider=str(row["provider"]), subject_id=str(row["subject_id"])
        )

    def verify_csrf(self, token: str, csrf_token: str, tenant_id: str) -> bool:
        now = self._now()
        with self.application.database.connection() as connection:
            row = connection.execute(
                """
                SELECT csrf_hash FROM pilot_sessions
                WHERE token_hash = ? AND tenant_id = ? AND revoked_at IS NULL
                  AND expires_at > ? AND created_at > ?
                """,
                (
                    self._hash(token),
                    tenant_id,
                    now.isoformat(),
                    (now - timedelta(seconds=self.absolute_ttl_seconds)).isoformat(),
                ),
            ).fetchone()
        return bool(
            row and hmac.compare_digest(str(row["csrf_hash"]), self._hash(csrf_token))
        )

    def renew(self, token: str, csrf_token: str, tenant_id: str) -> PilotSession:
        """Replace one active session while preserving its absolute anchor."""

        now = self._now()
        now_text = now.isoformat()
        absolute_cutoff = (
            now - timedelta(seconds=self.absolute_ttl_seconds)
        ).isoformat()
        token_hash = self._hash(token)
        csrf_hash = self._hash(csrf_token)
        replacement_token = secrets.token_urlsafe(32)
        replacement_csrf = secrets.token_urlsafe(24)
        with self.application.database.connection() as connection:
            session_row = connection.execute(
                """
                SELECT provider, subject_id, tenant_id, created_at
                FROM pilot_sessions
                WHERE token_hash = ? AND csrf_hash = ? AND tenant_id = ?
                  AND revoked_at IS NULL AND expires_at > ? AND created_at > ?
                """,
                (token_hash, csrf_hash, tenant_id, now_text, absolute_cutoff),
            ).fetchone()
        if session_row is None:
            raise PermissionError("Session cannot be renewed.")

        with self.application.database.transaction() as connection:
            membership = connection.execute(
                """
                UPDATE tenant_memberships SET updated_at = updated_at
                WHERE provider = ? AND subject_id = ? AND tenant_id = ?
                  AND active = 1
                """,
                (
                    str(session_row["provider"]),
                    str(session_row["subject_id"]),
                    tenant_id,
                ),
            )
            if int(membership.rowcount) != 1:
                raise PermissionError("Session membership is inactive.")
            rotated = connection.execute(
                SESSION_RENEW_CAS_SQL,
                (
                    now_text,
                    token_hash,
                    csrf_hash,
                    tenant_id,
                    now_text,
                    absolute_cutoff,
                ),
            )
            if int(rotated.rowcount) != 1:
                raise PermissionError("Session cannot be renewed.")
            created_at = datetime.fromisoformat(str(session_row["created_at"]))
            absolute_expiry = created_at + timedelta(seconds=self.absolute_ttl_seconds)
            expires_at = min(
                now + timedelta(seconds=self.idle_ttl_seconds), absolute_expiry
            )
            connection.execute(
                """
                INSERT INTO pilot_sessions (
                    token_hash, csrf_hash, provider, subject_id, tenant_id,
                    created_at, expires_at, revoked_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, NULL)
                """,
                (
                    self._hash(replacement_token),
                    self._hash(replacement_csrf),
                    str(session_row["provider"]),
                    str(session_row["subject_id"]),
                    tenant_id,
                    created_at.isoformat(),
                    expires_at.isoformat(),
                ),
            )
            self._audit_lifecycle(
                connection=connection,
                provider=str(session_row["provider"]),
                subject_id=str(session_row["subject_id"]),
                tenant_id=tenant_id,
                action="session_renew",
                metadata={"rotation": "identifier_and_csrf"},
            )
        return PilotSession(
            replacement_token,
            replacement_csrf,
            tenant_id,
            expires_at.isoformat(),
        )

    def revoke(self, token: str) -> None:
        with self.application.database.transaction() as connection:
            row = connection.execute(
                """
                SELECT provider, subject_id, tenant_id FROM pilot_sessions
                WHERE token_hash = ? AND revoked_at IS NULL
                """,
                (self._hash(token),),
            ).fetchone()
            connection.execute(
                "UPDATE pilot_sessions SET revoked_at = ? WHERE token_hash = ?",
                (self._now().isoformat(), self._hash(token)),
            )
        if row is not None:
            self._audit_revocation(
                provider=str(row["provider"]),
                subject_id=str(row["subject_id"]),
                tenant_id=str(row["tenant_id"]),
                scope="current_session",
            )

    def revoke_all(self, *, provider: str, subject_id: str, tenant_id: str) -> int:
        with self.application.database.transaction() as connection:
            cursor = connection.execute(
                """
                UPDATE pilot_sessions SET revoked_at = ?
                WHERE provider = ? AND subject_id = ? AND tenant_id = ?
                  AND revoked_at IS NULL
                """,
                (self._now().isoformat(), provider, subject_id, tenant_id),
            )
        count = int(cursor.rowcount)
        if count:
            self._audit_revocation(
                provider=provider,
                subject_id=subject_id,
                tenant_id=tenant_id,
                scope="all_identity_tenant_sessions",
            )
        return count

    def purge_expired(self) -> int:
        with self.application.database.transaction() as connection:
            cursor = connection.execute(
                "DELETE FROM pilot_sessions WHERE expires_at <= ?",
                (self._now().isoformat(),),
            )
        return int(cursor.rowcount)

    def _hash(self, value: str) -> str:
        if not isinstance(value, str) or not value:
            return ""
        return hmac.new(self.secret, value.encode(), hashlib.sha256).hexdigest()

    def _now(self) -> datetime:
        selected = self.clock()
        if selected.tzinfo is None:
            raise ValueError("Session clock must return a timezone-aware datetime.")
        return selected.astimezone(UTC)

    def _audit_lifecycle(
        self,
        *,
        connection,
        provider: str,
        subject_id: str,
        tenant_id: str,
        action: str,
        metadata: dict[str, object],
    ) -> None:
        try:
            self.application.identities.save_audit_event(
                AuthorizationAuditEvent(
                    event_id=str(uuid4()),
                    tenant_id=tenant_id,
                    subject_id=subject_id,
                    provider=provider,
                    action=action,
                    resource_type="pilot_session",
                    resource_id=tenant_id,
                    outcome="allowed",
                    metadata=metadata,
                ),
                connection=connection,
            )
        except Exception as error:
            raise PermissionError(
                "Session lifecycle evidence failed; authenticate again."
            ) from error

    def _audit_revocation(
        self, *, provider: str, subject_id: str, tenant_id: str, scope: str
    ) -> None:
        self.application.identities.save_audit_event(
            AuthorizationAuditEvent(
                event_id=str(uuid4()),
                tenant_id=tenant_id,
                subject_id=subject_id,
                provider=provider,
                action="session_revoke",
                resource_type="pilot_session",
                resource_id=tenant_id,
                outcome="allowed",
                metadata={"scope": scope},
            )
        )
