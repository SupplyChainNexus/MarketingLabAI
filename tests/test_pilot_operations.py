"""Operational release controls for MLAI-027.6."""

from __future__ import annotations

import io
import json
import tempfile
import unittest
from pathlib import Path

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
        with self.assertRaisesRegex(PermissionError, "inactive"):
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
