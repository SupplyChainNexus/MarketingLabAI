"""Authenticated, transport-neutral secure pilot API service."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Callable

from app.ai.registry import IntelligenceProviderRegistry
from app.application import CanonicalApplication, LifecycleConflictError
from app.identity import AuthorizationDeniedError, IdentityProviderAdapter
from app.pilot_api.contracts import (
    ApiResponse,
    ApprovalRequest,
    ContextRequest,
    ExportRequest,
    GenerationRequest,
)
from app.pilot_api.idempotency import IdempotencyRepository


class PilotApiError(RuntimeError):
    def __init__(self, status: int, code: str, message: str) -> None:
        super().__init__(message)
        self.status, self.code, self.message = status, code, message


class PilotApiService:
    """Expose only approved secure-pilot operations."""

    def __init__(
        self,
        application: CanonicalApplication,
        identity_provider: IdentityProviderAdapter,
        registry: IntelligenceProviderRegistry,
    ) -> None:
        if not isinstance(application, CanonicalApplication):
            raise TypeError("application must be a CanonicalApplication.")
        if not isinstance(identity_provider, IdentityProviderAdapter):
            raise TypeError("identity_provider must be an IdentityProviderAdapter.")
        if not isinstance(registry, IntelligenceProviderRegistry):
            raise TypeError("registry must be an IntelligenceProviderRegistry.")
        self.application = application
        self.identity_provider = identity_provider
        self.registry = registry
        self.idempotency = IdempotencyRepository(application.database)

    def context(
        self, *, credential: str, tenant_id: str, request: ContextRequest
    ) -> ApiResponse:
        session = self._session(credential, tenant_id)
        try:
            context = session.build_context(brand_id=request.brand_id)
        except AuthorizationDeniedError as error:
            raise PilotApiError(403, "forbidden", "Operation was denied.") from error
        return ApiResponse(
            200,
            {
                "brand_id": request.brand_id,
                "company_context": context.company_context,
                "customer_context": context.customer_context,
                "product_context": context.product_context,
                "memory_context": context.memory_context,
                "missing": {
                    "company": not context.company_brain_included,
                    "customer": not context.customer_intelligence_included,
                    "product": not context.product_intelligence_included,
                    "memory": not context.memory_included,
                },
            },
        )

    def generate(
        self,
        *,
        credential: str,
        tenant_id: str,
        request: GenerationRequest,
        idempotency_key: str,
    ) -> ApiResponse:
        principal, session = self._principal_and_session(credential, tenant_id)
        return self._idempotent(
            principal,
            tenant_id,
            "generate",
            idempotency_key,
            {
                "brand_id": request.brand_id,
                "campaign_id": request.campaign_id,
                "campaign_version": request.campaign_version,
                "brief_id": request.brief_id,
                "brief_version": request.brief_version,
                "task": request.task,
                "instructions": request.instructions,
            },
            lambda: self._generation_response(session, request),
        )

    def approve_campaign_plan(
        self,
        *,
        credential: str,
        tenant_id: str,
        campaign_id: str,
        request: ApprovalRequest,
        idempotency_key: str,
    ) -> ApiResponse:
        principal, session = self._principal_and_session(credential, tenant_id)
        return self._idempotent(
            principal,
            tenant_id,
            "approve_campaign_plan",
            idempotency_key,
            {"campaign_id": campaign_id, "expected_version": request.expected_version},
            lambda: self._campaign_approval_response(
                session, campaign_id, request.expected_version
            ),
        )

    def approve_marketing_brief(
        self,
        *,
        credential: str,
        tenant_id: str,
        brief_id: str,
        request: ApprovalRequest,
        idempotency_key: str,
    ) -> ApiResponse:
        principal, session = self._principal_and_session(credential, tenant_id)
        return self._idempotent(
            principal,
            tenant_id,
            "approve_marketing_brief",
            idempotency_key,
            {"brief_id": brief_id, "expected_version": request.expected_version},
            lambda: self._brief_approval_response(
                session, brief_id, request.expected_version
            ),
        )

    def authorize_export(
        self,
        *,
        credential: str,
        tenant_id: str,
        request: ExportRequest,
        idempotency_key: str,
    ) -> ApiResponse:
        principal, session = self._principal_and_session(credential, tenant_id)
        return self._idempotent(
            principal,
            tenant_id,
            "authorize_export",
            idempotency_key,
            {
                "resource_type": request.resource_type,
                "resource_id": request.resource_id,
            },
            lambda: self._export_response(session, request),
        )

    def _principal_and_session(self, credential: str, tenant_id: str):
        try:
            principal = self.identity_provider.authenticate(credential)
        except PermissionError as error:
            raise PilotApiError(
                401, "unauthenticated", "Authentication failed."
            ) from error
        try:
            session = self.application.authorize(principal, tenant_id=tenant_id)
        except AuthorizationDeniedError as error:
            raise PilotApiError(
                403, "forbidden", "Tenant access was denied."
            ) from error
        return principal, session

    def _session(self, credential: str, tenant_id: str):
        return self._principal_and_session(credential, tenant_id)[1]

    def _idempotent(
        self,
        principal,
        tenant_id: str,
        operation: str,
        key: str,
        request_payload: dict,
        execute: Callable[[], ApiResponse],
    ) -> ApiResponse:
        key = key.strip() if isinstance(key, str) else ""
        if not key:
            raise PilotApiError(
                400, "idempotency_required", "Idempotency-Key is required."
            )
        request_hash = hashlib.sha256(
            json.dumps(request_payload, sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest()
        identity = dict(
            tenant_id=tenant_id,
            provider=principal.provider,
            subject_id=principal.subject_id,
            operation=operation,
            idempotency_key=key,
        )
        stored = self.idempotency.get(**identity)
        if stored is not None:
            if stored.request_hash != request_hash:
                raise PilotApiError(
                    409,
                    "idempotency_conflict",
                    "Idempotency key was reused for another request.",
                )
            return ApiResponse(stored.status, stored.data, replayed=True)
        try:
            response = execute()
        except LifecycleConflictError as error:
            raise PilotApiError(409, "lifecycle_conflict", str(error)) from error
        except AuthorizationDeniedError as error:
            raise PilotApiError(403, "forbidden", "Operation was denied.") from error
        except FileNotFoundError as error:
            raise PilotApiError(404, "not_found", "Resource was not found.") from error
        except ValueError as error:
            raise PilotApiError(409, "lifecycle_conflict", str(error)) from error
        self.idempotency.save(
            **identity,
            request_hash=request_hash,
            status=response.status,
            data=response.data,
        )
        return response

    def _generation_response(self, session, request: GenerationRequest) -> ApiResponse:
        response = session.generate_approved(
            self.registry,
            brand_id=request.brand_id,
            campaign_id=request.campaign_id,
            campaign_version=request.campaign_version,
            brief_id=request.brief_id,
            brief_version=request.brief_version,
            task=request.task,
            instructions=request.instructions,
        )
        return ApiResponse(
            201,
            {
                "content": response.content,
                "provider": response.provider,
                "model": response.model,
                "finish_reason": response.finish_reason,
            },
        )

    @staticmethod
    def _campaign_approval_response(session, resource_id: str, version: int):
        plan = session.approve_campaign_plan(resource_id, expected_version=version)
        return ApiResponse(
            200,
            {
                "resource_type": "campaign_plan",
                "resource_id": plan.campaign_id,
                "version": plan.version,
                "status": plan.status.value,
            },
        )

    @staticmethod
    def _brief_approval_response(session, resource_id: str, version: int):
        brief = session.approve_marketing_brief(resource_id, expected_version=version)
        return ApiResponse(
            200,
            {
                "resource_type": "marketing_brief",
                "resource_id": brief.brief_id,
                "version": brief.version,
                "status": brief.status.value,
            },
        )

    @staticmethod
    def _export_response(session, request: ExportRequest):
        session.authorize_export(
            resource_type=request.resource_type, resource_id=request.resource_id
        )
        return ApiResponse(
            200,
            {
                "resource_type": request.resource_type,
                "resource_id": request.resource_id,
                "authorized": True,
            },
        )
