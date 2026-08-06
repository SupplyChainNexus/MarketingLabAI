"""Authenticated, transport-neutral secure pilot API service."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Callable
from datetime import UTC, datetime
from uuid import uuid4

from app.ai.registry import IntelligenceProviderRegistry
from app.application import CanonicalApplication, LifecycleConflictError
from app.compliance.engine import ComplianceEngine
from app.compliance.models import ReviewSubjectType
from app.design_partner import (
    DesignPartnerReadinessEvaluator,
    FounderDesignPartnerSignupService,
    PilotPrivacyPolicy,
    SignupConflictError,
)
from app.identity import AuthorizationDeniedError, IdentityProviderAdapter
from app.pilot_api.contracts import (
    ApiResponse,
    ApprovalRequest,
    BriefRevisionRequest,
    CampaignRevisionRequest,
    ContextRequest,
    DataBoundaryRequest,
    DesignPartnerReadinessRequest,
    DesignPartnerSignupRequest,
    ExportRequest,
    GenerationRequest,
    OnboardingRequest,
    WorkflowReviewRequest,
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
        *,
        signup_identity_provider: IdentityProviderAdapter | None = None,
        founder_invitation_hashes: dict[str, str] | None = None,
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
        self.founder_signup = FounderDesignPartnerSignupService(
            application.database,
            signup_identity_provider or identity_provider,
            founder_invitation_hashes or {},
        )

    def design_partner_signup(
        self,
        *,
        credential: str,
        request: DesignPartnerSignupRequest,
    ) -> ApiResponse:
        try:
            result = self.founder_signup.signup(
                credential=credential,
                partner_name=request.partner_name,
                invitation_code=request.invitation_code,
                privacy_notice_accepted=request.privacy_notice_accepted,
                synthetic_data_boundary_accepted=(
                    request.synthetic_data_boundary_accepted
                ),
                privacy_notice_version=request.privacy_notice_version,
                data_boundary_version=request.data_boundary_version,
            )
        except PermissionError as error:
            raise PilotApiError(403, "invitation_denied", str(error)) from error
        except SignupConflictError as error:
            raise PilotApiError(409, "invitation_claimed", str(error)) from error
        return ApiResponse(200 if result.replayed else 201, result.to_dict())

    def privacy_pack(self, *, credential: str, tenant_id: str) -> ApiResponse:
        principal, _ = self._principal_and_session(credential, tenant_id)
        pack = PilotPrivacyPolicy().pack(tenant_id=tenant_id)
        with self.application.database.connection() as connection:
            row = connection.execute(
                """
                SELECT notice_version, boundary_version, accepted_at
                FROM pilot_privacy_acceptances
                WHERE tenant_id = ? AND provider = ? AND subject_id = ?
                ORDER BY accepted_at DESC LIMIT 1
                """,
                (tenant_id, principal.provider, principal.subject_id),
            ).fetchone()
        pack["acceptance"] = (
            {
                "recorded": True,
                "notice_version": str(row["notice_version"]),
                "boundary_version": str(row["boundary_version"]),
                "accepted_at": str(row["accepted_at"]),
                "current": (
                    str(row["notice_version"]) == PilotPrivacyPolicy.NOTICE_VERSION
                    and str(row["boundary_version"])
                    == PilotPrivacyPolicy.BOUNDARY_VERSION
                ),
            }
            if row is not None
            else {"recorded": False, "current": False}
        )
        return ApiResponse(200, pack)

    def authorize_data_boundary(
        self,
        *,
        credential: str,
        tenant_id: str,
        request: DataBoundaryRequest,
    ) -> ApiResponse:
        self._session(credential, tenant_id)
        decision = PilotPrivacyPolicy().authorize(
            tenant_id=tenant_id, category=request.category
        )
        return ApiResponse(200, decision.to_dict())

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

    def workflow_review(
        self,
        *,
        credential: str,
        tenant_id: str,
        request: WorkflowReviewRequest,
    ) -> ApiResponse:
        session = self._session(credential, tenant_id)
        try:
            context = session.build_context(brand_id=request.brand_id)
            plan = session.review_campaign_plan(request.campaign_id)
            brief = session.review_marketing_brief(request.brief_id)
        except AuthorizationDeniedError as error:
            raise PilotApiError(403, "forbidden", "Operation was denied.") from error
        except FileNotFoundError as error:
            raise PilotApiError(404, "not_found", "Resource was not found.") from error
        if plan.brand_id != request.brand_id or brief.brand_id != request.brand_id:
            raise PilotApiError(
                409,
                "lifecycle_conflict",
                "Campaign Plan and Marketing Brief must belong to the requested brand.",
            )
        positioning = None
        positioning_ready = False
        positioning_reason = "A shared positioning reference is required."
        plan_reference = (plan.positioning_id, plan.positioning_version)
        brief_reference = (brief.positioning_id, brief.positioning_version)
        if plan.positioning_id and plan_reference == brief_reference:
            try:
                positioning = session.review_positioning(
                    plan.positioning_id, version=plan.positioning_version
                )
                latest = self.application.positioning_intelligence.latest(
                    tenant_id=tenant_id,
                    positioning_id=plan.positioning_id,
                )
                positioning_ready = (
                    positioning.brand_id == request.brand_id
                    and positioning.status.value == "approved"
                    and positioning.version == latest.version
                )
                positioning_reason = (
                    "Current approved positioning is available."
                    if positioning_ready
                    else "Positioning is not current, approved, and brand-aligned."
                )
            except (FileNotFoundError, AuthorizationDeniedError):
                positioning_reason = "Positioning is unavailable for this tenant."
        strategy = None
        strategy_ready = False
        strategy_reason = "A shared Strategy reference is required."
        plan_strategy = (plan.strategy_id, plan.strategy_version)
        brief_strategy = (brief.strategy_id, brief.strategy_version)
        if plan.strategy_id and plan_strategy == brief_strategy:
            try:
                strategy = session.review_strategy(
                    plan.strategy_id, version=plan.strategy_version
                )
                latest_strategy = self.application.strategy_intelligence.latest(
                    tenant_id=tenant_id, strategy_id=plan.strategy_id
                )
                strategy_ready = (
                    strategy.brand_id == request.brand_id
                    and strategy.status.value == "approved"
                    and strategy.version == latest_strategy.version
                    and (strategy.positioning_id, strategy.positioning_version)
                    == plan_reference
                )
                strategy_reason = (
                    "Current approved Strategy is available."
                    if strategy_ready
                    else "Strategy is not current, approved, and reference-aligned."
                )
            except (FileNotFoundError, AuthorizationDeniedError):
                strategy_reason = "Strategy is unavailable for this tenant."
        return ApiResponse(
            200,
            {
                "context": self._context_summary(request.brand_id, context),
                "campaign_plan": self._plan_summary(plan),
                "marketing_brief": self._brief_summary(brief),
                "positioning": self._positioning_summary(
                    positioning, positioning_ready, positioning_reason
                ),
                "strategy": self._strategy_summary(
                    strategy, strategy_ready, strategy_reason
                ),
                "generation_ready": (
                    plan.status.value == "approved"
                    and brief.status.value == "approved"
                    and positioning_ready
                    and strategy_ready
                ),
            },
        )

    def design_partner_readiness(
        self,
        *,
        credential: str,
        tenant_id: str,
        request: DesignPartnerReadinessRequest,
    ) -> ApiResponse:
        self._session(credential, tenant_id)
        data = DesignPartnerReadinessEvaluator().evaluate(
            partner_name=request.partner_name,
            evidence=request.evidence,
        )
        return ApiResponse(200, data)

    def save_onboarding_context(
        self,
        *,
        credential: str,
        tenant_id: str,
        request: OnboardingRequest,
        idempotency_key: str,
    ) -> ApiResponse:
        principal, session = self._principal_and_session(credential, tenant_id)
        return self._idempotent(
            principal,
            tenant_id,
            "save_onboarding_context",
            idempotency_key,
            {
                "brand_id": request.brand_id,
                "business": request.business,
                "customer": request.customer,
                "product": request.product,
            },
            lambda: self._onboarding_response(session, request),
        )

    def revise_campaign_plan(
        self,
        *,
        credential: str,
        tenant_id: str,
        campaign_id: str,
        request: CampaignRevisionRequest,
        idempotency_key: str,
    ) -> ApiResponse:
        principal, session = self._principal_and_session(credential, tenant_id)
        return self._idempotent(
            principal,
            tenant_id,
            "revise_campaign_plan",
            idempotency_key,
            {
                "campaign_id": campaign_id,
                "expected_version": request.expected_version,
                "changes": request.changes,
            },
            lambda: self._campaign_revision_response(session, campaign_id, request),
        )

    def revise_marketing_brief(
        self,
        *,
        credential: str,
        tenant_id: str,
        brief_id: str,
        request: BriefRevisionRequest,
        idempotency_key: str,
    ) -> ApiResponse:
        principal, session = self._principal_and_session(credential, tenant_id)
        return self._idempotent(
            principal,
            tenant_id,
            "revise_marketing_brief",
            idempotency_key,
            {
                "brief_id": brief_id,
                "expected_version": request.expected_version,
                "changes": request.changes,
            },
            lambda: self._brief_revision_response(session, brief_id, request),
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
        plan = self.application.campaign_plans.get(
            request.campaign_id,
            tenant_id=session.tenant_id,
            version=request.campaign_version,
        )

        subject_id = str(uuid4())
        compliance = ComplianceEngine(self.application.compliance_rules).evaluate(
            brand_id=request.brand_id,
            subject_id=subject_id,
            subject_type=ReviewSubjectType.TEXT,
            content=response.content,
        )
        return ApiResponse(
            201,
            {
                "asset_id": subject_id,
                "content": response.content,
                "provider": response.provider,
                "model": response.model,
                "finish_reason": response.finish_reason,
                "compliance": compliance.to_dict(),
                "limitations": [
                    "Private synthetic pilot only; real customer data is prohibited.",
                    "Human review remains required before external use.",
                    "Export authorization does not publish content.",
                ],
                "audit": {
                    "campaign_id": request.campaign_id,
                    "campaign_version": request.campaign_version,
                    "brief_id": request.brief_id,
                    "brief_version": request.brief_version,
                    "positioning_id": plan.positioning_id,
                    "positioning_version": plan.positioning_version,
                    "provider": response.provider,
                    "model": response.model,
                    "generated_at": datetime.now(UTC).isoformat(),
                },
            },
        )

    @staticmethod
    def _onboarding_response(session, request):
        session.save_onboarding_context(
            brand_id=request.brand_id,
            business=request.business,
            customer=request.customer,
            product=request.product,
        )
        return ApiResponse(
            200,
            {
                "brand_id": request.brand_id,
                "saved": True,
                "verified_sections": ["company", "customer", "product"],
            },
        )

    @staticmethod
    def _context_summary(brand_id, context):
        return {
            "brand_id": brand_id,
            "missing": {
                "company": not context.company_brain_included,
                "customer": not context.customer_intelligence_included,
                "product": not context.product_intelligence_included,
                "memory": not context.memory_included,
            },
        }

    @staticmethod
    def _plan_summary(plan):
        return {
            "campaign_id": plan.campaign_id,
            "version": plan.version,
            "brand_id": plan.brand_id,
            "name": plan.name,
            "objective": plan.objective.to_dict(),
            "audience": plan.audience.to_dict(),
            "timeline": plan.timeline.to_dict(),
            "channels": [channel.to_dict() for channel in plan.channels],
            "success_metrics": [metric.to_dict() for metric in plan.success_metrics],
            "owner": plan.owner,
            "status": plan.status.value,
            "notes": plan.notes,
            "positioning_id": plan.positioning_id,
            "positioning_version": plan.positioning_version,
        }

    @staticmethod
    def _positioning_summary(positioning, ready: bool, reason: str):
        if positioning is None:
            return {"ready": False, "reason": reason}
        return {
            "positioning_id": positioning.positioning_id,
            "version": positioning.version,
            "status": positioning.status.value,
            "value_proposition": positioning.value_proposition,
            "limitations": list(positioning.assumptions)
            + [item.reason for item in positioning.unknowns],
            "ready": ready,
            "reason": reason,
        }

    @staticmethod
    def _strategy_summary(strategy, ready: bool, reason: str):
        if strategy is None:
            return {"ready": False, "reason": reason}
        return {
            "strategy_id": strategy.strategy_id,
            "version": strategy.version,
            "status": strategy.status.value,
            "planning_horizon": strategy.planning_horizon,
            "business_objectives": list(strategy.business_objectives),
            "strategic_choices": list(strategy.strategic_choices),
            "explicit_non_choices": list(strategy.explicit_non_choices),
            "assumptions": list(strategy.assumptions),
            "unknowns": [item.reason for item in strategy.unknowns],
            "confidence": strategy.confidence,
            "positioning_id": strategy.positioning_id,
            "positioning_version": strategy.positioning_version,
            "ready": ready,
            "reason": reason,
        }

    @staticmethod
    def _brief_summary(brief):
        return {
            key: value
            for key, value in brief.to_dict().items()
            if key not in {"tenant_id", "evidence"}
        }

    @staticmethod
    def _campaign_revision_response(session, resource_id, request):
        plan = session.revise_campaign_plan(
            resource_id,
            expected_version=request.expected_version,
            changes=request.changes,
        )
        return ApiResponse(200, PilotApiService._plan_summary(plan))

    @staticmethod
    def _brief_revision_response(session, resource_id, request):
        brief = session.revise_marketing_brief(
            resource_id,
            expected_version=request.expected_version,
            changes=request.changes,
        )
        return ApiResponse(200, PilotApiService._brief_summary(brief))

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
