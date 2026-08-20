"""Operational release controls for MLAI-027.6."""

from __future__ import annotations

import io
import json
import sqlite3
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta
from pathlib import Path
from threading import Barrier
from unittest.mock import patch

from app.application import CanonicalApplication
from app.database.connection import SQLiteDatabase
from app.identity import (
    AuthenticatedPrincipal,
    IdentityProviderAdapter,
    TenantMembership,
    TenantRole,
)
from app.operations import (
    OperationalSignalMonitor,
    PilotConfiguration,
    PilotReleaseGate,
    PilotSessionProvider,
    PrivacySafeJsonLogger,
    RateLimitExceeded,
    SlidingWindowRateLimiter,
    SQLiteRecoveryService,
)
from app.operations.wsgi import OperationalPilotApplication
from app.tenants.models import Tenant


class TrustedTestIdentity(IdentityProviderAdapter):
    def authenticate(self, credential: str) -> AuthenticatedPrincipal:
        if credential != "upstream-proof":
            raise PermissionError("Invalid upstream proof.")
        return AuthenticatedPrincipal(subject_id="operator-one", provider="oidc-test")


class StubWsgiApplication:
    def __call__(self, environ, start_response):
        body = json.dumps(
            {"authorization": environ.get("HTTP_AUTHORIZATION", "")}
        ).encode()
        start_response("200 OK", [("Content-Length", str(len(body)))])
        return [body]


class PilotOperationsTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        root = Path(self.temp.name)
        self.database = SQLiteDatabase(root / "pilot.sqlite3")
        self.application = CanonicalApplication.build(self.database)
        self.application.tenants.save(Tenant(tenant_id="tenant-one", name="Pilot"))
        self.application.identities.save_membership(
            TenantMembership(
                subject_id="operator-one",
                provider="oidc-test",
                tenant_id="tenant-one",
                role=TenantRole.ADMIN,
            )
        )
        self.config = PilotConfiguration.from_environment(
            {
                "MLAI_ENVIRONMENT": "synthetic-pilot",
                "MLAI_DATABASE_PATH": str(root / "pilot.sqlite3"),
                "MLAI_BACKUP_DIRECTORY": str(root / "backups"),
                "MLAI_PUBLIC_ORIGIN": "https://pilot.example.test",
                "MLAI_TRUST_PROXY_TLS": "false",
                "MLAI_SESSION_SECRET": "s" * 48,
                "MLAI_IDENTITY_PROVIDER": "oidc-test",
                "MLAI_IDENTITY_ADAPTER_FACTORY": "deployment.identity:create_adapter",
                "MLAI_PROVIDER_REGISTRY_FACTORY": "deployment.providers:create_registry",
                "MLAI_FOUNDER_INVITATION_HASHES_JSON": json.dumps(
                    {
                        "strand-auto-parts-pilot": "a" * 64,
                        "velani-wholesale-pilot": "b" * 64,
                    }
                ),
                "MLAI_ALLOW_REAL_CUSTOMER_DATA": "false",
            }
        )
        self.sessions = PilotSessionProvider(
            self.application, TrustedTestIdentity(), "s" * 48
        )

    def tearDown(self) -> None:
        self.temp.cleanup()

    def test_configuration_requires_tls_secret_and_customer_data_freeze(self):
        values = {
            "MLAI_ENVIRONMENT": "pilot",
            "MLAI_DATABASE_PATH": "pilot.db",
            "MLAI_BACKUP_DIRECTORY": "backups",
            "MLAI_PUBLIC_ORIGIN": "http://localhost",
            "MLAI_TRUST_PROXY_TLS": "false",
            "MLAI_SESSION_SECRET": "short",
            "MLAI_IDENTITY_PROVIDER": "oidc",
            "MLAI_IDENTITY_ADAPTER_FACTORY": "deployment.identity:create_adapter",
            "MLAI_PROVIDER_REGISTRY_FACTORY": "deployment.providers:create_registry",
            "MLAI_ALLOW_REAL_CUSTOMER_DATA": "true",
        }
        with self.assertRaises(ValueError):
            PilotConfiguration.from_environment(values)

    def test_development_and_synthetic_rehearsal_are_authorized(self):
        summary = self.config.public_summary()
        self.assertTrue(summary["engineering_development_authorized"])
        self.assertTrue(summary["synthetic_rehearsal_authorized"])
        self.assertFalse(summary["real_customer_data_allowed"])
        self.assertEqual(summary["real_data_activation_status"], "frozen")

    def test_session_is_hashed_revocable_tenant_bound_and_csrf_protected(self):
        session = self.sessions.create("upstream-proof", "tenant-one")
        principal = self.sessions.authenticate(session.token)
        self.assertEqual("operator-one", principal.subject_id)
        self.assertTrue(
            self.sessions.verify_csrf(session.token, session.csrf_token, "tenant-one")
        )
        with self.database.connection() as connection:
            row = connection.execute(
                "SELECT token_hash, csrf_hash FROM pilot_sessions"
            ).fetchone()
        self.assertNotIn(session.token, tuple(row))
        self.assertNotIn(session.csrf_token, tuple(row))
        self.sessions.revoke(session.token)
        with self.assertRaises(PermissionError):
            self.sessions.authenticate(session.token)
        events = self.application.identities.list_audit_events(tenant_id="tenant-one")
        self.assertEqual(events[-1].action, "session_revoke")

    def test_private_pilot_session_limits_are_fixed(self):
        self.assertEqual(self.config.session_idle_ttl_seconds, 900)
        self.assertEqual(self.config.session_absolute_ttl_seconds, 3600)
        values = self._configuration_values()
        values["MLAI_SESSION_TTL_SECONDS"] = "3599"
        with self.assertRaisesRegex(ValueError, "must be 3600"):
            PilotConfiguration.from_environment(values)

    def test_renewal_rotates_identifier_and_csrf_and_preserves_anchor(self):
        now = [datetime(2026, 8, 20, 10, 0, tzinfo=UTC)]
        sessions = PilotSessionProvider(
            self.application,
            TrustedTestIdentity(),
            "s" * 48,
            clock=lambda: now[0],
        )
        original = sessions.create("upstream-proof", "tenant-one")
        now[0] += timedelta(minutes=14)
        successor = sessions.renew(original.token, original.csrf_token, "tenant-one")
        self.assertNotEqual(original.token, successor.token)
        self.assertNotEqual(original.csrf_token, successor.csrf_token)
        with self.assertRaises(PermissionError):
            sessions.authenticate(original.token)
        with self.database.connection() as connection:
            rows = connection.execute(
                "SELECT created_at, expires_at, revoked_at FROM pilot_sessions "
                "ORDER BY expires_at"
            ).fetchall()
        self.assertEqual(rows[0]["created_at"], rows[1]["created_at"])
        self.assertIsNotNone(rows[0]["revoked_at"])
        self.assertEqual(
            datetime.fromisoformat(str(rows[1]["expires_at"])),
            now[0] + timedelta(minutes=15),
        )

    def test_idle_expiry_blocks_use_and_renewal_at_fifteen_minutes(self):
        now = [datetime(2026, 8, 20, 10, 0, tzinfo=UTC)]
        sessions = PilotSessionProvider(
            self.application,
            TrustedTestIdentity(),
            "s" * 48,
            clock=lambda: now[0],
        )
        session = sessions.create("upstream-proof", "tenant-one")
        now[0] += timedelta(minutes=15)
        with self.assertRaises(PermissionError):
            sessions.authenticate(session.token)
        with self.assertRaises(PermissionError):
            sessions.renew(session.token, session.csrf_token, "tenant-one")

    def test_failed_csrf_renewal_does_not_replace_authoritative_session(self):
        session = self.sessions.create("upstream-proof", "tenant-one")
        with self.assertRaises(PermissionError):
            self.sessions.renew(session.token, "wrong-csrf", "tenant-one")
        principal = self.sessions.authenticate(session.token)
        self.assertEqual(principal.subject_id, "operator-one")

    def test_tenant_mismatched_session_cannot_renew(self):
        session = self.sessions.create("upstream-proof", "tenant-one")
        with self.assertRaises(PermissionError):
            self.sessions.renew(session.token, session.csrf_token, "tenant-two")
        self.assertEqual(
            self.sessions.authenticate(session.token).subject_id, "operator-one"
        )

    def test_explicitly_revoked_session_cannot_renew(self):
        session = self.sessions.create("upstream-proof", "tenant-one")
        self.sessions.revoke(session.token)
        with self.assertRaises(PermissionError):
            self.sessions.renew(session.token, session.csrf_token, "tenant-one")

    def test_successor_insert_failure_rolls_back_predecessor_revocation(self):
        session = self.sessions.create("upstream-proof", "tenant-one")
        with (
            patch(
                "app.operations.sessions.secrets.token_urlsafe",
                side_effect=(session.token, "replacement-csrf"),
            ),
            self.assertRaises(sqlite3.IntegrityError),
        ):
            self.sessions.renew(session.token, session.csrf_token, "tenant-one")
        self.assertEqual(
            self.sessions.authenticate(session.token).subject_id, "operator-one"
        )
        with self.database.connection() as connection:
            count = connection.execute(
                "SELECT COUNT(*) FROM pilot_sessions"
            ).fetchone()[0]
        self.assertEqual(count, 1)

    def test_renewal_caps_idle_deadline_at_original_absolute_expiry(self):
        now = [datetime(2026, 8, 20, 10, 0, tzinfo=UTC)]
        sessions = PilotSessionProvider(
            self.application,
            TrustedTestIdentity(),
            "s" * 48,
            clock=lambda: now[0],
        )
        current = sessions.create("upstream-proof", "tenant-one")
        for minute in (14, 28, 42, 55):
            now[0] = datetime(2026, 8, 20, 10, minute, tzinfo=UTC)
            current = sessions.renew(current.token, current.csrf_token, "tenant-one")
        self.assertEqual(
            datetime.fromisoformat(current.expires_at),
            datetime(2026, 8, 20, 11, 0, tzinfo=UTC),
        )
        now[0] = datetime(2026, 8, 20, 11, 0, tzinfo=UTC)
        with self.assertRaises(PermissionError):
            sessions.authenticate(current.token)
        with self.assertRaises(PermissionError):
            sessions.renew(current.token, current.csrf_token, "tenant-one")

    def test_competing_renewals_allow_at_most_one_success(self):
        session = self.sessions.create("upstream-proof", "tenant-one")
        barrier = Barrier(2)

        def attempt():
            barrier.wait()
            try:
                return self.sessions.renew(
                    session.token, session.csrf_token, "tenant-one"
                )
            except PermissionError:
                return None

        with ThreadPoolExecutor(max_workers=2) as executor:
            results = list(executor.map(lambda _: attempt(), range(2)))
        winners = [result for result in results if result is not None]
        self.assertEqual(len(winners), 1)
        with self.assertRaises(PermissionError):
            self.sessions.authenticate(session.token)

    def test_membership_role_or_active_change_invalidates_sessions(self):
        role_session = self.sessions.create("upstream-proof", "tenant-one")
        self.application.identities.save_membership(
            TenantMembership(
                subject_id="operator-one",
                provider="oidc-test",
                tenant_id="tenant-one",
                role=TenantRole.MARKETER,
            )
        )
        with self.assertRaises(PermissionError):
            self.sessions.authenticate(role_session.token)
        with self.assertRaises(PermissionError):
            self.sessions.renew(
                role_session.token, role_session.csrf_token, "tenant-one"
            )

        active_session = self.sessions.create("upstream-proof", "tenant-one")
        self.application.identities.save_membership(
            TenantMembership(
                subject_id="operator-one",
                provider="oidc-test",
                tenant_id="tenant-one",
                role=TenantRole.MARKETER,
                active=False,
            )
        )
        with self.assertRaises(PermissionError):
            self.sessions.authenticate(active_session.token)

    def test_membership_change_invalidates_successor_when_renewal_commits_first(self):
        original = self.sessions.create("upstream-proof", "tenant-one")
        successor = self.sessions.renew(
            original.token, original.csrf_token, "tenant-one"
        )
        self.application.identities.save_membership(
            TenantMembership(
                subject_id="operator-one",
                provider="oidc-test",
                tenant_id="tenant-one",
                role=TenantRole.MARKETER,
            )
        )
        with self.assertRaises(PermissionError):
            self.sessions.authenticate(successor.token)

    def test_membership_invalidation_audit_contains_only_safe_metadata(self):
        session = self.sessions.create("upstream-proof", "tenant-one")
        self.application.identities.save_membership(
            TenantMembership(
                subject_id="operator-one",
                provider="oidc-test",
                tenant_id="tenant-one",
                role=TenantRole.MARKETER,
            )
        )
        events = self.application.identities.list_audit_events(tenant_id="tenant-one")
        event = next(
            item for item in events if item.action == "membership_session_invalidate"
        )
        evidence = json.dumps(event.metadata, sort_keys=True)
        self.assertEqual(
            event.metadata,
            {
                "affected_sessions": 1,
                "reason": "membership_role_or_active_change",
            },
        )
        for prohibited in (
            session.token,
            session.csrf_token,
            self.sessions._hash(session.token),
            self.sessions._hash(session.csrf_token),
        ):
            self.assertNotIn(prohibited, evidence)

    def test_renewal_audit_contains_no_session_or_csrf_material(self):
        session = self.sessions.create("upstream-proof", "tenant-one")
        successor = self.sessions.renew(session.token, session.csrf_token, "tenant-one")
        events = self.application.identities.list_audit_events(tenant_id="tenant-one")
        evidence = json.dumps(events[-1].metadata, sort_keys=True)
        for prohibited in (
            session.token,
            session.csrf_token,
            successor.token,
            successor.csrf_token,
            self.sessions._hash(session.token),
            self.sessions._hash(session.csrf_token),
        ):
            self.assertNotIn(prohibited, evidence)

    def test_creation_audit_failure_leaves_no_active_session(self):
        original = self.application.identities.save_audit_event

        def fail_lifecycle_audit(event, **kwargs):
            if event.action == "session_create":
                raise RuntimeError("synthetic lifecycle audit failure")
            return original(event, **kwargs)

        self.application.identities.save_audit_event = fail_lifecycle_audit
        try:
            with self.assertRaisesRegex(PermissionError, "authenticate again"):
                self.sessions.create("upstream-proof", "tenant-one")
        finally:
            self.application.identities.save_audit_event = original
        with self.database.connection() as connection:
            count = connection.execute(
                "SELECT COUNT(*) FROM pilot_sessions WHERE revoked_at IS NULL"
            ).fetchone()[0]
        self.assertEqual(count, 0)

    def test_renewal_audit_failure_rolls_back_to_active_predecessor(self):
        session = self.sessions.create("upstream-proof", "tenant-one")
        original = self.application.identities.save_audit_event

        def fail_audit(*_args, **_kwargs):
            raise RuntimeError("synthetic audit failure")

        self.application.identities.save_audit_event = fail_audit
        try:
            with self.assertRaisesRegex(PermissionError, "authenticate again"):
                self.sessions.renew(session.token, session.csrf_token, "tenant-one")
        finally:
            self.application.identities.save_audit_event = original
        self.assertEqual(
            self.sessions.authenticate(session.token).subject_id, "operator-one"
        )
        with self.database.connection() as connection:
            rows = connection.execute(
                "SELECT token_hash, revoked_at FROM pilot_sessions"
            ).fetchall()
        self.assertEqual(len(rows), 1)
        self.assertIsNone(rows[0]["revoked_at"])

    def test_session_rechecks_tenant_and_active_membership(self):
        session = self.sessions.create("upstream-proof", "tenant-one")
        with self.assertRaisesRegex(PermissionError, "requested tenant"):
            self.sessions.authenticate_for_tenant(session.token, "tenant-two")
        self.application.identities.save_membership(
            TenantMembership(
                subject_id="operator-one",
                provider="oidc-test",
                tenant_id="tenant-one",
                role=TenantRole.ADMIN,
                active=False,
            )
        )
        with self.assertRaisesRegex(
            PermissionError, r"Session is invalid or expired\."
        ):
            self.sessions.authenticate(session.token)

    def test_bulk_revocation_and_expired_session_purge(self):
        first = self.sessions.create("upstream-proof", "tenant-one")
        second = self.sessions.create("upstream-proof", "tenant-one")
        self.assertEqual(
            self.sessions.revoke_all(
                provider="oidc-test",
                subject_id="operator-one",
                tenant_id="tenant-one",
            ),
            2,
        )
        for session in (first, second):
            with self.assertRaises(PermissionError):
                self.sessions.authenticate(session.token)
        with self.database.transaction() as connection:
            connection.execute(
                "UPDATE pilot_sessions SET expires_at = '2000-01-01T00:00:00+00:00'"
            )
        self.assertEqual(self.sessions.purge_expired(), 2)

    def test_backup_restore_is_verified_and_source_remains_unchanged(self):
        recovery = SQLiteRecoveryService(
            self.database, Path(self.temp.name) / "backups"
        )
        evidence = recovery.create_backup("release.sqlite3")
        moved_backup = evidence.path.with_name("release-moved.sqlite3")
        evidence.path.rename(moved_backup)
        restored = recovery.restore_to(
            moved_backup, Path(self.temp.name) / "restore" / "pilot.sqlite3"
        )
        self.assertEqual("ok", evidence.integrity)
        self.assertEqual("ok", SQLiteDatabase(restored).integrity_check())
        self.assertTrue(self.database.database_path.exists())

    def test_logger_redacts_secrets_prompts_and_customer_content(self):
        lines: list[str] = []
        line = PrivacySafeJsonLogger(lines.append).emit(
            "request",
            token="secret-token",
            nested={"prompt": "private", "tenant_id": "tenant-one"},
        )
        self.assertNotIn("secret-token", line)
        self.assertNotIn("private", line)
        self.assertIn("tenant-one", line)

    def test_operational_monitor_alerts_without_customer_content(self):
        monitor = OperationalSignalMonitor(
            {name: 2 for name in OperationalSignalMonitor.SIGNALS}
        )
        monitor.observe("authentication_failure")
        self.assertFalse(monitor.snapshot()["authentication_failure"]["alerting"])
        monitor.observe("authentication_failure")
        snapshot = monitor.snapshot()
        self.assertTrue(snapshot["authentication_failure"]["alerting"])
        self.assertNotIn("tenant", json.dumps(snapshot))

    def test_rate_limit_is_deterministic(self):
        now = [10.0]
        limiter = SlidingWindowRateLimiter(2, 60, clock=lambda: now[0])
        limiter.check("client")
        limiter.check("client")
        with self.assertRaises(RateLimitExceeded):
            limiter.check("client")
        now[0] = 71.0
        limiter.check("client")

    def test_release_gate_authorizes_rehearsal_but_freezes_real_data(self):
        report = PilotReleaseGate(self.config, self.database).evaluate()
        payload = report.to_dict()
        self.assertTrue(report.synthetic_pilot_ready)
        self.assertTrue(payload["engineering_development_authorized"])
        self.assertTrue(payload["synthetic_rehearsal_authorized"])
        self.assertFalse(report.private_customer_pilot_authorized)
        self.assertFalse(payload["real_data_activation_authorized"])
        self.assertEqual(
            "real_data_activation_frozen", payload["customer_pilot_status"]
        )

    def test_operational_wsgi_issues_secure_session_and_protects_api(self):
        runtime = OperationalPilotApplication(
            StubWsgiApplication(),
            self.sessions,
            self.config,
            logger=PrivacySafeJsonLogger(lambda _: None),
        )
        headers: list[tuple[str, str]] = []

        def start_response(status, selected_headers):
            headers.extend(selected_headers)
            self.assertEqual("201 Created", status)

        body = b"".join(
            runtime(
                {
                    "REQUEST_METHOD": "POST",
                    "PATH_INFO": "/v1/pilot/session",
                    "HTTP_AUTHORIZATION": "Bearer upstream-proof",
                    "HTTP_X_TENANT_ID": "tenant-one",
                    "REMOTE_ADDR": "127.0.0.1",
                    "wsgi.input": io.BytesIO(b""),
                },
                start_response,
            )
        )
        payload = json.loads(body)
        cookies = [value for name, value in headers if name == "Set-Cookie"]
        self.assertEqual(2, len(cookies))
        self.assertIn("HttpOnly", cookies[0])
        self.assertIn("Secure", cookies[0])
        self.assertIn("csrf_token", payload)
        response_headers = dict(headers)
        self.assertEqual(response_headers["Cache-Control"], "no-store")
        self.assertEqual(response_headers["X-Frame-Options"], "DENY")

    def test_logout_requires_csrf_revokes_session_and_expires_cookies(self):
        session = self.sessions.create("upstream-proof", "tenant-one")
        runtime = OperationalPilotApplication(
            StubWsgiApplication(),
            self.sessions,
            self.config,
            logger=PrivacySafeJsonLogger(lambda _: None),
        )
        captured = {}

        def start_response(status, headers):
            captured["status"] = status
            captured["headers"] = headers

        payload = json.loads(
            b"".join(
                runtime(
                    {
                        "REQUEST_METHOD": "DELETE",
                        "PATH_INFO": "/v1/pilot/session",
                        "HTTP_COOKIE": f"mlai_session={session.token}",
                        "HTTP_X_TENANT_ID": "tenant-one",
                        "HTTP_X_CSRF_TOKEN": session.csrf_token,
                        "REMOTE_ADDR": "127.0.0.1",
                        "wsgi.input": io.BytesIO(b""),
                    },
                    start_response,
                )
            )
        )
        self.assertEqual(captured["status"], "200 OK")
        self.assertTrue(payload["revoked"])
        cookies = [value for name, value in captured["headers"] if name == "Set-Cookie"]
        self.assertEqual(len(cookies), 2)
        self.assertTrue(all("Max-Age=0" in value for value in cookies))
        with self.assertRaises(PermissionError):
            self.sessions.authenticate(session.token)

    def test_put_session_renews_with_csrf_and_rotates_cookies(self):
        session = self.sessions.create("upstream-proof", "tenant-one")
        runtime = OperationalPilotApplication(
            StubWsgiApplication(),
            self.sessions,
            self.config,
            logger=PrivacySafeJsonLogger(lambda _: None),
        )
        captured = {}

        def start_response(status, headers):
            captured["status"] = status
            captured["headers"] = headers

        payload = json.loads(
            b"".join(
                runtime(
                    {
                        "REQUEST_METHOD": "PUT",
                        "PATH_INFO": "/v1/pilot/session",
                        "HTTP_COOKIE": f"mlai_session={session.token}",
                        "HTTP_X_TENANT_ID": "tenant-one",
                        "HTTP_X_CSRF_TOKEN": session.csrf_token,
                        "REMOTE_ADDR": "127.0.0.1",
                        "wsgi.input": io.BytesIO(b""),
                    },
                    start_response,
                )
            )
        )
        self.assertEqual(captured["status"], "200 OK")
        self.assertNotEqual(payload["csrf_token"], session.csrf_token)
        cookies = [value for name, value in captured["headers"] if name == "Set-Cookie"]
        self.assertEqual(len(cookies), 2)
        self.assertNotIn(session.token, cookies[0])
        with self.assertRaises(PermissionError):
            self.sessions.authenticate(session.token)

    def test_renewal_audit_failure_returns_no_replacement_cookie(self):
        session = self.sessions.create("upstream-proof", "tenant-one")
        runtime = OperationalPilotApplication(
            StubWsgiApplication(),
            self.sessions,
            self.config,
            logger=PrivacySafeJsonLogger(lambda _: None),
        )
        captured = {}
        original = self.application.identities.save_audit_event

        def fail_audit(*_args, **_kwargs):
            raise RuntimeError("synthetic audit failure")

        def start_response(status, headers):
            captured["status"] = status
            captured["headers"] = headers

        self.application.identities.save_audit_event = fail_audit
        try:
            b"".join(
                runtime(
                    {
                        "REQUEST_METHOD": "PUT",
                        "PATH_INFO": "/v1/pilot/session",
                        "HTTP_COOKIE": f"mlai_session={session.token}",
                        "HTTP_X_TENANT_ID": "tenant-one",
                        "HTTP_X_CSRF_TOKEN": session.csrf_token,
                        "REMOTE_ADDR": "127.0.0.1",
                        "wsgi.input": io.BytesIO(b""),
                    },
                    start_response,
                )
            )
        finally:
            self.application.identities.save_audit_event = original
        self.assertEqual(captured["status"], "401 Unauthorized")
        self.assertFalse(
            any(name == "Set-Cookie" for name, _value in captured["headers"])
        )
        self.assertEqual(
            self.sessions.authenticate(session.token).subject_id, "operator-one"
        )

    def _configuration_values(self) -> dict[str, str]:
        return {
            "MLAI_ENVIRONMENT": "synthetic-pilot",
            "MLAI_DATABASE_PATH": str(Path(self.temp.name) / "pilot.sqlite3"),
            "MLAI_BACKUP_DIRECTORY": str(Path(self.temp.name) / "backups"),
            "MLAI_PUBLIC_ORIGIN": "https://pilot.example.test",
            "MLAI_TRUST_PROXY_TLS": "false",
            "MLAI_SESSION_SECRET": "s" * 48,
            "MLAI_IDENTITY_PROVIDER": "oidc-test",
            "MLAI_IDENTITY_ADAPTER_FACTORY": "deployment.identity:create_adapter",
            "MLAI_PROVIDER_REGISTRY_FACTORY": "deployment.providers:create_registry",
            "MLAI_FOUNDER_INVITATION_HASHES_JSON": "{}",
            "MLAI_ALLOW_REAL_CUSTOMER_DATA": "false",
        }

    def test_request_body_limit_rejects_before_downstream(self):
        runtime = OperationalPilotApplication(
            StubWsgiApplication(),
            self.sessions,
            self.config,
            logger=PrivacySafeJsonLogger(lambda _: None),
        )
        captured = {}

        def start_response(status, headers):
            captured["status"] = status

        payload = json.loads(
            b"".join(
                runtime(
                    {
                        "REQUEST_METHOD": "POST",
                        "PATH_INFO": "/v1/pilot/context",
                        "CONTENT_LENGTH": str(self.config.max_request_bytes + 1),
                        "REMOTE_ADDR": "127.0.0.1",
                        "wsgi.input": io.BytesIO(b""),
                    },
                    start_response,
                )
            )
        )
        self.assertEqual(captured["status"], "413 Content Too Large")
        self.assertEqual(payload["error"]["code"], "request_too_large")

    def test_migration_thirteen_is_idempotent(self):
        self.database.initialise()
        self.database.initialise()
        with self.database.connection() as connection:
            count = connection.execute(
                "SELECT COUNT(*) FROM schema_migrations WHERE version = 13"
            ).fetchone()[0]
        self.assertEqual(1, count)


if __name__ == "__main__":
    unittest.main()
