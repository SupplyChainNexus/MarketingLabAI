"""Canonical composition root for the secure pilot workflow."""

from __future__ import annotations

from dataclasses import dataclass

from app.ai.assembler import AIContextAssembler
from app.ai.orchestrator import AIOrchestrator
from app.ai.registry import IntelligenceProviderRegistry
from app.campaign_planner.repository import CampaignPlanRepository
from app.campaigns.campaign_engine import CampaignEngine
from app.campaigns.review_pipeline import CampaignReviewPipeline
from app.compliance.engine import ComplianceEngine
from app.compliance.repository import BrandRuleRepository
from app.customer_intelligence.provider import CustomerContextProvider
from app.database.connection import SQLiteDatabase
from app.database.factory import bootstrap_database, require_database_ready
from app.database.repositories import (
    BrandRepository,
    BusinessIntelligenceRepository,
    CustomerIntelligenceRepository,
    MemoryRepository,
)
from app.identity import (
    AuthenticatedPrincipal,
    IdentityRepository,
    Permission,
    TenantAuthorizationService,
)
from app.marketing_brief.campaign_workflow import MarketingBriefCampaignWorkflow
from app.marketing_brief.prompt_pack import MarketingBriefPromptPackService
from app.marketing_brief.repository import MarketingBriefRepository
from app.marketing_brief.service import MarketingBriefService
from app.marketing_workflow.orchestration import (
    WorkflowApiOperationClaimRepository,
    WorkflowApiOrchestrationRepository,
)
from app.marketing_workflow.repository import MarketingWorkflowRepository
from app.positioning_intelligence import (
    PositioningContextProvider,
    PositioningRepository,
    PositioningService,
)
from app.product_intelligence import (
    ProductContextProvider,
    ProductIntelligenceRepository,
)
from app.prompts.repository import PromptPackRepository
from app.prompts.selector import PromptPackSelector
from app.strategy_intelligence import (
    StrategyContextProvider,
    StrategyRepository,
    StrategyService,
)
from app.tenants.repository import TenantRepository


@dataclass(slots=True)
class CanonicalApplication:
    """Own the shared SQLite-backed application dependencies."""

    database: SQLiteDatabase
    tenants: TenantRepository
    brands: BrandRepository
    business_intelligence: BusinessIntelligenceRepository
    customer_intelligence: CustomerIntelligenceRepository
    product_intelligence: ProductIntelligenceRepository
    positioning_intelligence: PositioningRepository
    strategy_intelligence: StrategyRepository
    memory: MemoryRepository
    campaign_plans: CampaignPlanRepository
    marketing_briefs: MarketingBriefRepository
    marketing_workflows: MarketingWorkflowRepository
    workflow_orchestrations: WorkflowApiOrchestrationRepository
    workflow_operation_claims: WorkflowApiOperationClaimRepository
    prompt_packs: PromptPackRepository
    compliance_rules: BrandRuleRepository
    identities: IdentityRepository
    authorization: TenantAuthorizationService

    @classmethod
    def build(
        cls,
        database: SQLiteDatabase | None = None,
        *,
        initialise_schema: bool = True,
    ) -> "CanonicalApplication":
        """Build all canonical repositories over one database."""

        selected_database = database or SQLiteDatabase()
        if initialise_schema:
            bootstrap_database(selected_database)
        else:
            require_database_ready(selected_database)

        identities = IdentityRepository(selected_database)
        return cls(
            database=selected_database,
            tenants=TenantRepository(selected_database),
            brands=BrandRepository(selected_database),
            business_intelligence=BusinessIntelligenceRepository(selected_database),
            customer_intelligence=CustomerIntelligenceRepository(selected_database),
            product_intelligence=ProductIntelligenceRepository(selected_database),
            positioning_intelligence=PositioningRepository(selected_database),
            strategy_intelligence=StrategyRepository(selected_database),
            memory=MemoryRepository(selected_database),
            campaign_plans=CampaignPlanRepository(selected_database),
            marketing_briefs=MarketingBriefRepository(selected_database),
            marketing_workflows=MarketingWorkflowRepository(selected_database),
            workflow_orchestrations=WorkflowApiOrchestrationRepository(
                selected_database
            ),
            workflow_operation_claims=WorkflowApiOperationClaimRepository(
                selected_database
            ),
            prompt_packs=PromptPackRepository(selected_database),
            compliance_rules=BrandRuleRepository(selected_database),
            identities=identities,
            authorization=TenantAuthorizationService(identities),
        )

    def authorize(
        self,
        principal: AuthenticatedPrincipal,
        *,
        tenant_id: str,
    ):
        """Return a tenant-bound facade only after trusted membership checks."""

        from app.application.authorized import AuthorizedTenantApplication

        self.authorization.authorize(
            principal,
            tenant_id=tenant_id,
            permission=Permission.VIEW,
            resource_type="tenant_session",
            resource_id=tenant_id,
            resource_tenant_id=tenant_id,
            audit_action="identity",
        )
        return AuthorizedTenantApplication(
            application=self,
            principal=principal,
            tenant_id=tenant_id,
            authorization=self.authorization,
        )

    def build_context_assembler(self) -> AIContextAssembler:
        """Compose Company, Customer, and memory context from SQLite."""

        return AIContextAssembler(
            intelligence_repository=self.business_intelligence,
            customer_context_provider=CustomerContextProvider(
                repository=self.customer_intelligence,
            ),
            product_context_provider=ProductContextProvider(
                repository=self.product_intelligence,
            ),
            positioning_context_provider=PositioningContextProvider(
                repository=self.positioning_intelligence,
            ),
            strategy_context_provider=StrategyContextProvider(
                repository=self.strategy_intelligence,
            ),
            memory_repository=self.memory,
        )

    def build_positioning_service(self) -> PositioningService:
        """Return the canonical immutable Positioning Intelligence service."""

        return PositioningService(self.positioning_intelligence)

    def build_strategy_service(self) -> StrategyService:
        """Return the canonical immutable Strategy Intelligence service."""

        return StrategyService(
            self.strategy_intelligence,
            positioning_repository=self.positioning_intelligence,
        )

    def build_marketing_brief_service(self) -> MarketingBriefService:
        """Return the canonical immutable Marketing Brief service."""

        return MarketingBriefService(self.marketing_briefs)

    def build_ai_orchestrator(
        self,
        registry: IntelligenceProviderRegistry,
    ) -> AIOrchestrator:
        """Compose provider-neutral generation with canonical context."""

        return AIOrchestrator(
            registry,
            context_assembler=self.build_context_assembler(),
        )

    def build_campaign_engine(
        self,
        registry: IntelligenceProviderRegistry,
        *,
        tenant_id: str,
        provider_name: str | None = None,
    ) -> CampaignEngine:
        """Compose campaign generation without a provider-specific path."""

        return CampaignEngine(
            orchestrator=self.build_ai_orchestrator(registry),
            tenant_id=tenant_id,
            provider_name=provider_name,
        )

    def build_campaign_workflow(
        self,
        *,
        campaign_engine,
        campaign_artifact_service,
        compliance_engine: ComplianceEngine | None = None,
    ) -> MarketingBriefCampaignWorkflow:
        """Compose the approved-plan governed generation workflow.

        Campaign artifacts remain an explicit boundary until their canonical
        relational repository is introduced. Callers must inject that boundary;
        the composition root never silently falls back to legacy JSON storage.
        """

        selected_compliance_engine = compliance_engine or ComplianceEngine(
            self.compliance_rules
        )
        review_pipeline = CampaignReviewPipeline(
            campaign_engine=campaign_engine,
            campaign_service=campaign_artifact_service,
            compliance_engine=selected_compliance_engine,
        )
        prompt_service = MarketingBriefPromptPackService(
            PromptPackSelector(self.prompt_packs)
        )

        return MarketingBriefCampaignWorkflow(
            review_pipeline=review_pipeline,
            prompt_pack_service=prompt_service,
        )
