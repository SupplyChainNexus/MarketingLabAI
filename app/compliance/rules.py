"""Business logic for versioning compliance rules."""

from __future__ import annotations

from typing import Any

from app.compliance.models import BrandRule, current_utc_timestamp


class RuleService:
    """Create controlled, immutable versions of brand rules."""

    _PROTECTED_FIELDS = {
        "rule_id",
        "brand_id",
        "version",
        "created_at",
        "updated_at",
    }

    def create_next_version(
        self,
        current_rule: BrandRule,
        **changes: Any,
    ) -> BrandRule:
        """Return a new rule version without changing the existing rule."""

        protected_changes = self._PROTECTED_FIELDS.intersection(changes)

        if protected_changes:
            fields = ", ".join(sorted(protected_changes))
            raise ValueError(f"Cannot directly change protected fields: {fields}.")

        payload = current_rule.to_dict()
        payload.update(changes)

        timestamp = current_utc_timestamp()
        payload["version"] = current_rule.version + 1
        payload["created_at"] = timestamp
        payload["updated_at"] = timestamp

        return BrandRule.from_dict(payload)

    def retire(self, current_rule: BrandRule) -> BrandRule:
        """Create a disabled successor version."""

        return self.create_next_version(current_rule, enabled=False)

    def activate(self, current_rule: BrandRule) -> BrandRule:
        """Create an enabled successor version."""

        return self.create_next_version(current_rule, enabled=True)
