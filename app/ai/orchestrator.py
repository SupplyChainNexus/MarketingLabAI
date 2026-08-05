"""Provider-neutral AI orchestration."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from app.ai.assembler import AIContext, AIContextAssembler
from app.ai.models import (
    IntelligenceRequest,
    IntelligenceResponse,
)
from app.ai.prompt import (
    PromptComposer,
    PromptSection,
)
from app.ai.registry import IntelligenceProviderRegistry


class AIOrchestrator:
    """Coordinate application AI requests through assembled context."""

    def __init__(
        self,
        registry: IntelligenceProviderRegistry,
        *,
        context_assembler: AIContextAssembler | None = None,
    ) -> None:
        if not isinstance(
            registry,
            IntelligenceProviderRegistry,
        ):
            raise TypeError("registry must be an " "IntelligenceProviderRegistry.")

        if context_assembler is not None and not isinstance(
            context_assembler,
            AIContextAssembler,
        ):
            raise TypeError("context_assembler must be an " "AIContextAssembler.")

        self.registry = registry
        self.context_assembler = context_assembler or AIContextAssembler()

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
        additional_sections: Sequence[PromptSection] = (),
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

        if isinstance(
            additional_sections,
            (str, bytes),
        ) or not isinstance(
            additional_sections,
            Sequence,
        ):
            raise TypeError("additional_sections must be a sequence.")

        validated_sections: list[PromptSection] = []

        for section in additional_sections:
            if not isinstance(section, PromptSection):
                raise TypeError(
                    "additional_sections must contain " "PromptSection objects."
                )

            validated_sections.append(section)

        context = self.context_assembler.build(
            tenant_id=tenant_id,
            brand_id=brand_id,
        )

        prompt = self._build_prompt(
            context=context,
            task=task,
            instructions=instructions,
            additional_sections=validated_sections,
        )

        request_metadata = dict(metadata or {})
        request_metadata.update(
            {
                "tenant_id": tenant_id,
                "brand_id": brand_id,
                "task": task,
                "company_brain_included": (context.company_brain_included),
                "customer_intelligence_included": (
                    context.customer_intelligence_included
                ),
                "product_intelligence_included": (
                    context.product_intelligence_included
                ),
                "memory_included": (context.memory_included),
                "memory_count": context.memory_count,
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

    @staticmethod
    def _build_prompt(
        *,
        context: AIContext,
        task: str,
        instructions: str,
        additional_sections: Sequence[PromptSection] = (),
    ) -> str:
        """Build a prompt from assembled context."""

        if not isinstance(context, AIContext):
            raise TypeError("context must be an AIContext.")

        composer = PromptComposer()

        composer.add(
            PromptSection(
                title="Company Context",
                content=context.company_context,
            )
        )
        composer.add(
            PromptSection(
                title="Customer Context",
                content=context.customer_context,
            )
        )
        composer.add(
            PromptSection(
                title="Verified Product and Offer Context",
                content=context.product_context,
            )
        )
        composer.add(
            PromptSection(
                title="Relevant Institutional Memory",
                content=context.memory_context,
            )
        )
        composer.add(
            PromptSection(
                title="Task",
                content=task,
            )
        )
        for section in additional_sections:
            composer.add(section)

        composer.add(
            PromptSection(
                title="Instructions",
                content=instructions,
            )
        )

        return composer.compose()
