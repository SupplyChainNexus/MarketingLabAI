"""Versioned, provider-neutral C5 policy packs.

Policy packs are immutable inputs to validation.  They are deliberately kept
out of persistence and provider adapters until those boundaries are separately
authorized.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Any

from app.marketing_workflow.canonical import canonical_json_bytes

from .models import (
    GROUNDING_CANONICALIZATION_VERSION,
    GROUNDING_SCHEMA_VERSION,
)

POLICY_DOMAIN = "earthonox/mlai-033.3/content-policy-pack/MLAI-CP-1"


class PolicyError(ValueError):
    """Raised when an immutable policy pack is malformed or incompatible."""


@dataclass(frozen=True, slots=True)
class ChannelRule:
    """Additional deterministic requirements for one channel/content type."""

    channel: str
    content_type: str
    required_markers: tuple[str, ...] = ()
    required_anchor_categories: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        for field_name in ("channel", "content_type"):
            value = getattr(self, field_name)
            if not isinstance(value, str) or not value.strip():
                raise PolicyError(f"{field_name} must be non-empty")
            object.__setattr__(self, field_name, value.strip().casefold())
        for field_name in ("required_markers", "required_anchor_categories"):
            values = getattr(self, field_name)
            if not isinstance(values, tuple):
                values = tuple(values)
            if any(not isinstance(item, str) or not item.strip() for item in values):
                raise PolicyError(f"{field_name} must contain non-empty strings")
            object.__setattr__(
                self,
                field_name,
                tuple(item.strip().casefold() for item in values),
            )
        if len(set(self.required_markers)) != len(self.required_markers):
            raise PolicyError("required_markers must be unique")
        if len(set(self.required_anchor_categories)) != len(
            self.required_anchor_categories
        ):
            raise PolicyError("required_anchor_categories must be unique")

    def to_canonical(self) -> dict[str, Any]:
        return {
            "channel": self.channel,
            "content_type": self.content_type,
            "required_anchor_categories": list(self.required_anchor_categories),
            "required_markers": list(self.required_markers),
        }


@dataclass(frozen=True, slots=True)
class TransformationRule:
    """A deterministic, unit-preserving derived-claim transformation."""

    transformation_id: str
    input_units: tuple[str, ...]
    output_unit: str
    deterministic: bool = True
    allows_extrapolation: bool = False

    def __post_init__(self) -> None:
        if not isinstance(self.transformation_id, str) or not self.transformation_id:
            raise PolicyError("transformation_id must be non-empty")
        units = tuple(self.input_units)
        if not units or any(not isinstance(item, str) or not item for item in units):
            raise PolicyError("input_units must contain non-empty strings")
        if not isinstance(self.output_unit, str) or not self.output_unit:
            raise PolicyError("output_unit must be non-empty")
        if not isinstance(self.deterministic, bool):
            raise PolicyError("deterministic must be boolean")
        if not isinstance(self.allows_extrapolation, bool):
            raise PolicyError("allows_extrapolation must be boolean")
        object.__setattr__(self, "input_units", units)

    def to_canonical(self) -> dict[str, Any]:
        return {
            "allows_extrapolation": self.allows_extrapolation,
            "deterministic": self.deterministic,
            "input_units": list(self.input_units),
            "output_unit": self.output_unit,
            "transformation_id": self.transformation_id,
        }


@dataclass(frozen=True, slots=True)
class PolicyPack:
    """An append-only policy pack compatible with one grounding contract."""

    name: str
    version: int
    effective_date: str
    channel_rules: tuple[ChannelRule, ...] = ()
    transformations: tuple[TransformationRule, ...] = ()
    grounding_schema_version: int = GROUNDING_SCHEMA_VERSION
    grounding_canonicalization_version: str = GROUNDING_CANONICALIZATION_VERSION
    anchor_floor: int = 3
    category_floor: int = 2
    _digest: str = ""

    def __post_init__(self) -> None:
        if not isinstance(self.name, str) or not self.name.strip():
            raise PolicyError("policy name must be non-empty")
        if type(self.version) is not int or self.version < 1:
            raise PolicyError("policy version must be a positive integer")
        if not isinstance(self.effective_date, str) or not self.effective_date.strip():
            raise PolicyError("effective_date must be non-empty")
        if self.grounding_schema_version != GROUNDING_SCHEMA_VERSION:
            raise PolicyError("grounding schema version is incompatible")
        if (
            self.grounding_canonicalization_version
            != GROUNDING_CANONICALIZATION_VERSION
        ):
            raise PolicyError("grounding canonicalization is incompatible")
        if self.anchor_floor != 3 or self.category_floor != 2:
            raise PolicyError(
                "the C5 safety floor is fixed at 3 anchors across 2 categories"
            )
        rules = tuple(self.channel_rules)
        transforms = tuple(self.transformations)
        if any(not isinstance(item, ChannelRule) for item in rules):
            raise PolicyError("channel_rules must contain ChannelRule values")
        if any(not isinstance(item, TransformationRule) for item in transforms):
            raise PolicyError("transformations must contain TransformationRule values")
        if len({(item.channel, item.content_type) for item in rules}) != len(rules):
            raise PolicyError("channel/content_type rules must be unique")
        if len({item.transformation_id for item in transforms}) != len(transforms):
            raise PolicyError("transformation IDs must be unique")
        object.__setattr__(self, "channel_rules", rules)
        object.__setattr__(self, "transformations", transforms)
        digest = hashlib.sha256(
            POLICY_DOMAIN.encode("ascii")
            + b"\n"
            + canonical_json_bytes(self._payload())
        ).hexdigest()
        if self._digest and self._digest != digest:
            raise PolicyError("policy digest is immutable")
        object.__setattr__(self, "_digest", digest)

    @classmethod
    def v1(
        cls,
        *,
        effective_date: str = "pending",
        channel_rules: tuple[ChannelRule, ...] = (),
        transformations: tuple[TransformationRule, ...] = (),
    ) -> "PolicyPack":
        return cls(
            name="c5-content-validation",
            version=1,
            effective_date=effective_date,
            channel_rules=channel_rules,
            transformations=transformations,
        )

    @property
    def digest(self) -> str:
        return self._digest

    def channel_rule(self, channel: str, content_type: str) -> ChannelRule | None:
        key = (channel.casefold(), content_type.casefold())
        return next(
            (
                rule
                for rule in self.channel_rules
                if (rule.channel, rule.content_type) == key
            ),
            None,
        )

    def transformation(self, transformation_id: str) -> TransformationRule | None:
        return next(
            (
                item
                for item in self.transformations
                if item.transformation_id == transformation_id
            ),
            None,
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "anchor_floor": self.anchor_floor,
            "category_floor": self.category_floor,
            "channel_rules": [item.to_canonical() for item in self.channel_rules],
            "effective_date": self.effective_date,
            "grounding_canonicalization_version": self.grounding_canonicalization_version,
            "grounding_schema_version": self.grounding_schema_version,
            "name": self.name,
            "record_kind": "content_policy_pack",
            "transformations": [item.to_canonical() for item in self.transformations],
            "version": self.version,
        }


class PolicyPackRegistry:
    """In-memory append-only policy registry for one validation process."""

    def __init__(self) -> None:
        self._packs: dict[tuple[str, int], PolicyPack] = {}

    def register(self, pack: PolicyPack) -> None:
        key = (pack.name, pack.version)
        existing = self._packs.get(key)
        if existing is not None and existing.digest != pack.digest:
            raise PolicyError("policy versions are immutable")
        self._packs[key] = pack

    def get(self, name: str, version: int) -> PolicyPack:
        try:
            return self._packs[(name, version)]
        except KeyError as error:
            raise PolicyError("policy version is unavailable") from error

    def rollback(self, name: str, version: int) -> PolicyPack:
        """Select an older approved pack for new requests only."""

        return self.get(name, version)
