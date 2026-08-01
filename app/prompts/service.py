"""Business workflow service for Prompt Packs."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from app.prompts.renderer import PromptPackRenderer
from app.prompts.selector import PromptPackSelector


@dataclass(slots=True, frozen=True)
class RenderedPrompt:
    """A rendered prompt with source-pack audit metadata."""

    content: str
    system_instruction: str
    prompt_pack_id: str
    version: int
    tenant_id: str
    brand_id: str | None
    task_type: str
    channel: str

    def __post_init__(self) -> None:
        """Validate the rendered prompt result."""

        if not self.content.strip():
            raise ValueError("content is required.")

        if not self.prompt_pack_id.strip():
            raise ValueError("prompt_pack_id is required.")

        if self.version < 1:
            raise ValueError("version must be at least 1.")

        if not self.tenant_id.strip():
            raise ValueError("tenant_id is required.")

        if not self.task_type.strip():
            raise ValueError("task_type is required.")


class PromptPackService:
    """Select and render Prompt Packs as one business operation."""

    def __init__(
        self,
        selector: PromptPackSelector,
        renderer: PromptPackRenderer | None = None,
    ) -> None:
        if not isinstance(selector, PromptPackSelector):
            raise TypeError("selector must be a PromptPackSelector.")

        if renderer is not None and not isinstance(
            renderer,
            PromptPackRenderer,
        ):
            raise TypeError("renderer must be a PromptPackRenderer.")

        self.selector = selector
        self.renderer = renderer or PromptPackRenderer()

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
        """Select and render the best matching Prompt Pack."""

        if not isinstance(values, Mapping):
            raise TypeError("values must be a mapping.")

        prompt_pack = self.selector.select(
            tenant_id=tenant_id,
            task_type=task_type,
            channel=channel,
            brand_id=brand_id,
            prompt_pack_id=prompt_pack_id,
        )

        content = self.renderer.render(
            prompt_pack,
            values,
        )

        return RenderedPrompt(
            content=content,
            system_instruction=prompt_pack.system_instruction,
            prompt_pack_id=prompt_pack.prompt_pack_id,
            version=prompt_pack.version,
            tenant_id=prompt_pack.tenant_id,
            brand_id=prompt_pack.brand_id,
            task_type=prompt_pack.task_type,
            channel=prompt_pack.channel,
        )
