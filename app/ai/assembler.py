"""AI context assembly for MarketingLabAI."""

from __future__ import annotations

from dataclasses import dataclass

from app.ai.context import CompanyBrainPromptBuilder
from app.ai.memory import MemoryPromptBuilder
from app.customer_intelligence.provider import CustomerContextProvider
from app.database.repositories import (
    BusinessIntelligenceRepository,
    MemoryRepository,
)
from app.product_intelligence.provider import ProductContextProvider


@dataclass(slots=True, frozen=True)
class AIContext:
    """Structured business context prepared for an AI request."""

    company_context: str = ""
    memory_context: str = ""
    memory_count: int = 0
    customer_context: str = ""
    product_context: str = ""

    @property
    def company_brain_included(self) -> bool:
        """Return whether Company Brain context is available."""

        return bool(self.company_context)

    @property
    def customer_intelligence_included(self) -> bool:
        """Return whether Customer Intelligence context is available."""

        return bool(self.customer_context)

    @property
    def memory_included(self) -> bool:
        """Return whether institutional memory is available."""

        return bool(self.memory_context)

    @property
    def product_intelligence_included(self) -> bool:
        """Return whether verified Product Intelligence is available."""

        return bool(self.product_context)


class AIContextAssembler:
    """Load and format context required by AI orchestration."""

    def __init__(
        self,
        *,
        intelligence_repository: BusinessIntelligenceRepository | None = None,
        memory_repository: MemoryRepository | None = None,
        customer_context_provider: CustomerContextProvider | None = None,
        product_context_provider: ProductContextProvider | None = None,
        company_brain_prompt_builder: CompanyBrainPromptBuilder | None = None,
        memory_prompt_builder: MemoryPromptBuilder | None = None,
        memory_limit: int = 10,
    ) -> None:
        if intelligence_repository is not None and not isinstance(
            intelligence_repository,
            BusinessIntelligenceRepository,
        ):
            raise TypeError(
                "intelligence_repository must be a " "BusinessIntelligenceRepository."
            )

        if memory_repository is not None and not isinstance(
            memory_repository,
            MemoryRepository,
        ):
            raise TypeError("memory_repository must be a MemoryRepository.")

        if customer_context_provider is not None and not isinstance(
            customer_context_provider,
            CustomerContextProvider,
        ):
            raise TypeError(
                "customer_context_provider must be a " "CustomerContextProvider."
            )

        if product_context_provider is not None and not isinstance(
            product_context_provider,
            ProductContextProvider,
        ):
            raise TypeError(
                "product_context_provider must be a ProductContextProvider."
            )

        if company_brain_prompt_builder is not None and not isinstance(
            company_brain_prompt_builder,
            CompanyBrainPromptBuilder,
        ):
            raise TypeError(
                "company_brain_prompt_builder must be a " "CompanyBrainPromptBuilder."
            )

        if memory_prompt_builder is not None and not isinstance(
            memory_prompt_builder,
            MemoryPromptBuilder,
        ):
            raise TypeError("memory_prompt_builder must be a MemoryPromptBuilder.")

        if memory_limit < 1:
            raise ValueError("memory_limit must be at least 1.")

        self.intelligence_repository = intelligence_repository
        self.memory_repository = memory_repository
        self.customer_context_provider = customer_context_provider
        self.product_context_provider = product_context_provider
        self.company_brain_prompt_builder = (
            company_brain_prompt_builder or CompanyBrainPromptBuilder()
        )
        self.memory_prompt_builder = memory_prompt_builder or MemoryPromptBuilder()
        self.memory_limit = memory_limit

    def build(
        self,
        *,
        brand_id: str,
        tenant_id: str = "default",
    ) -> AIContext:
        """Assemble available context for one brand."""

        if not isinstance(brand_id, str):
            raise TypeError("brand_id must be a string.")
        if not isinstance(tenant_id, str):
            raise TypeError("tenant_id must be a string.")

        brand_id = brand_id.strip()
        tenant_id = tenant_id.strip()

        if not brand_id or not tenant_id:
            raise ValueError("brand_id and tenant_id are required.")

        company_context = self._load_company_context(brand_id)
        customer_context = self._load_customer_context(brand_id)
        product_context = self._load_product_context(tenant_id, brand_id)
        memory_context = self._load_memory_context(brand_id)
        memory_count = len(memory_context.splitlines()) if memory_context else 0

        return AIContext(
            company_context=company_context,
            memory_context=memory_context,
            memory_count=memory_count,
            customer_context=customer_context,
            product_context=product_context,
        )

    def _load_product_context(self, tenant_id: str, brand_id: str) -> str:
        """Load tenant-scoped verified Product Intelligence when available."""

        provider = self.product_context_provider
        if provider is None:
            return ""
        return provider.build(tenant_id=tenant_id, brand_id=brand_id)

    def _load_company_context(
        self,
        brand_id: str,
    ) -> str:
        """Load Company Brain context when available."""

        repository = self.intelligence_repository

        if repository is None:
            return ""

        if not repository.exists(brand_id):
            return ""

        profile = repository.get(brand_id)

        return self.company_brain_prompt_builder.build(profile)

    def _load_customer_context(
        self,
        brand_id: str,
    ) -> str:
        """Load Customer Intelligence context when available."""

        provider = self.customer_context_provider

        if provider is None:
            return ""

        return provider.build(brand_id)

    def _load_memory_context(
        self,
        brand_id: str,
    ) -> str:
        """Load recent institutional memory when available."""

        repository = self.memory_repository

        if repository is None:
            return ""

        events = repository.list(
            brand_id,
            limit=self.memory_limit,
        )

        return self.memory_prompt_builder.build(
            events,
            limit=self.memory_limit,
        )
