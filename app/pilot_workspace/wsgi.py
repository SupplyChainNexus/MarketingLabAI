"""Framework-neutral WSGI host for the pilot workspace and JSON API."""

from __future__ import annotations

from pathlib import Path

from app.pilot_api import PilotApiService, PilotWsgiApplication


class PilotWorkspaceApplication:
    """Serve the guided workspace and delegate operations to the pilot API."""

    _ASSETS = Path(__file__).with_name("assets")
    _ROUTES = {
        "/pilot": ("index.html", "text/html; charset=utf-8"),
        "/pilot/workspace.css": ("workspace.css", "text/css; charset=utf-8"),
        "/pilot/workspace.js": (
            "workspace.js",
            "application/javascript; charset=utf-8",
        ),
    }

    def __init__(self, service: PilotApiService) -> None:
        if not isinstance(service, PilotApiService):
            raise TypeError("service must be a PilotApiService.")
        self.api = PilotWsgiApplication(service)

    def __call__(self, environ, start_response):
        method = str(environ.get("REQUEST_METHOD", "GET")).upper()
        path = str(environ.get("PATH_INFO", ""))
        if method == "GET" and path in self._ROUTES:
            filename, content_type = self._ROUTES[path]
            body = (self._ASSETS / filename).read_bytes()
            start_response(
                "200 OK",
                [
                    ("Content-Type", content_type),
                    ("Content-Length", str(len(body))),
                    ("Cache-Control", "no-store"),
                    ("X-Content-Type-Options", "nosniff"),
                    ("Content-Security-Policy", self._content_security_policy()),
                ],
            )
            return [body]
        return self.api(environ, start_response)

    @staticmethod
    def _content_security_policy() -> str:
        return (
            "default-src 'self'; script-src 'self' https://accounts.google.com/gsi/client; "
            "style-src 'self'; connect-src 'self' https://identitytoolkit.googleapis.com; "
            "frame-src https://accounts.google.com; img-src 'self' data:; "
            "object-src 'none'; base-uri 'none'; frame-ancestors 'none'; "
            "form-action 'self'"
        )
