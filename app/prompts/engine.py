"""Public Prompt Engine facade."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from app.prompts.service import (
    PromptPackService,
    RenderedPrompt,
)


class PromptEngine:
    """Stable public API for MarketingLabAI prompt rendering."""

    def __init__(
        self,
        service: PromptPackService,
    ) -> None:
        """Create a Prompt Engine."""

        if not isinstance(service, PromptPackService):
            raise TypeError("service must be a PromptPackService.")

        self._service = service

    def render(
        self,
        *,
        tenant_id: str,
        task_type: str,
        values: Mapping[str, Any],
        channel: str = "",
        brand_id: str | None = None,
        prompt_pack_id: str | None = None,
    ) -> RenderedPrompt:
        """Render the best matching Prompt Pack."""

        return self._service.render(
            tenant_id=tenant_id,
            task_type=task_type,
            values=values,
            channel=channel,
            brand_id=brand_id,
            prompt_pack_id=prompt_pack_id,
        )
