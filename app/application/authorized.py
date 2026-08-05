"""Tenant-bound application service facade for future pilot interfaces."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from app.ai.models import IntelligenceResponse
from app.ai.registry import IntelligenceProviderRegistry
from app.campaign_planner.service import CampaignPlanningService
from app.identity import (
    AuthenticatedPrincipal,
    Permission,
    TenantAuthorizationService,
    TenantMembership,
)
from app.marketing_brief.models import BriefStatus, MarketingBrief

if TYPE_CHECKING:
    from app.application.composition import CanonicalApplication


@dataclass(slots=True)
class AuthorizedTenantApplication:
    """Expose only operations authorized for one authenticated tenant session."""

    application: "CanonicalApplication"
    principal: AuthenticatedPrincipal
    tenant_id: str
    authorization: TenantAuthorizationService

    def build_context(self, *, brand_id: str):
        self._authorize_brand(Permission.VIEW, brand_id)
        return self.application.build_context_assembler().build(
            tenant_id=self.tenant_id,
            brand_id=brand_id,
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

    def approve_campaign_plan(self, campaign_id: str):
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
        successor = CampaignPlanningService().create_next_version(current)
        CampaignPlanningService().approve(successor)
        self.application.campaign_plans.save(successor)
        return successor

    def approve_marketing_brief(self, brief_id: str) -> MarketingBrief:
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
        return self.application.build_marketing_brief_service().save_next_version(
            current, status=BriefStatus.APPROVED
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
    ) -> None:
        self.authorization.authorize(
            self.principal,
            tenant_id=self.tenant_id,
            permission=permission,
            resource_type=resource_type,
            resource_id=resource_id,
            resource_tenant_id=resource_tenant_id,
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
