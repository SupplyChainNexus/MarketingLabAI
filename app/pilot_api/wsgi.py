"""Minimal WSGI JSON transport for the secure pilot API contract."""

import json
import re

from app.pilot_api.contracts import (
    ApprovalRequest,
    ContextRequest,
    ExportRequest,
    GenerationRequest,
)
from app.pilot_api.service import PilotApiError, PilotApiService


class PilotWsgiApplication:
    def __init__(self, service: PilotApiService) -> None:
        if not isinstance(service, PilotApiService):
            raise TypeError("service must be a PilotApiService.")
        self.service = service

    def __call__(self, environ, start_response):
        try:
            response = self._dispatch(environ)
            status, payload = response.status, {
                "data": response.data,
                "replayed": response.replayed,
            }
        except PilotApiError as error:
            status = error.status
            payload = {"error": {"code": error.code, "message": error.message}}
        except (TypeError, ValueError, json.JSONDecodeError) as error:
            status, payload = 400, {
                "error": {"code": "invalid_request", "message": str(error)}
            }
        body = json.dumps(payload, ensure_ascii=False, sort_keys=True).encode()
        phrase = {
            200: "OK",
            201: "Created",
            400: "Bad Request",
            401: "Unauthorized",
            403: "Forbidden",
            404: "Not Found",
            409: "Conflict",
        }.get(status, "Error")
        start_response(
            f"{status} {phrase}",
            [
                ("Content-Type", "application/json; charset=utf-8"),
                ("Content-Length", str(len(body))),
            ],
        )
        return [body]

    def _dispatch(self, environ):
        if environ.get("REQUEST_METHOD") != "POST":
            raise PilotApiError(404, "not_found", "Endpoint was not found.")
        path = str(environ.get("PATH_INFO", ""))
        credential = self._bearer(environ.get("HTTP_AUTHORIZATION", ""))
        tenant_id = str(environ.get("HTTP_X_TENANT_ID", "")).strip()
        if not tenant_id:
            raise PilotApiError(400, "tenant_required", "X-Tenant-ID is required.")
        body, key = self._json_body(environ), str(
            environ.get("HTTP_IDEMPOTENCY_KEY", "")
        )
        common = {"credential": credential, "tenant_id": tenant_id}
        if path == "/v1/pilot/context":
            return self.service.context(request=ContextRequest(**body), **common)
        if path == "/v1/pilot/generate":
            return self.service.generate(
                request=GenerationRequest(**body), idempotency_key=key, **common
            )
        match = re.fullmatch(r"/v1/pilot/campaign-plans/([^/]+)/approve", path)
        if match:
            return self.service.approve_campaign_plan(
                campaign_id=match.group(1),
                request=ApprovalRequest(**body),
                idempotency_key=key,
                **common,
            )
        match = re.fullmatch(r"/v1/pilot/marketing-briefs/([^/]+)/approve", path)
        if match:
            return self.service.approve_marketing_brief(
                brief_id=match.group(1),
                request=ApprovalRequest(**body),
                idempotency_key=key,
                **common,
            )
        if path == "/v1/pilot/exports/authorize":
            return self.service.authorize_export(
                request=ExportRequest(**body), idempotency_key=key, **common
            )
        raise PilotApiError(404, "not_found", "Endpoint was not found.")

    @staticmethod
    def _bearer(value: str) -> str:
        if not isinstance(value, str) or not value.startswith("Bearer "):
            raise PilotApiError(401, "unauthenticated", "Bearer credential required.")
        credential = value[7:].strip()
        if not credential:
            raise PilotApiError(401, "unauthenticated", "Bearer credential required.")
        return credential

    @staticmethod
    def _json_body(environ) -> dict:
        length = int(str(environ.get("CONTENT_LENGTH", "0") or "0"))
        raw = environ["wsgi.input"].read(length) if length else b"{}"
        value = json.loads(raw.decode())
        if not isinstance(value, dict):
            raise ValueError("JSON body must be an object.")
        return value
