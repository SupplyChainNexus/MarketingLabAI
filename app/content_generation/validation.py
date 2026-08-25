"""Pure deterministic validation over immutable C5 grounding material."""

from __future__ import annotations

import unicodedata
from dataclasses import dataclass
from enum import StrEnum
from typing import Any, Sequence

from .grounding import GroundingError, load_grounding_snapshot
from .models import SourceReference
from .policy import PolicyPack


class ValidationOutcome(StrEnum):
    APPROVED = "approved"
    REVIEW_REQUIRED = "review_required"
    BLOCKED = "blocked"


class ClaimKind(StrEnum):
    DIRECT = "direct"
    DERIVED = "derived"


class ClaimConfidence(StrEnum):
    SUPPORTED = "supported"
    UNKNOWN = "unknown"
    LOW = "low_confidence"


class ClaimRisk(StrEnum):
    NORMAL = "normal"
    HIGH = "high"


@dataclass(frozen=True, slots=True)
class GroundingAnchor:
    """A deterministic content anchor bound to one snapshot source."""

    text: str
    source: SourceReference

    def __post_init__(self) -> None:
        if not isinstance(self.text, str) or not self.text.strip():
            raise TypeError("anchor text must be non-empty")
        if not isinstance(self.source, SourceReference):
            raise TypeError("anchor source must be a SourceReference")
        object.__setattr__(self, "text", self.text.strip())


@dataclass(frozen=True, slots=True)
class GroundedClaim:
    """Untrusted structured claim material requiring deterministic validation."""

    claim_id: str
    text: str
    kind: ClaimKind | str
    confidence: ClaimConfidence | str
    risk: ClaimRisk | str = ClaimRisk.NORMAL
    evidence: tuple[SourceReference, ...] = ()
    transformation_id: str = ""
    derived_from: tuple[str, ...] = ()
    input_units: tuple[str, ...] = ()
    output_unit: str = ""

    def __post_init__(self) -> None:
        for field_name in ("claim_id", "text"):
            value = getattr(self, field_name)
            if not isinstance(value, str) or not value.strip():
                raise TypeError(f"{field_name} must be non-empty")
            object.__setattr__(self, field_name, value.strip())
        object.__setattr__(self, "kind", ClaimKind(self.kind))
        object.__setattr__(self, "confidence", ClaimConfidence(self.confidence))
        object.__setattr__(self, "risk", ClaimRisk(self.risk))
        evidence = tuple(self.evidence)
        if any(not isinstance(item, SourceReference) for item in evidence):
            raise TypeError("evidence must contain SourceReference values")
        object.__setattr__(self, "evidence", evidence)
        for field_name in ("derived_from", "input_units"):
            values = tuple(getattr(self, field_name))
            if any(not isinstance(item, str) or not item for item in values):
                raise TypeError(f"{field_name} must contain non-empty strings")
            object.__setattr__(self, field_name, values)
        if not isinstance(self.transformation_id, str) or not isinstance(
            self.output_unit, str
        ):
            raise TypeError("transformation fields must be strings")


@dataclass(frozen=True, slots=True)
class ValidationFinding:
    """Safe finding without content, source summaries, or tenant identifiers."""

    code: str
    category: str
    claim_id: str = ""


@dataclass(frozen=True, slots=True)
class ValidationResult:
    """Deterministic, privacy-safe validation result."""

    outcome: ValidationOutcome
    policy_name: str
    policy_version: int
    snapshot_digest: str
    findings: tuple[ValidationFinding, ...]

    @property
    def approvable(self) -> bool:
        return self.outcome is ValidationOutcome.APPROVED


def _fold(value: str) -> str:
    return unicodedata.normalize("NFC", value).casefold()


def _source_key(source: SourceReference) -> tuple[str, str, int, str]:
    return (source.source_type, source.source_id, source.version, source.digest)


class ContentValidator:
    """Validate output against one immutable snapshot and one policy pack."""

    def validate(
        self,
        *,
        snapshot_bytes: bytes,
        snapshot_digest: str,
        tenant_id: str,
        brand_id: str,
        content: str,
        channel: str,
        content_type: str,
        anchors: Sequence[GroundingAnchor],
        claims: Sequence[GroundedClaim],
        policy: PolicyPack,
        provider_metadata: Any = None,
    ) -> ValidationResult:
        """Return a safe outcome; provider metadata is never an authority input."""

        del provider_metadata
        if not isinstance(policy, PolicyPack):
            raise TypeError("policy must be a PolicyPack")
        try:
            snapshot = load_grounding_snapshot(
                snapshot_bytes,
                expected_digest=snapshot_digest,
                tenant_id=tenant_id,
                brand_id=brand_id,
            )
        except GroundingError as error:
            code = (
                "grounding_unavailable"
                if error.code == "resource_unavailable"
                else "grounding_invalid"
            )
            return self._result(
                policy, snapshot_digest, ValidationOutcome.BLOCKED, code
            )
        if (
            policy.grounding_schema_version != snapshot.schema_version
            or policy.grounding_canonicalization_version != "MLAI-GS-1"
        ):
            return self._result(
                policy,
                snapshot.digest,
                ValidationOutcome.BLOCKED,
                "policy_incompatible",
            )
        if not isinstance(content, str) or not content.strip():
            return self._result(
                policy, snapshot.digest, ValidationOutcome.BLOCKED, "content_invalid"
            )
        if not isinstance(channel, str) or not isinstance(content_type, str):
            return self._result(
                policy, snapshot.digest, ValidationOutcome.BLOCKED, "channel_invalid"
            )
        anchor_result = self._validate_anchors(
            snapshot.source_refs, content, anchors, policy
        )
        if anchor_result:
            return self._result(
                policy, snapshot.digest, anchor_result[0], *anchor_result[1:]
            )
        channel_result = self._validate_channel(
            content, channel, content_type, anchors, policy
        )
        if channel_result:
            return self._result(
                policy, snapshot.digest, channel_result[0], *channel_result[1:]
            )
        claim_result = self._validate_claims(snapshot.source_refs, claims, policy)
        if claim_result:
            return self._result(
                policy, snapshot.digest, claim_result[0], *claim_result[1:]
            )
        return self._result(
            policy, snapshot.digest, ValidationOutcome.APPROVED, "validation_passed"
        )

    @staticmethod
    def _validate_anchors(
        snapshot_sources: Sequence[SourceReference],
        content: str,
        anchors: Sequence[GroundingAnchor],
        policy: PolicyPack,
    ) -> tuple[ValidationOutcome, str, str] | None:
        if isinstance(anchors, (str, bytes)):
            return (ValidationOutcome.BLOCKED, "anchors_invalid", "validation")
        allowed = {_source_key(item) for item in snapshot_sources}
        seen: set[tuple[str, str, int, str]] = set()
        distinct_text: set[str] = set()
        categories: set[str] = set()
        folded_content = _fold(content)
        for anchor in anchors:
            if not isinstance(anchor, GroundingAnchor):
                return (ValidationOutcome.BLOCKED, "anchors_invalid", "validation")
            key = _source_key(anchor.source)
            if key not in allowed or key in seen:
                return (ValidationOutcome.BLOCKED, "evidence_invalid", "evidence")
            if _fold(anchor.text) not in folded_content:
                return (
                    ValidationOutcome.REVIEW_REQUIRED,
                    "anchor_missing",
                    "specificity",
                )
            seen.add(key)
            distinct_text.add(_fold(anchor.text))
            categories.add(anchor.source.source_type)
        if (
            len(distinct_text) < policy.anchor_floor
            or len(categories) < policy.category_floor
        ):
            return (
                ValidationOutcome.REVIEW_REQUIRED,
                "specificity_insufficient",
                "specificity",
            )
        return None

    @staticmethod
    def _validate_channel(
        content: str,
        channel: str,
        content_type: str,
        anchors: Sequence[GroundingAnchor],
        policy: PolicyPack,
    ) -> tuple[ValidationOutcome, str, str] | None:
        rule = policy.channel_rule(channel, content_type)
        if rule is None:
            return None
        folded = _fold(content)
        for marker in rule.required_markers:
            if marker not in folded:
                return (
                    ValidationOutcome.REVIEW_REQUIRED,
                    "channel_structure_missing",
                    "channel",
                )
        categories = {item.source.source_type for item in anchors}
        if not set(rule.required_anchor_categories).issubset(categories):
            return (
                ValidationOutcome.REVIEW_REQUIRED,
                "channel_anchor_missing",
                "channel",
            )
        return None

    @staticmethod
    def _validate_claims(
        snapshot_sources: Sequence[SourceReference],
        claims: Sequence[GroundedClaim],
        policy: PolicyPack,
    ) -> tuple[ValidationOutcome, str, str] | None:
        if isinstance(claims, (str, bytes)) or not claims:
            return (ValidationOutcome.REVIEW_REQUIRED, "claims_missing", "factuality")
        allowed = {_source_key(item) for item in snapshot_sources}
        if any(not isinstance(item, GroundedClaim) for item in claims):
            return (ValidationOutcome.BLOCKED, "claim_invalid", "factuality")
        claim_ids = {item.claim_id for item in claims}
        claims_by_id = {item.claim_id: item for item in claims}
        seen_claims: dict[str, tuple[str, ClaimKind]] = {}
        for claim in claims:
            prior = seen_claims.get(claim.claim_id)
            identity = (claim.text, claim.kind)
            if prior is not None and prior != identity:
                return (ValidationOutcome.BLOCKED, "claims_conflicting", "factuality")
            seen_claims[claim.claim_id] = identity
            if claim.confidence is not ClaimConfidence.SUPPORTED:
                if claim.risk is ClaimRisk.HIGH:
                    return (
                        ValidationOutcome.BLOCKED,
                        "high_risk_unsupported",
                        "factuality",
                    )
                return (
                    ValidationOutcome.REVIEW_REQUIRED,
                    "claim_review_required",
                    "factuality",
                )
            keys = [_source_key(item) for item in claim.evidence]
            if not keys or any(key not in allowed for key in keys):
                return (ValidationOutcome.BLOCKED, "evidence_invalid", "evidence")
            by_identity: dict[tuple[str, str, int], str] = {}
            for item in claim.evidence:
                identity_key = (item.source_type, item.source_id, item.version)
                prior_digest = by_identity.get(identity_key)
                if prior_digest is not None and prior_digest != item.digest:
                    return (
                        ValidationOutcome.BLOCKED,
                        "evidence_conflicting",
                        "evidence",
                    )
                by_identity[identity_key] = item.digest
            if claim.risk is ClaimRisk.HIGH and claim.kind is not ClaimKind.DIRECT:
                return (
                    ValidationOutcome.BLOCKED,
                    "high_risk_requires_direct",
                    "factuality",
                )
            if claim.kind is ClaimKind.DERIVED:
                transform = policy.transformation(claim.transformation_id)
                if transform is None or not transform.deterministic:
                    return (
                        ValidationOutcome.BLOCKED,
                        "transformation_invalid",
                        "factuality",
                    )
                if not claim.derived_from or not claim.output_unit:
                    return (ValidationOutcome.BLOCKED, "lineage_incomplete", "evidence")
                if not set(claim.derived_from).issubset(claim_ids):
                    return (ValidationOutcome.BLOCKED, "lineage_incomplete", "evidence")
                if claim.claim_id in claim.derived_from:
                    return (ValidationOutcome.BLOCKED, "lineage_cycle", "evidence")
                lineage_keys = {
                    _source_key(item)
                    for source_claim_id in claim.derived_from
                    for item in claims_by_id[source_claim_id].evidence
                }
                if not lineage_keys.issubset(set(keys)):
                    return (ValidationOutcome.BLOCKED, "lineage_incomplete", "evidence")
                if tuple(claim.input_units) != transform.input_units:
                    return (ValidationOutcome.BLOCKED, "unit_mismatch", "factuality")
                if claim.output_unit != transform.output_unit:
                    return (ValidationOutcome.BLOCKED, "unit_mismatch", "factuality")
                if transform.allows_extrapolation:
                    return (
                        ValidationOutcome.BLOCKED,
                        "unsupported_extrapolation",
                        "factuality",
                    )
        return None

    @staticmethod
    def _result(
        policy: PolicyPack,
        snapshot_digest: str,
        outcome: ValidationOutcome,
        code: str,
        category: str = "validation",
    ) -> ValidationResult:
        return ValidationResult(
            outcome=outcome,
            policy_name=policy.name,
            policy_version=policy.version,
            snapshot_digest=snapshot_digest,
            findings=(ValidationFinding(code=code, category=category),),
        )
