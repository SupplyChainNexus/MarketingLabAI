"""Short-lived, revocable sessions over an external identity adapter."""

from __future__ import annotations

import hashlib
import hmac
import secrets
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from uuid import uuid4

from app.application import CanonicalApplication
from app.identity import (
    AuthenticatedPrincipal,
    AuthorizationAuditEvent,
    IdentityProviderAdapter,
)


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
        ttl_seconds: int = 3600,
    ) -> None:
        if len(secret) < 32:
            raise ValueError("Session secret must contain at least 32 characters.")
        self.application = application
        self.upstream = upstream
        self.secret = secret.encode()
        self.ttl_seconds = ttl_seconds

    def create(self, credential: str, tenant_id: str) -> PilotSession:
        principal = self.upstream.authenticate(credential)
        self.application.authorize(principal, tenant_id=tenant_id)
        token = secrets.token_urlsafe(32)
        csrf = secrets.token_urlsafe(24)
        expires = datetime.now(UTC) + timedelta(seconds=self.ttl_seconds)
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
                    datetime.now(UTC).isoformat(),
                    expires.isoformat(),
                ),
            )
        return PilotSession(token, csrf, tenant_id, expires.isoformat())

    def authenticate(self, credential: str) -> AuthenticatedPrincipal:
        return self.authenticate_for_tenant(credential)

    def authenticate_for_tenant(
        self, credential: str, tenant_id: str | None = None
    ) -> AuthenticatedPrincipal:
        now = datetime.now(UTC).isoformat()
        with self.application.database.connection() as connection:
            row = connection.execute(
                """
                SELECT provider, subject_id, tenant_id FROM pilot_sessions
                WHERE token_hash = ? AND revoked_at IS NULL AND expires_at > ?
                """,
                (self._hash(credential), now),
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
        with self.application.database.connection() as connection:
            row = connection.execute(
                """
                SELECT csrf_hash, tenant_id, expires_at, revoked_at
                FROM pilot_sessions WHERE token_hash = ?
                """,
                (self._hash(token),),
            ).fetchone()
        return bool(
            row
            and row["revoked_at"] is None
            and str(row["tenant_id"]) == tenant_id
            and str(row["expires_at"]) > datetime.now(UTC).isoformat()
            and hmac.compare_digest(str(row["csrf_hash"]), self._hash(csrf_token))
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
                (datetime.now(UTC).isoformat(), self._hash(token)),
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
                (datetime.now(UTC).isoformat(), provider, subject_id, tenant_id),
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
                (datetime.now(UTC).isoformat(),),
            )
        return int(cursor.rowcount)

    def _hash(self, value: str) -> str:
        if not isinstance(value, str) or not value:
            return ""
        return hmac.new(self.secret, value.encode(), hashlib.sha256).hexdigest()

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
