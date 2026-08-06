"""Operational WSGI boundary for health, sessions, rate limits, and logs."""

from __future__ import annotations

import json
from http.cookies import SimpleCookie

from app.operations.configuration import PilotConfiguration
from app.operations.observability import PrivacySafeJsonLogger
from app.operations.rate_limit import RateLimitExceeded, SlidingWindowRateLimiter
from app.operations.release_gate import PilotReleaseGate
from app.operations.sessions import PilotSessionProvider


class OperationalPilotApplication:
    def __init__(
        self,
        application,
        sessions: PilotSessionProvider,
        configuration: PilotConfiguration,
        *,
        logger: PrivacySafeJsonLogger | None = None,
        rate_limiter: SlidingWindowRateLimiter | None = None,
    ) -> None:
        self.application = application
        self.sessions = sessions
        self.configuration = configuration
        self.logger = logger or PrivacySafeJsonLogger()
        self.rate_limiter = rate_limiter or SlidingWindowRateLimiter(
            configuration.rate_limit_requests,
            configuration.rate_limit_window_seconds,
        )

    def __call__(self, environ, start_response):
        path = str(environ.get("PATH_INFO", ""))
        method = str(environ.get("REQUEST_METHOD", "GET")).upper()
        request_id = str(environ.get("HTTP_X_REQUEST_ID", ""))[:64]
        try:
            self.rate_limiter.check(self._client_key(environ))
            if path == "/health/live" and method == "GET":
                return self._json(start_response, 200, {"status": "alive"})
            if path == "/health/ready" and method == "GET":
                report = PilotReleaseGate(
                    self.configuration, self.sessions.application.database
                ).evaluate()
                status = 200 if report.synthetic_pilot_ready else 503
                return self._json(start_response, status, report.to_dict())
            if path == "/v1/pilot/identity/config" and method == "GET":
                return self._json(
                    start_response,
                    200,
                    self.configuration.public_identity_configuration(),
                    [("Cache-Control", "no-store")],
                )
            if path == "/v1/pilot/session" and method == "POST":
                return self._create_session(environ, start_response)
            if path == "/v1/pilot/session" and method == "GET":
                return self._session_status(environ, start_response)
            if (
                path.startswith("/v1/pilot/")
                and path != "/v1/pilot/design-partner/signup"
            ):
                self._bind_session(environ)
            response = self.application(environ, start_response)
            self.logger.emit(
                "pilot_request",
                request_id=request_id,
                method=method,
                path=path,
                outcome="accepted",
            )
            return response
        except RateLimitExceeded:
            return self._json(
                start_response,
                429,
                {
                    "error": {
                        "code": "rate_limited",
                        "message": "Request limit exceeded.",
                    }
                },
            )
        except PermissionError:
            return self._json(
                start_response,
                401,
                {
                    "error": {
                        "code": "unauthenticated",
                        "message": "A valid pilot session is required.",
                    }
                },
            )

    def _create_session(self, environ, start_response):
        authorization = str(environ.get("HTTP_AUTHORIZATION", ""))
        if not authorization.startswith("Bearer "):
            raise PermissionError
        tenant_id = str(environ.get("HTTP_X_TENANT_ID", "")).strip()
        if not tenant_id:
            return self._json(
                start_response,
                400,
                {
                    "error": {
                        "code": "tenant_required",
                        "message": "X-Tenant-ID is required.",
                    }
                },
            )
        session = self.sessions.create(authorization[7:].strip(), tenant_id)
        body = {
            "tenant_id": tenant_id,
            "csrf_token": session.csrf_token,
            "expires_at": session.expires_at,
        }
        secure = "; Secure" if self.configuration.secure_cookies else ""
        session_cookie = (
            f"mlai_session={session.token}; Path=/; HttpOnly{secure}; "
            "SameSite=Strict"
        )
        csrf_cookie = f"mlai_csrf={session.csrf_token}; Path=/{secure}; SameSite=Strict"
        return self._json(
            start_response,
            201,
            body,
            [
                ("Set-Cookie", session_cookie),
                ("Set-Cookie", csrf_cookie),
                ("Cache-Control", "no-store"),
            ],
        )

    def _session_status(self, environ, start_response):
        token = self._cookie(environ)
        self.sessions.authenticate(token)
        tenant_id = str(environ.get("HTTP_X_TENANT_ID", "")).strip()
        csrf = str(environ.get("HTTP_X_CSRF_TOKEN", ""))
        valid = self.sessions.verify_csrf(token, csrf, tenant_id)
        return self._json(
            start_response, 200, {"authenticated": True, "csrf_valid": valid}
        )

    def _bind_session(self, environ) -> None:
        token = self._cookie(environ)
        self.sessions.authenticate(token)
        tenant_id = str(environ.get("HTTP_X_TENANT_ID", "")).strip()
        if str(environ.get("REQUEST_METHOD", "GET")).upper() != "GET":
            csrf = str(environ.get("HTTP_X_CSRF_TOKEN", ""))
            if not self.sessions.verify_csrf(token, csrf, tenant_id):
                raise PermissionError
        environ["HTTP_AUTHORIZATION"] = f"Bearer {token}"

    @staticmethod
    def _cookie(environ) -> str:
        cookie = SimpleCookie()
        cookie.load(str(environ.get("HTTP_COOKIE", "")))
        morsel = cookie.get("mlai_session")
        if morsel is None:
            raise PermissionError
        return morsel.value

    @staticmethod
    def _client_key(environ) -> str:
        return str(environ.get("REMOTE_ADDR", "unknown"))[:128]

    @staticmethod
    def _json(start_response, status, payload, extra_headers=None):
        body = json.dumps(payload, sort_keys=True).encode()
        phrase = {
            200: "OK",
            201: "Created",
            400: "Bad Request",
            401: "Unauthorized",
            429: "Too Many Requests",
            503: "Service Unavailable",
        }.get(status, "Error")
        headers = [
            ("Content-Type", "application/json; charset=utf-8"),
            ("Content-Length", str(len(body))),
            ("X-Content-Type-Options", "nosniff"),
        ]
        headers.extend(extra_headers or [])
        start_response(f"{status} {phrase}", headers)
        return [body]
