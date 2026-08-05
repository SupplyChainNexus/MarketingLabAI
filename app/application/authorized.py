"""Tenant-bound application service facade for future pilot interfaces."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from app.ai.models import IntelligenceResponse
from app.ai.registry import IntelligenceProviderRegistry
from app.campaign_planner.models import CampaignStatus
from app.campaign_planner.service import CampaignPlanningService
from app.customer_intelligence import (
    CustomerEvidence,
    CustomerIntelligenceProfile,
    CustomerSegment,
)
from app.identity import (
    AuthenticatedPrincipal,
    Permission,
    TenantAuthorizationService,
    TenantMembership,
)
from app.intelligence.models import BusinessIntelligenceProfile
from app.marketing_brief.models import BriefStatus, MarketingBrief
from app.product_intelligence import (
    ProductEvidence,
    ProductIntelligenceProfile,
    ProductRecord,
    ProductType,
)


class LifecycleConflictError(RuntimeError):
    """Raised when an expected resource version is no longer current."""


if TYPE_CHECKING:
    from app.application.composition import CanonicalApplication


@dataclass(slots=True)
class AuthorizedTenantApplication:
    """Expose only operations authorized for one authenticated tenant session."""

    application: "CanonicalApplication"
    principal: AuthenticatedPrincipal
    tenant_id: str
    authorization: TenantAuthorizationService

    def build_context(
        self,
        *,
        brand_id: str,
        positioning_id: str = "",
        positioning_version: int = 0,
    ):
        self._authorize_brand(Permission.VIEW, brand_id)
        return self.application.build_context_assembler().build(
            tenant_id=self.tenant_id,
            brand_id=brand_id,
            positioning_id=positioning_id,
            positioning_version=positioning_version,
        )

    def save_onboarding_context(
        self,
        *,
        brand_id: str,
        business: dict[str, Any],
        customer: dict[str, Any],
        product: dict[str, Any],
    ) -> None:
        """Persist the minimum verified context collected by pilot onboarding."""

        self._authorize_brand(Permission.APPROVE, brand_id)
        source = str(product["evidence_source"]).strip()
        customer_source = str(customer["evidence_source"]).strip()
        self.application.business_intelligence.save(
            BusinessIntelligenceProfile(
                brand_id=brand_id,
                revenue_model=str(business.get("revenue_model", "")),
                geographic_markets=list(business.get("geographic_markets", [])),
                business_goals=list(business.get("business_goals", [])),
            )
        )
        segment_id = str(customer["segment_id"])
        self.application.customer_intelligence.save(
            CustomerIntelligenceProfile(
                brand_id=brand_id,
                summary=str(customer.get("summary", "")),
                primary_segment_id=segment_id,
                segments=[
                    CustomerSegment(
                        segment_id=segment_id,
                        name=str(customer["name"]),
                        description=str(customer.get("description", "")),
                        evidence=[
                            CustomerEvidence(
                                source=customer_source,
                                confidence=1.0,
                                summary="Verified during synthetic pilot onboarding.",
                                verified=True,
                            )
                        ],
                    )
                ],
            )
        )
        self.application.product_intelligence.save(
            ProductIntelligenceProfile(
                tenant_id=self.tenant_id,
                brand_id=brand_id,
                products=[
                    ProductRecord(
                        product_id=str(product["product_id"]),
                        name=str(product["name"]),
                        product_type=ProductType(str(product["product_type"])),
                        description=str(product.get("description", "")),
                        evidence=[ProductEvidence(source)],
                        features=list(product.get("features", [])),
                        benefits=list(product.get("benefits", [])),
                        limitations=list(product.get("limitations", [])),
                        prohibited_claims=list(product.get("prohibited_claims", [])),
                    )
                ],
            )
        )

    def generate(
        self,
        registry: IntelligenceProviderRegistry,
        *,
        brand_id: str,
        task: str,
        instructions: str = "",
        **options: Any,
    ) -> IntelligenceResponse:
        self._authorize_brand(Permission.GENERATE, brand_id)
        return self.application.build_ai_orchestrator(registry).generate(
            tenant_id=self.tenant_id,
            brand_id=brand_id,
            task=task,
            instructions=instructions,
            metadata={
                "authenticated_subject_id": self.principal.subject_id,
                "identity_provider": self.principal.provider,
            },
            **options,
        )

    def generate_approved(
        self,
        registry: IntelligenceProviderRegistry,
        *,
        brand_id: str,
        campaign_id: str,
        campaign_version: int,
        brief_id: str,
        brief_version: int,
        task: str,
        instructions: str = "",
        **options: Any,
    ) -> IntelligenceResponse:
        """Generate only from approved, tenant-bound campaign governance."""

        self._authorize_brand(Permission.GENERATE, brand_id)
        plan = self.application.campaign_plans.get(
            campaign_id,
            tenant_id=self.tenant_id,
            version=campaign_version,
        )
        brief = self.application.marketing_briefs.get(
            brief_id,
            tenant_id=self.tenant_id,
            version=brief_version,
        )
        if plan.brand_id != brand_id or brief.brand_id != brand_id:
            raise LifecycleConflictError(
                "Campaign Plan and Marketing Brief must belong to the requested brand."
            )
        if plan.status is not CampaignStatus.APPROVED:
            raise LifecycleConflictError("Campaign Plan version is not approved.")
        if brief.status is not BriefStatus.APPROVED:
            raise LifecycleConflictError("Marketing Brief version is not approved.")
        plan_reference = (plan.positioning_id, plan.positioning_version)
        brief_reference = (brief.positioning_id, brief.positioning_version)
        if not plan.positioning_id or plan_reference != brief_reference:
            raise LifecycleConflictError(
                "Campaign Plan and Marketing Brief require the same approved "
                "positioning reference."
            )
        try:
            positioning = self.application.positioning_intelligence.get(
                tenant_id=self.tenant_id,
                positioning_id=plan.positioning_id,
                version=plan.positioning_version,
            )
            latest_positioning = self.application.positioning_intelligence.latest(
                tenant_id=self.tenant_id,
                positioning_id=plan.positioning_id,
            )
        except FileNotFoundError as error:
            raise LifecycleConflictError(
                "Referenced positioning was not found for this tenant."
            ) from error
        if positioning.brand_id != brand_id:
            raise LifecycleConflictError(
                "Referenced positioning belongs to another brand."
            )
        if (
            positioning.status.value != "approved"
            or latest_positioning.version != positioning.version
        ):
            raise LifecycleConflictError(
                "Referenced positioning is not the current approved version."
            )
        plan_strategy = (plan.strategy_id, plan.strategy_version)
        brief_strategy = (brief.strategy_id, brief.strategy_version)
        if not plan.strategy_id or plan_strategy != brief_strategy:
            raise LifecycleConflictError(
                "Campaign Plan and Marketing Brief require the same approved "
                "strategy reference."
            )
        try:
            strategy = self.application.strategy_intelligence.get(
                tenant_id=self.tenant_id,
                strategy_id=plan.strategy_id,
                version=plan.strategy_version,
            )
            latest_strategy = self.application.strategy_intelligence.latest(
                tenant_id=self.tenant_id,
                strategy_id=plan.strategy_id,
            )
        except FileNotFoundError as error:
            raise LifecycleConflictError(
                "Referenced strategy was not found for this tenant."
            ) from error
        if strategy.brand_id != brand_id:
            raise LifecycleConflictError(
                "Referenced strategy belongs to another brand."
            )
        if (
            strategy.status.value != "approved"
            or latest_strategy.version != strategy.version
        ):
            raise LifecycleConflictError(
                "Referenced strategy is not the current approved version."
            )
        if (
            strategy.positioning_id,
            strategy.positioning_version,
        ) != plan_reference:
            raise LifecycleConflictError(
                "Approved strategy and positioning references do not match."
            )
        return self.application.build_ai_orchestrator(registry).generate(
            tenant_id=self.tenant_id,
            brand_id=brand_id,
            task=task,
            instructions=instructions,
            metadata={
                "authenticated_subject_id": self.principal.subject_id,
                "identity_provider": self.principal.provider,
                "approved_campaign_id": plan.campaign_id,
                "approved_campaign_version": plan.version,
                "approved_brief_id": brief.brief_id,
                "approved_brief_version": brief.version,
                "approved_positioning_id": positioning.positioning_id,
                "approved_positioning_version": positioning.version,
                "approved_strategy_id": strategy.strategy_id,
                "approved_strategy_version": strategy.version,
            },
            positioning_id=positioning.positioning_id,
            positioning_version=positioning.version,
            strategy_id=strategy.strategy_id,
            strategy_version=strategy.version,
            **options,
        )

    def approve_campaign_plan(
        self, campaign_id: str, *, expected_version: int | None = None
    ):
        owner = self._resource_tenant("campaign_plans", "campaign_id", campaign_id)
        self._authorize(
            Permission.APPROVE,
            "campaign_plan",
            campaign_id,
            resource_tenant_id=owner,
        )
        current = self.application.campaign_plans.get(
            campaign_id, tenant_id=self.tenant_id
        )
        self._require_expected_version(current.version, expected_version)
        successor = CampaignPlanningService().create_next_version(current)
        CampaignPlanningService().approve(successor)
        self.application.campaign_plans.save(successor)
        return successor

    def review_campaign_plan(self, campaign_id: str, *, version: int | None = None):
        owner = self._resource_tenant("campaign_plans", "campaign_id", campaign_id)
        self._authorize(
            Permission.VIEW,
            "campaign_plan",
            campaign_id,
            resource_tenant_id=owner,
        )
        return self.application.campaign_plans.get(
            campaign_id, tenant_id=self.tenant_id, version=version
        )

    def review_positioning(self, positioning_id: str, *, version: int):
        """Return one authorized, tenant-scoped positioning decision."""

        decision = self.application.positioning_intelligence.get(
            tenant_id=self.tenant_id,
            positioning_id=positioning_id,
            version=version,
        )
        self._authorize_brand(Permission.VIEW, decision.brand_id)
        return decision

    def revise_campaign_plan(
        self,
        campaign_id: str,
        *,
        expected_version: int,
        changes: dict[str, Any],
    ):
        owner = self._resource_tenant("campaign_plans", "campaign_id", campaign_id)
        self._authorize(
            Permission.APPROVE,
            "campaign_plan",
            campaign_id,
            resource_tenant_id=owner,
            audit_action="revise",
        )
        current = self.application.campaign_plans.get(
            campaign_id, tenant_id=self.tenant_id
        )
        self._require_expected_version(current.version, expected_version)
        successor = CampaignPlanningService().create_next_version(current, **changes)
        CampaignPlanningService().mark_planned(successor)
        self.application.campaign_plans.save(successor)
        return successor

    def approve_marketing_brief(
        self, brief_id: str, *, expected_version: int | None = None
    ) -> MarketingBrief:
        owner = self._resource_tenant("marketing_briefs", "brief_id", brief_id)
        self._authorize(
            Permission.APPROVE,
            "marketing_brief",
            brief_id,
            resource_tenant_id=owner,
        )
        current = self.application.marketing_briefs.get(
            brief_id, tenant_id=self.tenant_id
        )
        self._require_expected_version(current.version, expected_version)
        return self.application.build_marketing_brief_service().save_next_version(
            current, status=BriefStatus.APPROVED
        )

    def review_marketing_brief(
        self, brief_id: str, *, version: int | None = None
    ) -> MarketingBrief:
        owner = self._resource_tenant("marketing_briefs", "brief_id", brief_id)
        self._authorize(
            Permission.VIEW,
            "marketing_brief",
            brief_id,
            resource_tenant_id=owner,
        )
        return self.application.marketing_briefs.get(
            brief_id, tenant_id=self.tenant_id, version=version
        )

    def revise_marketing_brief(
        self,
        brief_id: str,
        *,
        expected_version: int,
        changes: dict[str, Any],
    ) -> MarketingBrief:
        owner = self._resource_tenant("marketing_briefs", "brief_id", brief_id)
        self._authorize(
            Permission.APPROVE,
            "marketing_brief",
            brief_id,
            resource_tenant_id=owner,
            audit_action="revise",
        )
        current = self.application.marketing_briefs.get(
            brief_id, tenant_id=self.tenant_id
        )
        self._require_expected_version(current.version, expected_version)
        return self.application.build_marketing_brief_service().save_next_version(
            current, status=BriefStatus.DRAFT, **changes
        )

    @staticmethod
    def _require_expected_version(current: int, expected: int | None) -> None:
        if expected is None:
            return
        if isinstance(expected, bool) or not isinstance(expected, int):
            raise TypeError("expected_version must be an integer.")
        if expected != current:
            raise LifecycleConflictError(
                f"Expected version {expected}, but current version is {current}."
            )

    def authorize_export(self, *, resource_type: str, resource_id: str) -> None:
        """Authorize and audit export; byte serialization remains MLAI-027.4."""

        lookup = {
            "campaign_plan": ("campaign_plans", "campaign_id"),
            "marketing_brief": ("marketing_briefs", "brief_id"),
        }.get(resource_type)
        owner = (
            self._resource_tenant(*lookup, resource_id)
            if lookup is not None
            else "missing"
        )
        self._authorize(
            Permission.EXPORT,
            resource_type,
            resource_id,
            resource_tenant_id=owner,
        )

    def save_membership(self, membership: TenantMembership) -> None:
        """Provision or change membership only within the bound tenant."""

        if not isinstance(membership, TenantMembership):
            raise TypeError("membership must be a TenantMembership.")
        self._authorize(
            Permission.MANAGE_MEMBERS,
            "tenant_membership",
            f"{membership.provider}:{membership.subject_id}",
            resource_tenant_id=membership.tenant_id,
        )
        self.application.identities.save_membership(membership)

    def _authorize_brand(self, permission: Permission, brand_id: str) -> None:
        owner = None
        try:
            owner = self.application.brands.tenant_id_for(brand_id)
        except FileNotFoundError:
            pass
        self._authorize(
            permission, "brand", brand_id, resource_tenant_id=owner or "missing"
        )

    def _authorize(
        self,
        permission: Permission,
        resource_type: str,
        resource_id: str,
        *,
        resource_tenant_id: str | None = None,
        audit_action: str | None = None,
    ) -> None:
        self.authorization.authorize(
            self.principal,
            tenant_id=self.tenant_id,
            permission=permission,
            resource_type=resource_type,
            resource_id=resource_id,
            resource_tenant_id=resource_tenant_id,
            audit_action=audit_action,
        )

    def _resource_tenant(self, table: str, id_column: str, resource_id: str) -> str:
        allowed = {
            ("campaign_plans", "campaign_id"),
            ("marketing_briefs", "brief_id"),
        }
        if (table, id_column) not in allowed:
            raise ValueError("Unsupported authorized resource lookup.")
        with self.application.database.connection() as connection:
            row = connection.execute(
                f"SELECT tenant_id FROM {table} WHERE {id_column} = ? "
                "ORDER BY version DESC LIMIT 1",
                (resource_id,),
            ).fetchone()
        return str(row["tenant_id"]) if row is not None else "missing"
