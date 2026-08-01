"""Provider-neutral AI orchestration."""

from __future__ import annotations

from typing import Any

from app.ai.context import CompanyBrainPromptBuilder
from app.ai.models import (
    IntelligenceRequest,
    IntelligenceResponse,
)
from app.ai.prompt import (
    PromptComposer,
    PromptSection,
)
from app.ai.registry import IntelligenceProviderRegistry
from app.database.repositories import (
    BusinessIntelligenceRepository,
)


class AIOrchestrator:
    """Coordinate application AI requests through the provider registry."""

    def __init__(
        self,
        registry: IntelligenceProviderRegistry,
        *,
        intelligence_repository: BusinessIntelligenceRepository | None = None,
        company_brain_prompt_builder: CompanyBrainPromptBuilder | None = None,
    ) -> None:
        if not isinstance(
            registry,
            IntelligenceProviderRegistry,
        ):
            raise TypeError("registry must be an " "IntelligenceProviderRegistry.")

        if intelligence_repository is not None and not isinstance(
            intelligence_repository,
            BusinessIntelligenceRepository,
        ):
            raise TypeError(
                "intelligence_repository must be a " "BusinessIntelligenceRepository."
            )

        if company_brain_prompt_builder is not None and not isinstance(
            company_brain_prompt_builder,
            CompanyBrainPromptBuilder,
        ):
            raise TypeError(
                "company_brain_prompt_builder must be a " "CompanyBrainPromptBuilder."
            )

        self.registry = registry
        self.intelligence_repository = intelligence_repository
        self.company_brain_prompt_builder = (
            company_brain_prompt_builder or CompanyBrainPromptBuilder()
        )

    def generate(
        self,
        *,
        tenant_id: str,
        brand_id: str,
        task: str,
        instructions: str = "",
        system_instruction: str = "",
        provider_name: str | None = None,
        model: str = "",
        temperature: float | None = None,
        max_output_tokens: int | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> IntelligenceResponse:
        """Generate a provider-neutral intelligence response."""

        tenant_id = tenant_id.strip()
        brand_id = brand_id.strip()
        task = task.strip()
        instructions = instructions.strip()
        system_instruction = system_instruction.strip()
        model = model.strip()

        if provider_name is not None:
            provider_name = provider_name.strip()

        if not tenant_id:
            raise ValueError("tenant_id is required.")

        if not brand_id:
            raise ValueError("brand_id is required.")

        if not task:
            raise ValueError("task is required.")

        if provider_name == "":
            raise ValueError("provider_name cannot be blank.")

        if metadata is not None and not isinstance(
            metadata,
            dict,
        ):
            raise TypeError("metadata must be a dictionary.")

        company_context = self._load_company_context(brand_id)

        prompt = self._build_prompt(
            task=task,
            instructions=instructions,
            company_context=company_context,
        )

        request_metadata = dict(metadata or {})
        request_metadata.update(
            {
                "tenant_id": tenant_id,
                "brand_id": brand_id,
                "task": task,
                "company_brain_included": bool(company_context),
            }
        )

        request = IntelligenceRequest(
            prompt=prompt,
            system_instruction=system_instruction,
            model=model,
            temperature=temperature,
            max_output_tokens=max_output_tokens,
            metadata=request_metadata,
        )

        return self.registry.generate(
            request,
            provider_name=provider_name,
        )

    def _load_company_context(
        self,
        brand_id: str,
    ) -> str:
        """Load and format Company Brain context when available."""

        repository = self.intelligence_repository

        if repository is None:
            return ""

        if not repository.exists(brand_id):
            return ""

        profile = repository.get(brand_id)

        return self.company_brain_prompt_builder.build(profile)

    @staticmethod
    def _build_prompt(
        *,
        task: str,
        instructions: str,
        company_context: str = "",
    ) -> str:
        """Build the orchestration prompt."""

        composer = PromptComposer()

        composer.add(
            PromptSection(
                title="Company Context",
                content=company_context,
            )
        )
        composer.add(
            PromptSection(
                title="Task",
                content=task,
            )
        )
        composer.add(
            PromptSection(
                title="Instructions",
                content=instructions,
            )
        )

        return composer.compose()
