"""Gemini adapter for the provider-neutral intelligence contract."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from app.ai.capabilities import ProviderCapabilities
from app.ai.gemini_client import (
    get_gemini_client,
)
from app.ai.models import (
    IntelligenceRequest,
    IntelligenceResponse,
)
from app.ai.provider import IntelligenceProvider


@runtime_checkable
class GeminiTextClient(Protocol):
    """Minimum client contract required by the Gemini adapter."""

    @property
    def settings(self) -> object:
        """Return client configuration containing gemini_model."""

    def generate_text(
        self,
        prompt: str,
    ) -> str:
        """Generate text from Gemini."""


class GeminiIntelligenceProvider(IntelligenceProvider):
    """Expose Gemini through the provider-neutral AI contract."""

    def __init__(
        self,
        client: GeminiTextClient | None = None,
    ) -> None:
        if client is not None and not isinstance(
            client,
            GeminiTextClient,
        ):
            raise TypeError("client must implement GeminiTextClient.")

        self._client = client or get_gemini_client()

        model = self._configured_model()

        self._capabilities = ProviderCapabilities(
            available_models=[
                model,
            ],
            metadata={
                "adapter": "gemini",
            },
        )

    @property
    def provider_name(self) -> str:
        """Return the stable Gemini provider identifier."""

        return "gemini"

    @property
    def capabilities(self) -> ProviderCapabilities:
        """Return conservatively declared Gemini capabilities."""

        return self._capabilities

    @property
    def client(self) -> GeminiTextClient:
        """Return the configured low-level Gemini client."""

        return self._client

    def generate(
        self,
        request: IntelligenceRequest,
    ) -> IntelligenceResponse:
        """Generate and normalize a Gemini response."""

        if not isinstance(
            request,
            IntelligenceRequest,
        ):
            raise TypeError("request must be an IntelligenceRequest.")

        configured_model = self._configured_model()
        selected_model = request.model if request.model else configured_model

        if not self.capabilities.supports_model(selected_model):
            raise ValueError(f"Gemini model '{selected_model}' " "is not configured.")

        provider_prompt = self._compose_prompt(request)

        content = self._client.generate_text(provider_prompt).strip()

        if not content:
            raise RuntimeError("Gemini provider returned empty content.")

        return IntelligenceResponse(
            content=content,
            provider=self.provider_name,
            model=selected_model,
            input_tokens=None,
            output_tokens=None,
            finish_reason="stop",
            metadata={
                "adapter": "gemini",
                "request_metadata": dict(request.metadata),
            },
        )

    def _configured_model(self) -> str:
        """Return the model configured on the low-level client."""

        settings = getattr(
            self._client,
            "settings",
            None,
        )
        model = getattr(
            settings,
            "gemini_model",
            "",
        )

        if not isinstance(model, str):
            raise TypeError("Gemini client model must be a string.")

        cleaned_model = model.strip()

        if not cleaned_model:
            raise ValueError("Gemini client model is required.")

        return cleaned_model

    @staticmethod
    def _compose_prompt(
        request: IntelligenceRequest,
    ) -> str:
        """Compose Gemini input without losing system instructions."""

        if not request.system_instruction:
            return request.prompt

        return (
            "System Instruction\n"
            "------------------\n"
            f"{request.system_instruction}\n\n"
            "User Request\n"
            "------------\n"
            f"{request.prompt}"
        )
