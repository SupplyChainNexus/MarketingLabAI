"Business logic for immutable Marketing Brief versions."

from __future__ import annotations

from dataclasses import fields
from typing import Any

from app.database import SQLiteDatabase, bootstrap_database
from app.marketing_brief.models import (
    MarketingBrief,
    current_utc_timestamp,
)
from app.marketing_brief.repository import (
    MarketingBriefRepository,
)


class MarketingBriefService:
    "Create and persist controlled Marketing Brief versions."

    _PROTECTED_FIELDS = {
        "brief_id",
        "tenant_id",
        "brand_id",
        "version",
        "created_at",
        "updated_at",
    }
    _FIELD_NAMES = {field.name for field in fields(MarketingBrief)}

    def __init__(
        self,
        repository: MarketingBriefRepository | None = None,
    ) -> None:
        if repository is not None and not isinstance(
            repository,
            MarketingBriefRepository,
        ):
            raise TypeError("repository must be a MarketingBriefRepository.")

        self.repository = repository or MarketingBriefRepository(
            bootstrap_database(SQLiteDatabase())
        )

    def save(self, brief: MarketingBrief) -> None:
        "Persist a new immutable Marketing Brief version."

        self.repository.save(brief)

    def create_next_version(
        self,
        current_brief: MarketingBrief,
        **changes: Any,
    ) -> MarketingBrief:
        "Return a new brief version without mutating history."

        if not isinstance(current_brief, MarketingBrief):
            raise TypeError("current_brief must be a MarketingBrief.")

        protected_changes = self._PROTECTED_FIELDS.intersection(changes)

        if protected_changes:
            names = ", ".join(sorted(protected_changes))
            raise ValueError(
                "Cannot change protected Marketing Brief " f"fields: {names}."
            )

        unknown_changes = set(changes) - self._FIELD_NAMES

        if unknown_changes:
            names = ", ".join(sorted(unknown_changes))
            raise ValueError(f"Unknown Marketing Brief fields: {names}.")

        payload = current_brief.to_dict()
        payload.update(changes)
        payload["version"] = current_brief.version + 1
        payload["created_at"] = current_brief.created_at
        payload["updated_at"] = current_utc_timestamp()

        return MarketingBrief.from_dict(payload)

    def save_next_version(
        self,
        current_brief: MarketingBrief,
        **changes: Any,
    ) -> MarketingBrief:
        "Create and persist the next Marketing Brief version."

        next_version = self.create_next_version(
            current_brief,
            **changes,
        )
        self.repository.save(next_version)

        return next_version
