"""C5 Campaign Asset integration for governed generation and review."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Protocol, Sequence

from app.campaign_planner.asset_repository import (
    AssetRevisionRecord,
    CampaignAssetRepository,
    GenerationAttemptRecord,
)
from app.marketing_workflow.orchestration import WorkflowApiOperationClaimRepository
from app.marketing_workflow.repository import MarketingWorkflowRepository

from .grounding import (
    GROUNDING_CANONICALIZATION_VERSION,
    GroundingError,
    load_grounding_snapshot,
)
from .models import GroundingSnapshot, SourceLifecycle, SourceReference
from .policy import PolicyPack
from .validation import (
    ContentValidator,
    GroundedClaim,
    GroundingAnchor,
    ValidationFinding,
    ValidationOutcome,
    ValidationResult,
)


class GenerationBoundaryError(RuntimeError):
    """Privacy-safe fail-closed integration refusal."""


@dataclass(frozen=True, slots=True)
class GeneratedOutput:
    content: str
    provider_name: str | None = None
    model_name: str | None = None
    model_version: str | None = None


class ContentGenerator(Protocol):
    def __call__(self, snapshot: GroundingSnapshot) -> GeneratedOutput: ...


class ImmutableOutputStore(Protocol):
    def save(
        self,
        content: str,
        *,
        tenant_id: str,
        brand_id: str,
        asset_id: str,
        revision: int,
        request_id: str,
    ) -> str: ...

    def load(self, reference: str) -> str | None: ...


@dataclass(frozen=True, slots=True)
class GenerationRequest:
    tenant_id: str
    brand_id: str
    campaign_id: str
    asset_id: str
    revision: int
    request_id: str
    generation_identity: str
    operation_claim_id: str
    workflow_id: str
    workflow_version: int
    snapshot_bytes: bytes
    snapshot_digest: str
    channel: str
    content_type: str
    anchors: Sequence[GroundingAnchor]
    claims: Sequence[GroundedClaim]
    policy: PolicyPack
    created_at: str
    attempt_id: str
    parent_revision: int | None = None


@dataclass(frozen=True, slots=True)
class GovernedGenerationResult:
    revision: AssetRevisionRecord
    validation: ValidationResult
    content: str
    replay: bool


class GovernedGenerationService:
    """Keep lifecycle, evidence, approval, and replay ownership separated."""

    APPROVAL_ACTION = "approve_campaign_asset"

    def __init__(
        self,
        *,
        assets: CampaignAssetRepository,
        operation_claims: WorkflowApiOperationClaimRepository,
        workflows: MarketingWorkflowRepository,
        output_store: ImmutableOutputStore,
        generator: ContentGenerator,
        validator: ContentValidator | None = None,
    ) -> None:
        self.assets = assets
        self.operation_claims = operation_claims
        self.workflows = workflows
        self.output_store = output_store
        self.generator = generator
        self.validator = validator or ContentValidator()

    def generate(self, request: GenerationRequest) -> GovernedGenerationResult:
        """Generate once, validate, and persist only bounded metadata."""

        replay = self.assets.get_revision_by_request(
            tenant_id=request.tenant_id,
            brand_id=request.brand_id,
            request_id=request.request_id,
        )
        if replay is not None:
            self._assert_operation_claim(request)
            self._assert_exact_request(replay, request)
            return self._replay(replay, request.policy)

        self._assert_operation_claim(request)

        try:
            snapshot = load_grounding_snapshot(
                request.snapshot_bytes,
                expected_digest=request.snapshot_digest,
                tenant_id=request.tenant_id,
                brand_id=request.brand_id,
            )
        except GroundingError:
            self._refuse()
        if snapshot.generation_identity != request.generation_identity:
            self._refuse()

        state = self.assets.asset_state(
            tenant_id=request.tenant_id,
            brand_id=request.brand_id,
            asset_id=request.asset_id,
        )
        if state is None:
            if request.revision != 1 or request.parent_revision is not None:
                self._refuse()
            self.assets.create_asset(
                tenant_id=request.tenant_id,
                brand_id=request.brand_id,
                asset_id=request.asset_id,
                campaign_id=request.campaign_id,
                created_at=request.created_at,
            )
            state = ("requested", 1, 1)
        elif (
            request.parent_revision != state[1]
            or request.revision != state[1] + 1
            or state[0] == "superseded"
        ):
            self._refuse()

        generated = self.generator(snapshot)
        if not isinstance(generated, GeneratedOutput) or not generated.content:
            self._refuse()
        validation = self.validator.validate(
            snapshot_bytes=request.snapshot_bytes,
            snapshot_digest=request.snapshot_digest,
            tenant_id=request.tenant_id,
            brand_id=request.brand_id,
            content=generated.content,
            channel=request.channel,
            content_type=request.content_type,
            anchors=request.anchors,
            claims=request.claims,
            policy=request.policy,
            provider_metadata=generated,
        )
        output_digest = self._output_digest(generated.content)
        output_reference = self.output_store.save(
            generated.content,
            tenant_id=request.tenant_id,
            brand_id=request.brand_id,
            asset_id=request.asset_id,
            revision=request.revision,
            request_id=request.request_id,
        )
        revision = AssetRevisionRecord(
            tenant_id=request.tenant_id,
            brand_id=request.brand_id,
            asset_id=request.asset_id,
            revision=request.revision,
            generation_identity=request.generation_identity,
            request_id=request.request_id,
            snapshot_digest=request.snapshot_digest,
            snapshot_schema_version=snapshot.schema_version,
            snapshot_canonicalization_version=GROUNDING_CANONICALIZATION_VERSION,
            source_references=tuple(
                self._source_metadata(item) for item in snapshot.source_refs
            ),
            output_digest=output_digest,
            output_reference=output_reference,
            validation_outcome=validation.outcome.value,
            policy_pack_name=request.policy.name,
            policy_pack_version=request.policy.version,
            policy_pack_digest=request.policy.digest,
            safe_findings=tuple(
                {
                    "code": item.code,
                    "category": item.category,
                    **({"claim_id": item.claim_id} if item.claim_id else {}),
                }
                for item in validation.findings
            ),
            provider_name=generated.provider_name,
            model_name=generated.model_name,
            model_version=generated.model_version,
            workflow_id=request.workflow_id,
            workflow_version=request.workflow_version,
            parent_revision=request.parent_revision,
            created_at=request.created_at,
        )
        lifecycle_state = (
            "reviewable"
            if validation.outcome is not ValidationOutcome.BLOCKED
            else "validation_failed"
        )
        attempt = GenerationAttemptRecord(
            attempt_id=request.attempt_id,
            tenant_id=request.tenant_id,
            brand_id=request.brand_id,
            asset_id=request.asset_id,
            revision=request.revision,
            operation_claim_id=request.operation_claim_id,
            generation_identity=request.generation_identity,
            request_id=request.request_id,
            attempt_state=lifecycle_state,
            snapshot_digest=request.snapshot_digest,
            output_digest=output_digest,
            validation_outcome=validation.outcome.value,
            policy_pack_name=request.policy.name,
            policy_pack_version=request.policy.version,
            policy_pack_digest=request.policy.digest,
            provider_name=generated.provider_name,
            model_name=generated.model_name,
            model_version=generated.model_version,
            created_at=request.created_at,
            updated_at=request.created_at,
        )
        with self.assets.database.transaction() as connection:
            self.assets.save_revision(revision, connection=connection)
            self.assets.save_attempt(attempt, connection=connection)
            self.assets.advance_asset(
                tenant_id=request.tenant_id,
                brand_id=request.brand_id,
                asset_id=request.asset_id,
                expected_version=state[2],
                expected_revision=request.revision,
                lifecycle_state=lifecycle_state,
                updated_at=request.created_at,
                connection=connection,
            )
        return GovernedGenerationResult(revision, validation, generated.content, False)

    def approve(
        self,
        *,
        tenant_id: str,
        brand_id: str,
        asset_id: str,
        revision: int,
        policy: PolicyPack,
        current_sources: Sequence[SourceReference],
        updated_at: str,
    ) -> AssetRevisionRecord:
        """Validate immutable result and evidence again before lifecycle approval."""

        record = self.assets.get_revision(
            tenant_id=tenant_id,
            brand_id=brand_id,
            asset_id=asset_id,
            revision=revision,
        )
        state = self.assets.asset_state(
            tenant_id=tenant_id, brand_id=brand_id, asset_id=asset_id
        )
        if record is None or state is None or state[1] != revision:
            self._refuse()
        if record.validation_outcome != ValidationOutcome.APPROVED.value:
            self._refuse()
        if (
            record.policy_pack_name != policy.name
            or record.policy_pack_version != policy.version
            or record.policy_pack_digest != policy.digest
        ):
            self._refuse()
        self._assert_current_sources(record, current_sources, tenant_id, brand_id)
        self._load_verified_output(record)
        if record.workflow_id is None or record.workflow_version is None:
            self._refuse()
        try:
            approval = self.workflows.approved_for(
                tenant_id=tenant_id,
                brand_id=brand_id,
                workflow_id=record.workflow_id,
                workflow_version=record.workflow_version,
                action=self.APPROVAL_ACTION,
            )
        except (KeyError, ValueError):
            self._refuse()
        if approval is None:
            self._refuse()
        self.assets.advance_asset(
            tenant_id=tenant_id,
            brand_id=brand_id,
            asset_id=asset_id,
            expected_version=state[2],
            expected_revision=revision,
            lifecycle_state="approved",
            updated_at=updated_at,
        )
        return record

    def _replay(
        self, record: AssetRevisionRecord, policy: PolicyPack
    ) -> GovernedGenerationResult:
        if (
            record.policy_pack_name != policy.name
            or record.policy_pack_version != policy.version
            or record.policy_pack_digest != policy.digest
        ):
            self._refuse()
        content = self._load_verified_output(record)
        validation = ValidationResult(
            outcome=ValidationOutcome(record.validation_outcome),
            policy_name=record.policy_pack_name,
            policy_version=record.policy_pack_version,
            snapshot_digest=record.snapshot_digest,
            findings=tuple(
                ValidationFinding(
                    code=str(item["code"]),
                    category=str(item.get("category", "validation")),
                    claim_id=str(item.get("claim_id", "")),
                )
                for item in record.safe_findings
            ),
        )
        return GovernedGenerationResult(record, validation, content, True)

    @staticmethod
    def _assert_exact_request(
        record: AssetRevisionRecord, request: GenerationRequest
    ) -> None:
        if (
            record.asset_id != request.asset_id
            or record.revision != request.revision
            or record.generation_identity != request.generation_identity
            or record.snapshot_digest != request.snapshot_digest
            or record.parent_revision != request.parent_revision
            or record.workflow_id != request.workflow_id
            or record.workflow_version != request.workflow_version
        ):
            GovernedGenerationService._refuse()

    def _assert_operation_claim(self, request: GenerationRequest) -> None:
        try:
            claim = self.operation_claims.get(request.operation_claim_id)
        except (KeyError, ValueError):
            self._refuse()
        if (
            claim is None
            or claim.tenant_id != request.tenant_id
            or claim.brand_id != request.brand_id
            or claim.workflow_id != request.workflow_id
        ):
            self._refuse()

    @staticmethod
    def _source_metadata(source: SourceReference) -> dict[str, object]:
        return {
            "source_id": source.source_id,
            "source_type": source.source_type,
            "version": source.version,
            "digest": source.digest,
            "lifecycle_state": source.lifecycle.value,
            "privacy_classification": source.privacy_classification.value,
        }

    @classmethod
    def _assert_current_sources(
        cls,
        record: AssetRevisionRecord,
        sources: Sequence[SourceReference],
        tenant_id: str,
        brand_id: str,
    ) -> None:
        if any(
            item.tenant_id != tenant_id
            or item.brand_id != brand_id
            or item.lifecycle is not SourceLifecycle.APPROVED
            for item in sources
        ):
            cls._refuse()
        expected = sorted(
            record.source_references,
            key=lambda item: (item["source_type"], item["source_id"]),
        )
        current = sorted(
            (cls._source_metadata(item) for item in sources),
            key=lambda item: (item["source_type"], item["source_id"]),
        )
        if expected != current:
            cls._refuse()

    def _load_verified_output(self, record: AssetRevisionRecord) -> str:
        content = self.output_store.load(record.output_reference)
        if content is None or self._output_digest(content) != record.output_digest:
            self._refuse()
        return content

    @staticmethod
    def _output_digest(content: str) -> str:
        return hashlib.sha256(content.encode("utf-8")).hexdigest()

    @staticmethod
    def _refuse() -> None:
        raise GenerationBoundaryError("generation state is unavailable")
