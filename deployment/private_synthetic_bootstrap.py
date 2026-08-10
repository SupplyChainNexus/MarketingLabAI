"""Fail-closed planning and evidence checks for private Cloud Run bootstrap."""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum
from typing import Mapping

CANONICAL_SERVICE = "marketinglabai-velani-pilot"
APPROVED_INGRESS = "internal-and-cloud-load-balancing"
IMAGE_PATTERN = re.compile(
    r"africa-south1-docker\.pkg\.dev/marketinglabai-identity-dev/"
    r"mlai-synthetic/marketinglabai-pilot@sha256:[0-9a-f]{64}"
)
SHA256_PATTERN = re.compile(r"[0-9a-f]{64}")


class ServiceState(str, Enum):
    ABSENT = "ABSENT"
    EXISTING_PRIVATE = "EXISTING_PRIVATE"
    EXISTING_PUBLIC = "EXISTING_PUBLIC"
    AMBIGUOUS = "AMBIGUOUS"


class RevisionCreationMode(str, Enum):
    FIRST_PRIVATE_REVISION = "FIRST_PRIVATE_REVISION"
    ZERO_TRAFFIC_REVISION = "ZERO_TRAFFIC_REVISION"
    REFUSED = "REFUSED"


@dataclass(frozen=True, slots=True)
class BootstrapObservation:
    canonical_service_name: str
    service_state: ServiceState
    cloud_run_baseline_sha256: str
    immutable_image_digest: str
    ingress: str | None
    public_principal_count: int
    pilot_invoker_grant_count: int


@dataclass(frozen=True, slots=True)
class BootstrapPlan:
    canonical_service_name: str
    service_existed_before: bool
    creation_mode: RevisionCreationMode
    expected_new_revision_traffic_percent: int
    required_ingress: str
    maximum_mutation_count: int
    deployable: bool
    refusal_reason: str


def plan_revision_creation(observation: BootstrapObservation) -> BootstrapPlan:
    """Return a deterministic plan without performing a cloud mutation."""

    if observation.canonical_service_name != CANONICAL_SERVICE:
        return _refused(observation, "Canonical service name is invalid.")
    if not SHA256_PATTERN.fullmatch(observation.cloud_run_baseline_sha256):
        return _refused(observation, "Cloud Run baseline hash is invalid.")
    if not IMAGE_PATTERN.fullmatch(observation.immutable_image_digest):
        return _refused(observation, "Image is not the approved immutable digest.")
    if (
        observation.public_principal_count < 0
        or observation.pilot_invoker_grant_count < 0
    ):
        return _refused(observation, "Principal counts may not be negative.")
    if observation.public_principal_count:
        return _refused(observation, "Public invocation authority is prohibited.")
    if observation.service_state in {
        ServiceState.EXISTING_PUBLIC,
        ServiceState.AMBIGUOUS,
    }:
        return _refused(observation, "Observed service state is not safely deployable.")

    if observation.service_state is ServiceState.ABSENT:
        if observation.ingress is not None:
            return _refused(
                observation, "Absent service unexpectedly has ingress state."
            )
        if observation.pilot_invoker_grant_count:
            return _refused(
                observation, "First-service bootstrap may not grant pilot invocation."
            )
        return BootstrapPlan(
            canonical_service_name=CANONICAL_SERVICE,
            service_existed_before=False,
            creation_mode=RevisionCreationMode.FIRST_PRIVATE_REVISION,
            expected_new_revision_traffic_percent=100,
            required_ingress=APPROVED_INGRESS,
            maximum_mutation_count=1,
            deployable=True,
            refusal_reason="",
        )

    if observation.ingress != APPROVED_INGRESS:
        return _refused(observation, "Existing service ingress is not private.")
    return BootstrapPlan(
        canonical_service_name=CANONICAL_SERVICE,
        service_existed_before=True,
        creation_mode=RevisionCreationMode.ZERO_TRAFFIC_REVISION,
        expected_new_revision_traffic_percent=0,
        required_ingress=APPROVED_INGRESS,
        maximum_mutation_count=1,
        deployable=True,
        refusal_reason="",
    )


def validate_revision_evidence(values: Mapping[str, str]) -> None:
    """Reject incomplete or contradictory REVISION_CREATED evidence."""

    required = {
        "authorization_id",
        "pre_mutation_baseline_sha256",
        "post_mutation_state_sha256",
        "created_revision",
        "service_existed_before",
        "creation_mode",
        "image_digest",
        "mutation_count",
        "ingress",
        "public_principals",
        "pilot_invoker_grants",
        "created_revision_traffic_percent",
        "cloud_run_operation_id",
        "configuration_evidence_sha256",
    }
    missing = sorted(required - set(values))
    if missing:
        raise ValueError(f"REVISION_CREATED evidence is incomplete: {missing}")
    if not values["authorization_id"].strip():
        raise ValueError("Revision authorization is required.")
    for field in (
        "pre_mutation_baseline_sha256",
        "post_mutation_state_sha256",
        "configuration_evidence_sha256",
    ):
        if not SHA256_PATTERN.fullmatch(values[field]):
            raise ValueError(f"Invalid evidence hash: {field}")
    if not IMAGE_PATTERN.fullmatch(values["image_digest"]):
        raise ValueError("Revision evidence image is not digest-pinned.")
    if values["mutation_count"] != "1":
        raise ValueError("Exactly one revision mutation must be observed.")
    if values["ingress"] != APPROVED_INGRESS:
        raise ValueError("Revision ingress is not private.")
    if values["public_principals"] != "0":
        raise ValueError("Public principals are prohibited.")

    mode = RevisionCreationMode(values["creation_mode"])
    existed = values["service_existed_before"]
    traffic = values["created_revision_traffic_percent"]
    pilot_grants = values["pilot_invoker_grants"]
    if mode is RevisionCreationMode.FIRST_PRIVATE_REVISION:
        if existed != "false" or traffic != "100" or pilot_grants != "0":
            raise ValueError("First-service bootstrap evidence is contradictory.")
    elif mode is RevisionCreationMode.ZERO_TRAFFIC_REVISION:
        if existed != "true" or traffic != "0":
            raise ValueError("Existing-service revision must have zero traffic.")
    else:
        raise ValueError("A refused plan cannot record REVISION_CREATED.")


def _refused(observation: BootstrapObservation, reason: str) -> BootstrapPlan:
    return BootstrapPlan(
        canonical_service_name=observation.canonical_service_name,
        service_existed_before=observation.service_state is not ServiceState.ABSENT,
        creation_mode=RevisionCreationMode.REFUSED,
        expected_new_revision_traffic_percent=0,
        required_ingress=APPROVED_INGRESS,
        maximum_mutation_count=0,
        deployable=False,
        refusal_reason=reason,
    )
