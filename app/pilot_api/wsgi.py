"""Minimal WSGI JSON transport for the secure pilot API contract."""

import json
import re

from app.pilot_api.contracts import (
    ApprovalRequest,
    BriefRevisionRequest,
    CampaignRevisionRequest,
    ContextRequest,
    DataBoundaryRequest,
    DesignPartnerAcceptanceRequest,
    DesignPartnerReadinessRequest,
    DesignPartnerSignupRequest,
    ExportRequest,
    GenerationRequest,
    OnboardingRequest,
    WorkflowApprovalDecisionRequest,
    WorkflowCommandRequest,
    WorkflowCreateRequest,
    WorkflowReviewRequest,
)
from app.pilot_api.service import PilotApiError, PilotApiService


class PilotWsgiApplication:
    def __init__(self, service: PilotApiService) -> None:
        if not isinstance(service, PilotApiService):
            raise TypeError("service must be a PilotApiService.")
        self.service = service

    def __call__(self, environ, start_response):
        body = None
        headers = None
        try:
            response = self._dispatch(environ)
            status = response.status
            if response.body_bytes is not None:
                body = response.body_bytes
                headers = list(response.headers)
            else:
                payload = {"data": response.data}
                if response.replay_marker_in_body:
                    payload["replayed"] = response.replayed
                body = json.dumps(payload, ensure_ascii=False, sort_keys=True).encode()
                headers = [("Content-Type", "application/json; charset=utf-8")]
        except PilotApiError as error:
            status = error.status
            payload = {"error": {"code": error.code, "message": error.message}}
        except (TypeError, ValueError, json.JSONDecodeError) as error:
            status, payload = 400, {
                "error": {"code": "invalid_request", "message": str(error)}
            }
        if body is None:
            body = json.dumps(payload, ensure_ascii=False, sort_keys=True).encode()
            headers = [("Content-Type", "application/json; charset=utf-8")]
        headers = list(headers)
        if not any(name.casefold() == "content-length" for name, _ in headers):
            headers.append(("Content-Length", str(len(body))))
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
            headers,
        )
        return [body]

    def _dispatch(self, environ):
        method = environ.get("REQUEST_METHOD")
        path = str(environ.get("PATH_INFO", ""))
        credential = self._bearer(environ.get("HTTP_AUTHORIZATION", ""))
        body = self._json_body(environ) if method == "POST" else {}
        key = str(environ.get("HTTP_IDEMPOTENCY_KEY", ""))
        csrf = str(environ.get("HTTP_X_CSRF_TOKEN", ""))
        if path == "/v1/pilot/design-partner/signup":
            return self.service.design_partner_signup(
                credential=credential,
                request=DesignPartnerSignupRequest(**body),
            )
        tenant_id = str(environ.get("HTTP_X_TENANT_ID", "")).strip()
        if not tenant_id:
            raise PilotApiError(400, "tenant_required", "X-Tenant-ID is required.")
        common = {"credential": credential, "tenant_id": tenant_id}
        match = re.fullmatch(r"/v1/pilot/workflows/([^/]+)", path)
        if match and method == "GET":
            brand_id = str(environ.get("HTTP_X_BRAND_ID", "")).strip()
            if not brand_id:
                raise PilotApiError(400, "brand_required", "X-Brand-ID is required.")
            return self.service.workflow_status(
                brand_id=brand_id, workflow_id=match.group(1), **common
            )
        if method != "POST":
            raise PilotApiError(404, "not_found", "Endpoint was not found.")
        if path == "/v1/pilot/workflows":
            return self.service.create_workflow(
                request=WorkflowCreateRequest(**body),
                idempotency_key=key,
                csrf_token=csrf,
                **common,
            )
        match = re.fullmatch(r"/v1/pilot/workflows/([^/]+)/request-approval", path)
        if match:
            return self.service.request_workflow_approval(
                brand_id=str(body.get("brand_id", "")),
                workflow_id=match.group(1),
                request=WorkflowCommandRequest(
                    expected_version=body.get("expected_version")
                ),
                idempotency_key=key,
                csrf_token=csrf,
                **common,
            )
        match = re.fullmatch(r"/v1/pilot/workflows/([^/]+)/approval", path)
        if match:
            return self.service.decide_workflow_approval(
                brand_id=str(body.get("brand_id", "")),
                workflow_id=match.group(1),
                request=WorkflowApprovalDecisionRequest(
                    expected_version=body.get("expected_version"),
                    decision=body.get("decision", ""),
                ),
                idempotency_key=key,
                csrf_token=csrf,
                **common,
            )
        if path == "/v1/pilot/privacy/pack":
            return self.service.privacy_pack(**common)
        if path == "/v1/pilot/privacy/authorize":
            return self.service.authorize_data_boundary(
                request=DataBoundaryRequest(**body), **common
            )
        if path == "/v1/pilot/context":
            return self.service.context(request=ContextRequest(**body), **common)
        if path == "/v1/pilot/generate":
            return self.service.generate(
                request=GenerationRequest(**body), idempotency_key=key, **common
            )
        if path == "/v1/pilot/workflow-review":
            return self.service.workflow_review(
                request=WorkflowReviewRequest(**body), **common
            )
        if path == "/v1/pilot/design-partner/readiness":
            return self.service.design_partner_readiness(
                request=DesignPartnerReadinessRequest(**body), **common
            )
        if path == "/v1/pilot/design-partner/acceptance":
            return self.service.design_partner_acceptance(
                request=DesignPartnerAcceptanceRequest(**body), **common
            )
        if path == "/v1/pilot/onboarding/context":
            return self.service.save_onboarding_context(
                request=OnboardingRequest(**body), idempotency_key=key, **common
            )
        match = re.fullmatch(r"/v1/pilot/campaign-plans/([^/]+)/approve", path)
        if match:
            return self.service.approve_campaign_plan(
                campaign_id=match.group(1),
                request=ApprovalRequest(**body),
                idempotency_key=key,
                **common,
            )
        match = re.fullmatch(r"/v1/pilot/campaign-plans/([^/]+)/revise", path)
        if match:
            return self.service.revise_campaign_plan(
                campaign_id=match.group(1),
                request=CampaignRevisionRequest(**body),
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
        match = re.fullmatch(r"/v1/pilot/marketing-briefs/([^/]+)/revise", path)
        if match:
            return self.service.revise_marketing_brief(
                brief_id=match.group(1),
                request=BriefRevisionRequest(**body),
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
