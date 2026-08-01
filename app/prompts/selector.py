"""Deterministic Prompt Pack selection."""

from __future__ import annotations

from app.prompts.models import PromptPack
from app.prompts.repository import PromptPackRepository


class PromptPackSelector:
    """Select the best enabled Prompt Pack for a task."""

    def __init__(
        self,
        repository: PromptPackRepository,
    ) -> None:
        if not isinstance(
            repository,
            PromptPackRepository,
        ):
            raise TypeError("repository must be a PromptPackRepository.")

        self.repository = repository

    def select(
        self,
        *,
        tenant_id: str,
        task_type: str,
        channel: str = "",
        brand_id: str | None = None,
        prompt_pack_id: str | None = None,
    ) -> PromptPack:
        """Return the best matching enabled Prompt Pack."""

        tenant_id = self._required_text(
            "tenant_id",
            tenant_id,
        )
        task_type = self._required_text(
            "task_type",
            task_type,
        )
        channel = self._optional_text(
            "channel",
            channel,
        )
        brand_id = self._optional_text(
            "brand_id",
            brand_id,
        )
        prompt_pack_id = self._optional_text(
            "prompt_pack_id",
            prompt_pack_id,
        )

        candidates = self.repository.list_for_tenant(
            tenant_id,
            task_type=task_type,
            channel=channel or None,
            enabled_only=True,
        )

        candidates = [
            pack
            for pack in candidates
            if pack.brand_id is None or pack.brand_id == brand_id
        ]

        if brand_id is None:
            candidates = [pack for pack in candidates if pack.brand_id is None]

        if prompt_pack_id is not None:
            candidates = [
                pack for pack in candidates if pack.prompt_pack_id == prompt_pack_id
            ]

        if not candidates:
            raise FileNotFoundError(
                self._missing_message(
                    tenant_id=tenant_id,
                    task_type=task_type,
                    channel=channel,
                    brand_id=brand_id,
                    prompt_pack_id=prompt_pack_id,
                )
            )

        if brand_id is not None:
            brand_candidates = [
                pack for pack in candidates if pack.brand_id == brand_id
            ]

            if brand_candidates:
                candidates = brand_candidates
            else:
                candidates = [pack for pack in candidates if pack.brand_id is None]

        if len(candidates) > 1:
            identifiers = ", ".join(sorted(pack.prompt_pack_id for pack in candidates))

            raise ValueError(
                "Prompt Pack selection is ambiguous. " f"Matching packs: {identifiers}."
            )

        return candidates[0]

    @staticmethod
    def _required_text(
        field_name: str,
        value: str,
    ) -> str:
        if not isinstance(value, str):
            raise TypeError(f"{field_name} must be a string.")

        cleaned_value = value.strip()

        if not cleaned_value:
            raise ValueError(f"{field_name} is required.")

        return cleaned_value

    @staticmethod
    def _optional_text(
        field_name: str,
        value: str | None,
    ) -> str | None:
        if value is None:
            return None

        if not isinstance(value, str):
            raise TypeError(f"{field_name} must be a string.")

        return value.strip() or None

    @staticmethod
    def _missing_message(
        *,
        tenant_id: str,
        task_type: str,
        channel: str | None,
        brand_id: str | None,
        prompt_pack_id: str | None,
    ) -> str:
        details = [
            f"tenant '{tenant_id}'",
            f"task type '{task_type}'",
        ]

        if channel:
            details.append(f"channel '{channel}'")

        if brand_id:
            details.append(f"brand '{brand_id}'")

        if prompt_pack_id:
            details.append(f"Prompt Pack ID '{prompt_pack_id}'")

        return "No enabled Prompt Pack matches " + ", ".join(details) + "."
