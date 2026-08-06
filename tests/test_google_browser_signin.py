"""Synthetic contract tests for the Google browser sign-in bridge."""

from __future__ import annotations

import io
import json
import unittest
from pathlib import Path

from app.operations.configuration import PilotConfiguration
from app.operations.wsgi import OperationalPilotApplication


class _Sessions:
    class _Application:
        database = None

    application = _Application()


class _Downstream:
    def __call__(self, environ, start_response):
        start_response("404 Not Found", [])
        return [b""]


class GoogleBrowserSignInTests(unittest.TestCase):
    def configuration(self, **changes) -> PilotConfiguration:
        values = {
            "MLAI_ENVIRONMENT": "synthetic-pilot",
            "MLAI_DATABASE_PATH": "database/pilot.db",
            "MLAI_BACKUP_DIRECTORY": "backups",
            "MLAI_PUBLIC_ORIGIN": "http://127.0.0.1:8080",
            "MLAI_TRUST_PROXY_TLS": "false",
            "MLAI_SESSION_SECRET": "s" * 48,
            "MLAI_IDENTITY_PROVIDER": "google-cloud-identity-platform",
            "MLAI_IDENTITY_ADAPTER_FACTORY": (
                "app.identity.google_cloud:create_google_cloud_adapter"
            ),
            "MLAI_PROVIDER_REGISTRY_FACTORY": "deployment.providers:create_registry",
            "MLAI_GOOGLE_CLOUD_PROJECT_ID": "marketinglabai-identity-dev",
            "MLAI_GOOGLE_WEB_API_KEY": "restricted-public-browser-key",
            "MLAI_GOOGLE_OAUTH_CLIENT_ID": "public-client.apps.googleusercontent.com",
            "MLAI_GOOGLE_AUTH_DOMAIN": ("marketinglabai-identity-dev.firebaseapp.com"),
            "MLAI_FOUNDER_INVITATION_HASHES_JSON": "{}",
            "MLAI_ALLOW_REAL_CUSTOMER_DATA": "false",
        }
        values.update(changes)
        return PilotConfiguration.from_environment(values)

    def test_exact_synthetic_loopback_origin_is_allowed(self) -> None:
        configuration = self.configuration()
        self.assertFalse(configuration.secure_cookies)
        for unsafe in (
            "http://localhost:8080",
            "http://127.0.0.2:8080",
            "http://127.0.0.1.evil.test:8080",
        ):
            with self.subTest(origin=unsafe), self.assertRaises(ValueError):
                self.configuration(MLAI_PUBLIC_ORIGIN=unsafe)

    def test_google_browser_values_and_auth_domain_are_required(self) -> None:
        for name in (
            "MLAI_GOOGLE_WEB_API_KEY",
            "MLAI_GOOGLE_OAUTH_CLIENT_ID",
            "MLAI_GOOGLE_AUTH_DOMAIN",
        ):
            with self.subTest(name=name), self.assertRaises(ValueError):
                self.configuration(**{name: ""})
        with self.assertRaises(ValueError):
            self.configuration(MLAI_GOOGLE_AUTH_DOMAIN="attacker.example")

    def test_public_endpoint_exposes_identifiers_but_no_secret(self) -> None:
        app = OperationalPilotApplication(
            _Downstream(), _Sessions(), self.configuration()
        )
        captured = {}

        def start_response(status, headers):
            captured["status"] = status
            captured["headers"] = dict(headers)

        body = b"".join(
            app(
                {
                    "REQUEST_METHOD": "GET",
                    "PATH_INFO": "/v1/pilot/identity/config",
                    "REMOTE_ADDR": "127.0.0.1",
                    "wsgi.input": io.BytesIO(b""),
                },
                start_response,
            )
        )
        payload = json.loads(body)
        self.assertEqual(captured["status"], "200 OK")
        self.assertEqual(captured["headers"]["Cache-Control"], "no-store")
        self.assertEqual(payload["project_id"], "marketinglabai-identity-dev")
        self.assertIn("api_key", payload)
        self.assertIn("oauth_client_id", payload)
        self.assertNotIn("secret", json.dumps(payload).lower())

    def test_workspace_uses_memory_only_token_exchange_and_strict_csp(self) -> None:
        script = Path("app/pilot_workspace/assets/workspace.js").read_text(
            encoding="utf-8"
        )
        host = Path("app/pilot_workspace/wsgi.py").read_text(encoding="utf-8")
        self.assertIn("accounts:signInWithIdp", script)
        self.assertIn("returnSecureToken: true", script)
        self.assertIn('state.idToken = ""', script)
        self.assertNotIn("localStorage", script)
        self.assertNotIn("sessionStorage", script)
        self.assertIn("https://accounts.google.com/gsi/client", host)
        self.assertIn("https://identitytoolkit.googleapis.com", host)


if __name__ == "__main__":
    unittest.main()
