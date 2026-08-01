"""Provider-neutral AI orchestration."""

from __future__ import annotations

from typing import Any

from app.ai.models import (
    IntelligenceRequest,
    IntelligenceResponse,
)
from app.ai.registry import IntelligenceProviderRegistry


class AIOrchestrator:
    """Coordinate application AI requests through the provider registry."""

    def __init__(
        self,
        registry: IntelligenceProviderRegistry,
    ) -> None:
        if not isinstance(
            registry,
            IntelligenceProviderRegistry,
        ):
            raise TypeError("registry must be an " "IntelligenceProviderRegistry.")

        self.registry = registry

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

        prompt = self._build_prompt(
            task=task,
            instructions=instructions,
        )

        request_metadata = dict(metadata or {})
        request_metadata.update(
            {
                "tenant_id": tenant_id,
                "brand_id": brand_id,
                "task": task,
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
        task: str,
        instructions: str,
    ) -> str:
        """Build the initial orchestration prompt."""

        if not instructions:
            return task

        return f"Task:\n{task}\n\n" f"Instructions:\n{instructions}"
