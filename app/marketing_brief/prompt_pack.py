"""Integrate Marketing Briefs with versioned Prompt Packs."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from app.marketing_brief.models import MarketingBrief
from app.prompts.models import PromptPack
from app.prompts.renderer import PromptPackRenderer
from app.prompts.selector import PromptPackSelector
from app.prompts.service import RenderedPrompt


class MarketingBriefPromptValuesMapper:
    """Map a Marketing Brief into declared Prompt Pack variables."""

    def map(
        self,
        brief: MarketingBrief,
        variables: Sequence[str],
    ) -> dict[str, str]:
        """Return values only for variables declared by a Prompt Pack."""

        if not isinstance(brief, MarketingBrief):
            raise TypeError("brief must be a MarketingBrief.")

        if isinstance(variables, (str, bytes)):
            raise TypeError("variables must be a sequence of strings.")

        if not isinstance(variables, Sequence):
            raise TypeError("variables must be a sequence of strings.")

        available_values = self._available_values(brief)
        mapped_values: dict[str, str] = {}
        seen_variables: set[str] = set()

        for variable in variables:
            if not isinstance(variable, str):
                raise TypeError("variables must contain strings.")

            cleaned_variable = variable.strip()

            if not cleaned_variable:
                raise ValueError("variables cannot contain blank values.")

            if cleaned_variable in seen_variables:
                continue

            seen_variables.add(cleaned_variable)

            if cleaned_variable not in available_values:
                raise ValueError(
                    "Marketing Brief does not support Prompt Pack "
                    f"variable '{cleaned_variable}'."
                )

            value = available_values[cleaned_variable]

            if not value.strip():
                raise ValueError(
                    "Marketing Brief cannot supply a non-empty value "
                    f"for Prompt Pack variable '{cleaned_variable}'."
                )

            mapped_values[cleaned_variable] = value

        return mapped_values

    @staticmethod
    def supported_variables() -> tuple[str, ...]:
        """Return supported Prompt Pack variable names."""

        return (
            "brief_id",
            "brief_version",
            "brief_name",
            "objective",
            "audience",
            "offer",
            "key_message",
            "call_to_action",
            "channels",
            "deliverables",
            "constraints",
            "success_metrics",
            "customer_segment_ids",
            "product_ids",
            "evidence",
            "assumptions",
            "notes",
            "status",
        )

    def _available_values(
        self,
        brief: MarketingBrief,
    ) -> dict[str, str]:
        return {
            "brief_id": brief.brief_id,
            "brief_version": str(brief.version),
            "brief_name": brief.name,
            "objective": brief.objective,
            "audience": brief.audience,
            "offer": brief.offer,
            "key_message": brief.key_message,
            "call_to_action": brief.call_to_action,
            "channels": self._comma_list(brief.channels),
            "deliverables": self._bullet_list(brief.deliverables),
            "constraints": self._bullet_list(brief.constraints),
            "success_metrics": self._bullet_list(brief.success_metrics),
            "customer_segment_ids": self._comma_list(brief.customer_segment_ids),
            "product_ids": self._comma_list(brief.product_ids),
            "evidence": self._evidence_list(brief),
            "assumptions": self._bullet_list(brief.assumptions),
            "notes": brief.notes,
            "status": brief.status.value,
        }

    @staticmethod
    def _comma_list(values: Sequence[str]) -> str:
        return ", ".join(values)

    @staticmethod
    def _bullet_list(values: Sequence[str]) -> str:
        return "\n".join(f"- {value}" for value in values)

    @staticmethod
    def _evidence_list(brief: MarketingBrief) -> str:
        return "\n".join(
            "- "
            f"[{item.source_type}:{item.source_id}] "
            f"{item.summary} "
            f"(confidence: {item.confidence:.2f})"
            for item in brief.evidence
        )


@dataclass(slots=True, frozen=True)
class RenderedMarketingBriefPrompt:
    """Rendered prompt plus Marketing Brief and Prompt Pack audit data."""

    prompt: RenderedPrompt
    brief_id: str
    brief_version: int
    brief_status: str
    mapped_variables: tuple[str, ...]

    def __post_init__(self) -> None:
        """Validate the integration result."""

        if not isinstance(self.prompt, RenderedPrompt):
            raise TypeError("prompt must be a RenderedPrompt.")

        if not self.brief_id.strip():
            raise ValueError("brief_id is required.")

        if isinstance(self.brief_version, bool):
            raise TypeError("brief_version must be an integer.")

        if not isinstance(self.brief_version, int):
            raise TypeError("brief_version must be an integer.")

        if self.brief_version < 1:
            raise ValueError("brief_version must be at least 1.")

        if not self.brief_status.strip():
            raise ValueError("brief_status is required.")

        if not isinstance(self.mapped_variables, tuple):
            raise TypeError("mapped_variables must be a tuple.")

        if any(
            not isinstance(variable, str) or not variable.strip()
            for variable in self.mapped_variables
        ):
            raise ValueError("mapped_variables must contain non-empty strings.")


class MarketingBriefPromptPackService:
    """Select and render Prompt Packs from Marketing Brief data."""

    def __init__(
        self,
        selector: PromptPackSelector,
        renderer: PromptPackRenderer | None = None,
        mapper: MarketingBriefPromptValuesMapper | None = None,
    ) -> None:
        """Create the Marketing Brief Prompt Pack service."""

        if not isinstance(selector, PromptPackSelector):
            raise TypeError("selector must be a PromptPackSelector.")

        if renderer is not None and not isinstance(
            renderer,
            PromptPackRenderer,
        ):
            raise TypeError("renderer must be a PromptPackRenderer.")

        if mapper is not None and not isinstance(
            mapper,
            MarketingBriefPromptValuesMapper,
        ):
            raise TypeError("mapper must be a " "MarketingBriefPromptValuesMapper.")

        self.selector = selector
        self.renderer = renderer or PromptPackRenderer()
        self.mapper = mapper or MarketingBriefPromptValuesMapper()

    def render(
        self,
        brief: MarketingBrief,
        *,
        task_type: str,
        channel: str = "",
        prompt_pack_id: str | None = None,
    ) -> RenderedMarketingBriefPrompt:
        """Select and render the best Prompt Pack for a brief."""

        if not isinstance(brief, MarketingBrief):
            raise TypeError("brief must be a MarketingBrief.")

        prompt_pack = self.selector.select(
            tenant_id=brief.tenant_id,
            task_type=task_type,
            channel=channel,
            brand_id=brief.brand_id,
            prompt_pack_id=prompt_pack_id,
        )

        values = self.mapper.map(
            brief,
            prompt_pack.variables,
        )
        content = self.renderer.render(
            prompt_pack,
            values,
        )

        rendered_prompt = self._result_from_pack(
            prompt_pack,
            content,
        )

        return RenderedMarketingBriefPrompt(
            prompt=rendered_prompt,
            brief_id=brief.brief_id,
            brief_version=brief.version,
            brief_status=brief.status.value,
            mapped_variables=tuple(values),
        )

    @staticmethod
    def _result_from_pack(
        prompt_pack: PromptPack,
        content: str,
    ) -> RenderedPrompt:
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
