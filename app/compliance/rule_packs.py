"""Configurable compliance rule-pack loading and installation."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from app.compliance.engine import ComplianceEngine, RuleEvaluator
from app.compliance.evaluators import (
    forbidden_regex_evaluator,
    maximum_keyword_count_evaluator,
    maximum_length_evaluator,
    required_phrase_evaluator,
    required_url_evaluator,
)
from app.compliance.models import BrandRule
from app.compliance.repository import BrandRuleRepository
from app.compliance.rules import RuleService


@dataclass(slots=True)
class RulePackEntry:
    """One configurable rule and its deterministic evaluator."""

    rule: BrandRule
    evaluator_type: str
    evaluator_config: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.evaluator_type = self.evaluator_type.strip()

        if not self.evaluator_type:
            raise ValueError("evaluator_type is required.")

        if not isinstance(self.evaluator_config, dict):
            raise ValueError("evaluator_config must be an object.")

        self.evaluator_config = dict(self.evaluator_config)


@dataclass(slots=True)
class RulePack:
    """A validated collection of compliance rules."""

    pack_id: str
    name: str
    description: str
    rules: list[RulePackEntry]
    version: int = 1

    def __post_init__(self) -> None:
        self.pack_id = self.pack_id.strip()
        self.name = self.name.strip()
        self.description = self.description.strip()

        if not self.pack_id:
            raise ValueError("pack_id is required.")

        if not self.name:
            raise ValueError("name is required.")

        if self.version < 1:
            raise ValueError("version must be at least 1.")

        if not self.rules:
            raise ValueError("rules must contain at least one rule.")

        rule_ids = [entry.rule.rule_id for entry in self.rules]

        if len(rule_ids) != len(set(rule_ids)):
            raise ValueError("Rule pack contains duplicate rule IDs.")


@dataclass(slots=True)
class RulePackInstallResult:
    """Summary of installing a rule pack."""

    created: list[BrandRule] = field(default_factory=list)
    updated: list[BrandRule] = field(default_factory=list)
    unchanged: list[BrandRule] = field(default_factory=list)

    @property
    def installed_rules(self) -> list[BrandRule]:
        return [*self.created, *self.updated, *self.unchanged]


class RulePackLoader:
    """Load safe, data-driven compliance rule packs."""

    _EVALUATOR_FACTORIES = {
        "required_phrase": required_phrase_evaluator,
        "required_url": required_url_evaluator,
        "maximum_length": maximum_length_evaluator,
        "forbidden_regex": forbidden_regex_evaluator,
        "maximum_keyword_count": maximum_keyword_count_evaluator,
    }

    def load_file(
        self,
        path: str | Path,
        *,
        brand_id: str,
    ) -> RulePack:
        rule_pack_path = Path(path)

        try:
            payload = json.loads(rule_pack_path.read_text(encoding="utf-8"))
        except OSError as error:
            raise ValueError(f"Unable to read rule pack: {rule_pack_path}") from error
        except json.JSONDecodeError as error:
            raise ValueError(f"Rule pack contains invalid JSON: {error}") from error

        return self.load_dict(payload, brand_id=brand_id)

    def load_dict(
        self,
        payload: dict[str, Any],
        *,
        brand_id: str,
    ) -> RulePack:
        if not isinstance(payload, dict):
            raise ValueError("Rule pack must be a JSON object.")

        cleaned_brand_id = brand_id.strip()

        if not cleaned_brand_id:
            raise ValueError("brand_id is required.")

        rules_payload = payload.get("rules")

        if not isinstance(rules_payload, list):
            raise ValueError("rules must be a list.")

        entries = [
            self._load_entry(
                rule_payload,
                brand_id=cleaned_brand_id,
            )
            for rule_payload in rules_payload
        ]

        return RulePack(
            pack_id=self._required_string(payload, "pack_id"),
            name=self._required_string(payload, "name"),
            description=self._optional_string(
                payload,
                "description",
            ),
            version=self._positive_integer(
                payload.get("version", 1),
                "version",
            ),
            rules=entries,
        )

    def build_evaluator(
        self,
        entry: RulePackEntry,
    ) -> RuleEvaluator:
        factory = self._EVALUATOR_FACTORIES.get(entry.evaluator_type)

        if factory is None:
            supported = ", ".join(sorted(self._EVALUATOR_FACTORIES))
            raise ValueError(
                f"Unsupported evaluator_type "
                f"'{entry.evaluator_type}'. "
                f"Supported values: {supported}."
            )

        try:
            return factory(**entry.evaluator_config)
        except TypeError as error:
            raise ValueError(
                f"Invalid evaluator configuration for "
                f"'{entry.rule.rule_id}': {error}"
            ) from error

    def register_evaluators(
        self,
        rule_pack: RulePack,
        engine: ComplianceEngine,
    ) -> None:
        for entry in rule_pack.rules:
            engine.register_evaluator(
                entry.rule.rule_id,
                self.build_evaluator(entry),
            )

    def _load_entry(
        self,
        payload: Any,
        *,
        brand_id: str,
    ) -> RulePackEntry:
        if not isinstance(payload, dict):
            raise ValueError("Each rule must be an object.")

        rule_payload = payload.get("rule")

        if not isinstance(rule_payload, dict):
            raise ValueError("Each rule entry must contain a rule object.")

        configured_brand_id = rule_payload.get("brand_id")

        if configured_brand_id is not None and configured_brand_id != brand_id:
            raise ValueError("Rule-pack rules cannot override brand_id.")

        normalised_rule_payload = dict(rule_payload)
        normalised_rule_payload["brand_id"] = brand_id

        evaluator_type = self._required_string(
            payload,
            "evaluator_type",
        )
        evaluator_config = payload.get(
            "evaluator_config",
            {},
        )

        if not isinstance(evaluator_config, dict):
            raise ValueError("evaluator_config must be an object.")

        entry = RulePackEntry(
            rule=BrandRule.from_dict(normalised_rule_payload),
            evaluator_type=evaluator_type,
            evaluator_config=evaluator_config,
        )

        self.build_evaluator(entry)

        return entry

    @staticmethod
    def _required_string(
        payload: dict[str, Any],
        field_name: str,
    ) -> str:
        value = payload.get(field_name)

        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"{field_name} is required.")

        return value.strip()

    @staticmethod
    def _optional_string(
        payload: dict[str, Any],
        field_name: str,
    ) -> str:
        value = payload.get(field_name, "")

        if not isinstance(value, str):
            raise ValueError(f"{field_name} must be a string.")

        return value.strip()

    @staticmethod
    def _positive_integer(
        value: Any,
        field_name: str,
    ) -> int:
        if isinstance(value, bool) or not isinstance(value, int):
            raise ValueError(f"{field_name} must be an integer.")

        if value < 1:
            raise ValueError(f"{field_name} must be at least 1.")

        return value


class RulePackInstaller:
    """Install rule packs while preserving version history."""

    def __init__(
        self,
        repository: BrandRuleRepository,
        rule_service: RuleService | None = None,
    ) -> None:
        self.repository = repository
        self.rule_service = rule_service or RuleService()

    def install(
        self,
        rule_pack: RulePack,
    ) -> RulePackInstallResult:
        result = RulePackInstallResult()

        for entry in rule_pack.rules:
            incoming_rule = entry.rule

            if not self.repository.exists(incoming_rule.rule_id):
                self.repository.save(incoming_rule)
                result.created.append(incoming_rule)
                continue

            current_rule = self.repository.get(incoming_rule.rule_id)

            if current_rule.brand_id != incoming_rule.brand_id:
                raise ValueError(
                    f"Rule '{incoming_rule.rule_id}' already "
                    "belongs to another brand."
                )

            changes = self._changed_fields(
                current_rule,
                incoming_rule,
            )

            if not changes:
                result.unchanged.append(current_rule)
                continue

            updated_rule = self.rule_service.create_next_version(
                current_rule,
                **changes,
            )
            self.repository.save(updated_rule)
            result.updated.append(updated_rule)

        return result

    @staticmethod
    def _changed_fields(
        current_rule: BrandRule,
        incoming_rule: BrandRule,
    ) -> dict[str, Any]:
        current_payload = current_rule.to_dict()
        incoming_payload = incoming_rule.to_dict()

        ignored_fields = {
            "rule_id",
            "brand_id",
            "version",
            "created_at",
            "updated_at",
        }

        return {
            field_name: incoming_value
            for field_name, incoming_value in incoming_payload.items()
            if field_name not in ignored_fields
            and current_payload[field_name] != incoming_value
        }
