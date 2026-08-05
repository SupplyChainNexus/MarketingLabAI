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
from app.database.repositories import (
    BrandRepository,
    BusinessIntelligenceRepository,
    CustomerIntelligenceRepository,
    MemoryRepository,
)
from app.marketing_brief.campaign_workflow import MarketingBriefCampaignWorkflow
from app.marketing_brief.prompt_pack import MarketingBriefPromptPackService
from app.marketing_brief.repository import MarketingBriefRepository
from app.marketing_brief.service import MarketingBriefService
from app.prompts.repository import PromptPackRepository
from app.prompts.selector import PromptPackSelector
from app.tenants.repository import TenantRepository


@dataclass(slots=True)
class CanonicalApplication:
    """Own the shared SQLite-backed application dependencies."""

    database: SQLiteDatabase
    tenants: TenantRepository
    brands: BrandRepository
    business_intelligence: BusinessIntelligenceRepository
    customer_intelligence: CustomerIntelligenceRepository
    memory: MemoryRepository
    campaign_plans: CampaignPlanRepository
    marketing_briefs: MarketingBriefRepository
    prompt_packs: PromptPackRepository
    compliance_rules: BrandRuleRepository

    @classmethod
    def build(
        cls,
        database: SQLiteDatabase | None = None,
    ) -> "CanonicalApplication":
        """Build all canonical repositories over one database."""

        selected_database = database or SQLiteDatabase()
        selected_database.initialise()

        return cls(
            database=selected_database,
            tenants=TenantRepository(selected_database),
            brands=BrandRepository(selected_database),
            business_intelligence=BusinessIntelligenceRepository(selected_database),
            customer_intelligence=CustomerIntelligenceRepository(selected_database),
            memory=MemoryRepository(selected_database),
            campaign_plans=CampaignPlanRepository(selected_database),
            marketing_briefs=MarketingBriefRepository(selected_database),
            prompt_packs=PromptPackRepository(selected_database),
            compliance_rules=BrandRuleRepository(selected_database),
        )

    def build_context_assembler(self) -> AIContextAssembler:
        """Compose Company, Customer, and memory context from SQLite."""

        return AIContextAssembler(
            intelligence_repository=self.business_intelligence,
            customer_context_provider=CustomerContextProvider(
                repository=self.customer_intelligence,
            ),
            memory_repository=self.memory,
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
