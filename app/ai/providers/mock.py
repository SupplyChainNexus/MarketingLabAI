"""Deterministic test provider."""

from __future__ import annotations

from collections.abc import Callable

from app.ai.models import (
    IntelligenceRequest,
    IntelligenceResponse,
)
from app.ai.provider import IntelligenceProvider

ResponseFactory = Callable[
    [IntelligenceRequest],
    IntelligenceResponse,
]


class MockIntelligenceProvider(IntelligenceProvider):
    """Deterministic provider for tests and local development."""

    def __init__(
        self,
        response_content: str = "Mock response",
        *,
        model: str = "mock-model",
        response_factory: ResponseFactory | None = None,
    ) -> None:
        self.response_content = response_content
        self.model = model
        self.response_factory = response_factory
        self.requests: list[IntelligenceRequest] = []

    @property
    def provider_name(self) -> str:
        return "mock"

    def generate(
        self,
        request: IntelligenceRequest,
    ) -> IntelligenceResponse:
        if not isinstance(request, IntelligenceRequest):
            raise TypeError("request must be an IntelligenceRequest.")

        self.requests.append(request)

        if self.response_factory is not None:
            return self.response_factory(request)

        return IntelligenceResponse(
            content=self.response_content,
            provider=self.provider_name,
            model=request.model or self.model,
            input_tokens=0,
            output_tokens=0,
            finish_reason="stop",
            metadata={
                "mock": True,
            },
        )
