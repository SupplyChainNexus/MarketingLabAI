"""Independent shadow verifier for zero-trust release evidence.

This module never signs, deploys, mutates cloud resources, or converts legacy
controller state into release authority. Cryptographic operations remain the
responsibility of isolated Cosign, KMS, RFC 3161, and Binary Authorization
components. The repository verifier validates their bound claims and policy
relationships before infrastructure enforcement is enabled.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping, Sequence

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_POLICY = ROOT / "deployment" / "zero_trust_supply_chain_policy.json"
IN_TOTO_STATEMENT = "https://in-toto.io/Statement/v1"
GATE_PREDICATE = "https://supplychainnexus.co.za/attestation/release-gate/v1"
RELEASE_PREDICATE = (
    "https://supplychainnexus.co.za/attestation/release-authorization/v1"
)


def canonical_json(value: Mapping[str, object]) -> bytes:
    return json.dumps(
        value, ensure_ascii=True, separators=(",", ":"), sort_keys=True
    ).encode("utf-8")


def sha256_json(value: Mapping[str, object]) -> str:
    return hashlib.sha256(canonical_json(value)).hexdigest()


@dataclass(frozen=True, slots=True)
class ReleaseIdentity:
    run_id: str
    git_commit: str
    image_digest: str
    environment: str

    def validate(self, repository: str) -> None:
        if not re.fullmatch(r"run-[A-Za-z0-9._-]{8,120}", self.run_id):
            raise ValueError("Run ID is invalid.")
        if not re.fullmatch(r"[0-9a-f]{40}", self.git_commit):
            raise ValueError("Git commit must be a full lowercase SHA-1 object ID.")
        expected = rf"{re.escape(repository)}@sha256:[0-9a-f]{{64}}"
        if not re.fullmatch(expected, self.image_digest):
            raise ValueError("Image must use the approved repository and digest.")
        if self.environment != "cloud-synthetic":
            raise ValueError("Only the cloud-synthetic environment is permitted.")


def load_policy(path: Path = DEFAULT_POLICY) -> dict[str, object]:
    policy = json.loads(path.read_text(encoding="utf-8"))
    if policy.get("schema_version") != 1 or policy.get("mode") != "shadow":
        raise ValueError("Unsupported or prematurely enforcing supply-chain policy.")
    required = policy.get("required_gates")
    if not isinstance(required, list) or not required:
        raise ValueError("Supply-chain policy has no required gates.")
    if len(required) != len(set(required)):
        raise ValueError("Supply-chain policy repeats a gate.")
    legacy = policy.get("legacy", {})
    if any(
        legacy.get(field) is not False
        for field in (
            "controller_state_authoritative",
            "backfill_may_authorize_deployment",
            "historical_runs_deployable",
        )
    ):
        raise ValueError("Legacy controller authority must remain disabled.")
    return policy


def _subject_digest(statement: Mapping[str, object]) -> str:
    subjects = statement.get("subject")
    if not isinstance(subjects, list) or len(subjects) != 1:
        raise ValueError("Attestation must contain exactly one image subject.")
    subject = subjects[0]
    digest = subject.get("digest") if isinstance(subject, dict) else None
    value = digest.get("sha256") if isinstance(digest, dict) else None
    if not isinstance(value, str) or not re.fullmatch(r"[0-9a-f]{64}", value):
        raise ValueError("Attestation subject SHA-256 is invalid.")
    return f"sha256:{value}"


def validate_gate_attestation(
    statement: Mapping[str, object],
    verification: Mapping[str, object],
    identity: ReleaseIdentity,
    policy: Mapping[str, object],
) -> str:
    if statement.get("_type") != IN_TOTO_STATEMENT:
        raise ValueError("Unsupported in-toto statement type.")
    if statement.get("predicateType") != GATE_PREDICATE:
        raise ValueError("Unsupported gate predicate type.")
    predicate = statement.get("predicate")
    if not isinstance(predicate, dict):
        raise ValueError("Gate predicate is missing.")
    expected = {
        "runId": identity.run_id,
        "gitCommit": identity.git_commit,
        "imageDigest": identity.image_digest,
        "environment": identity.environment,
    }
    for name, value in expected.items():
        if predicate.get(name) != value:
            raise ValueError(f"Gate attestation has a mismatched {name}.")
    if _subject_digest(statement) != identity.image_digest.rsplit("@", 1)[1]:
        raise ValueError("Gate subject is not the release image digest.")
    gate_id = predicate.get("gateId")
    if gate_id not in policy["required_gates"]:
        raise ValueError("Gate is not required by the trusted policy.")
    if predicate.get("outcome") != "passed":
        raise ValueError("Only passed gate attestations are eligible.")
    policy_digest = predicate.get("policyBundleDigest")
    if not isinstance(policy_digest, str) or not re.fullmatch(
        r"sha256:[0-9a-f]{64}", policy_digest
    ):
        raise ValueError("Gate policy-bundle digest is invalid.")
    for claim, required_value in policy["required_claims"].items():
        if verification.get(claim) is not required_value:
            raise ValueError(f"Cryptographic verification claim failed: {claim}")
    envelope_digest = verification.get("signed_envelope_sha256")
    timestamp_imprint = verification.get("rfc3161_message_imprint_sha256")
    if not isinstance(envelope_digest, str) or not re.fullmatch(
        r"[0-9a-f]{64}", envelope_digest
    ):
        raise ValueError("Signed-envelope digest is invalid.")
    if timestamp_imprint != envelope_digest:
        raise ValueError("RFC 3161 token does not cover the signed envelope.")
    return str(gate_id)


def evaluate_shadow_release(
    *,
    identity: ReleaseIdentity,
    attestations: Sequence[Mapping[str, object]],
    verifications: Sequence[Mapping[str, object]],
    policy_path: Path = DEFAULT_POLICY,
) -> dict[str, object]:
    """Evaluate evidence without issuing deployment authority."""

    policy = load_policy(policy_path)
    identity.validate(str(policy["artifact_repository"]))
    if len(attestations) != len(verifications):
        raise ValueError("Every attestation requires one verification record.")
    observed: set[str] = set()
    for statement, verification in zip(attestations, verifications, strict=True):
        gate_id = validate_gate_attestation(statement, verification, identity, policy)
        if gate_id in observed:
            raise ValueError(f"Duplicate gate attestation: {gate_id}")
        observed.add(gate_id)
    required = set(policy["required_gates"])
    missing = sorted(required - observed)
    return {
        "schema_version": 1,
        "mode": "shadow",
        "run_id": identity.run_id,
        "git_commit": identity.git_commit,
        "image_digest": identity.image_digest,
        "policy_sha256": sha256_json(policy),
        "verified_gates": sorted(observed),
        "missing_gates": missing,
        "evidence_complete": not missing,
        "release_authorization_issued": False,
        "deployment_authorized": False,
        "cloud_mutation_performed": False,
    }
