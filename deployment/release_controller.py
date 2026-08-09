"""Legacy observational coordinator for private synthetic release sequencing.

ADR-0035 supersedes this controller as release authority. Its state cannot
authorize deployment and must not be repaired or backfilled into compliance.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import secrets
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Mapping, Sequence

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CATALOG = ROOT / "deployment" / "private_synthetic_release_gates.json"
EVENTS_FILE = "events.jsonl"
METADATA_FILE = "release.json"
ZERO_HASH = "0" * 64


@dataclass(frozen=True, slots=True)
class GateDefinition:
    id: str
    kind: str
    depends_on: tuple[str, ...]
    may_mutate_cloud: bool
    purpose: str


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _canonical(value: Mapping[str, object]) -> bytes:
    return json.dumps(
        value, ensure_ascii=True, separators=(",", ":"), sort_keys=True
    ).encode("utf-8")


def _outside_repository(path: Path) -> bool:
    try:
        path.resolve().relative_to(ROOT.resolve())
    except ValueError:
        return True
    return False


def load_catalog(path: Path = DEFAULT_CATALOG) -> tuple[GateDefinition, ...]:
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    if payload.get("schema_version") != 1:
        raise ValueError("Unsupported release-gate catalogue schema.")
    raw_gates = payload.get("gates")
    if not isinstance(raw_gates, list) or not raw_gates:
        raise ValueError("Release-gate catalogue must contain gates.")

    gates: list[GateDefinition] = []
    known: set[str] = set()
    for raw in raw_gates:
        gate_id = str(raw.get("id", ""))
        if not re.fullmatch(r"[A-Z][A-Z0-9_]+", gate_id):
            raise ValueError(f"Invalid release-gate identifier: {gate_id}")
        if gate_id in known:
            raise ValueError(f"Duplicate release-gate identifier: {gate_id}")
        dependencies = tuple(str(item) for item in raw.get("depends_on", ()))
        missing = tuple(item for item in dependencies if item not in known)
        if missing:
            raise ValueError(
                f"Gate {gate_id} has unknown or forward dependencies: {missing}"
            )
        gate = GateDefinition(
            id=gate_id,
            kind=str(raw.get("kind", "")),
            depends_on=dependencies,
            may_mutate_cloud=bool(raw.get("may_mutate_cloud", False)),
            purpose=str(raw.get("purpose", "")),
        )
        if not gate.kind or not gate.purpose:
            raise ValueError(f"Gate {gate_id} is incomplete.")
        gates.append(gate)
        known.add(gate_id)
    return tuple(gates)


def validate_release_identity(
    *, commit: str, image_digest: str, environment: str
) -> None:
    if not re.fullmatch(r"[0-9a-f]{40}", commit):
        raise ValueError("Release commit must be a full lowercase 40-character SHA.")
    image_pattern = (
        r"africa-south1-docker\.pkg\.dev/marketinglabai-identity-dev/"
        r"mlai-synthetic/marketinglabai-pilot@sha256:[0-9a-f]{64}"
    )
    if not re.fullmatch(image_pattern, image_digest):
        raise ValueError("Release image must be the approved digest-pinned package.")
    if environment != "cloud-synthetic":
        raise ValueError("The controller currently permits cloud-synthetic only.")


def start_release(
    runs_root: Path,
    *,
    commit: str,
    image_digest: str,
    environment: str = "cloud-synthetic",
    operator: str,
    catalog_path: Path = DEFAULT_CATALOG,
) -> Path:
    """Create a unique immutable release identity outside the repository."""

    load_catalog(catalog_path)
    validate_release_identity(
        commit=commit, image_digest=image_digest, environment=environment
    )
    if not _outside_repository(runs_root):
        raise ValueError("Release evidence must remain outside the repository.")
    if not operator.strip():
        raise ValueError("Release operator is required.")

    runs_root.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    run_id = f"run-{stamp}-{secrets.token_hex(4)}"
    run_dir = runs_root / run_id
    run_dir.mkdir()
    metadata = {
        "schema_version": 1,
        "run_id": run_id,
        "created_at": _utc_now(),
        "commit": commit,
        "image_digest": image_digest,
        "environment": environment,
        "operator": operator.strip(),
        "controller_authoritative": False,
        "deployment_authority_source": "external-zero-trust-admission",
        "catalog_sha256": hashlib.sha256(catalog_path.read_bytes()).hexdigest(),
        "application_deployment_authorized": False,
        "public_access_authorized": False,
        "real_customer_data_authorized": False,
        "external_invitations_authorized": False,
        "billing_authorized": False,
        "publishing_authorized": False,
        "real_data_learning_authorized": False,
    }
    (run_dir / METADATA_FILE).write_text(
        json.dumps(metadata, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    (run_dir / EVENTS_FILE).touch(exist_ok=False)
    return run_dir


def read_events(run_dir: Path) -> tuple[dict[str, object], ...]:
    path = run_dir / EVENTS_FILE
    if not path.is_file():
        raise ValueError("Release event ledger is missing.")
    events = []
    for line_number, line in enumerate(
        path.read_text(encoding="utf-8").splitlines(), 1
    ):
        if not line.strip():
            continue
        try:
            event = json.loads(line)
        except json.JSONDecodeError as error:
            raise ValueError(f"Invalid event ledger line {line_number}.") from error
        events.append(event)
    return tuple(events)


def verify_run(
    run_dir: Path, catalog_path: Path = DEFAULT_CATALOG
) -> dict[str, object]:
    metadata_path = run_dir / METADATA_FILE
    if not metadata_path.is_file():
        raise ValueError("Release metadata is missing.")
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    expected_catalog_hash = hashlib.sha256(catalog_path.read_bytes()).hexdigest()
    if metadata.get("catalog_sha256") != expected_catalog_hash:
        raise ValueError("Release run is bound to a different gate catalogue.")

    previous_hash = ZERO_HASH
    for sequence, event in enumerate(read_events(run_dir), 1):
        recorded_hash = str(event.get("event_hash", ""))
        unsigned = {key: value for key, value in event.items() if key != "event_hash"}
        if event.get("sequence") != sequence:
            raise ValueError("Release event sequence is invalid.")
        if event.get("previous_event_hash") != previous_hash:
            raise ValueError("Release event hash chain is invalid.")
        calculated = hashlib.sha256(_canonical(unsigned)).hexdigest()
        if recorded_hash != calculated:
            raise ValueError("Release event content has been modified.")
        previous_hash = recorded_hash
    return metadata


def gate_status(run_dir: Path, catalog_path: Path = DEFAULT_CATALOG) -> dict[str, str]:
    verify_run(run_dir, catalog_path)
    status = {gate.id: "pending" for gate in load_catalog(catalog_path)}
    for event in read_events(run_dir):
        status[str(event["gate_id"])] = str(event["outcome"])
    return status


def record_gate(
    run_dir: Path,
    *,
    gate_id: str,
    outcome: str,
    evidence_reference: str,
    operator: str,
    mutation_performed: bool = False,
    authorization_reference: str = "",
    failure_classification: str = "",
    remediation: str = "",
    safe_next_action: str = "",
    catalog_path: Path = DEFAULT_CATALOG,
) -> dict[str, object]:
    """Append one terminal gate result after enforcing its dependencies."""

    verify_run(run_dir, catalog_path)
    catalog = {gate.id: gate for gate in load_catalog(catalog_path)}
    if gate_id not in catalog:
        raise ValueError(f"Unknown release gate: {gate_id}")
    if outcome not in {"passed", "failed"}:
        raise ValueError("Gate outcome must be passed or failed.")
    if not evidence_reference.strip() or not operator.strip():
        raise ValueError("Evidence reference and operator are required.")

    status = gate_status(run_dir, catalog_path)
    if status[gate_id] != "pending":
        raise ValueError(f"Gate {gate_id} already has a terminal result.")
    gate = catalog[gate_id]
    blocked = tuple(dep for dep in gate.depends_on if status[dep] != "passed")
    if blocked:
        raise ValueError(f"Gate {gate_id} is blocked by prerequisites: {blocked}")
    if mutation_performed and not gate.may_mutate_cloud:
        raise ValueError(f"Gate {gate_id} may not record a cloud mutation.")
    if mutation_performed and not authorization_reference.strip():
        raise ValueError("Cloud mutation requires an authorization reference.")
    if outcome == "failed" and not all(
        item.strip() for item in (failure_classification, remediation, safe_next_action)
    ):
        raise ValueError(
            "Failed gates require classification, remediation and safe next action."
        )

    events = read_events(run_dir)
    previous_hash = str(events[-1]["event_hash"]) if events else ZERO_HASH
    event: dict[str, object] = {
        "sequence": len(events) + 1,
        "timestamp": _utc_now(),
        "gate_id": gate_id,
        "outcome": outcome,
        "operator": operator.strip(),
        "evidence_reference": evidence_reference.strip(),
        "mutation_performed": mutation_performed,
        "authorization_reference": authorization_reference.strip(),
        "failure_classification": failure_classification.strip(),
        "remediation": remediation.strip(),
        "safe_next_action": safe_next_action.strip(),
        "previous_event_hash": previous_hash,
        "public_access_authorized": False,
        "real_customer_data_authorized": False,
    }
    event["event_hash"] = hashlib.sha256(_canonical(event)).hexdigest()
    ledger = run_dir / EVENTS_FILE
    with ledger.open("a", encoding="utf-8", newline="\n") as stream:
        stream.write(json.dumps(event, sort_keys=True) + "\n")
        stream.flush()
        os.fsync(stream.fileno())
    return event


def release_summary(
    run_dir: Path, catalog_path: Path = DEFAULT_CATALOG
) -> dict[str, object]:
    metadata = verify_run(run_dir, catalog_path)
    gates = load_catalog(catalog_path)
    status = gate_status(run_dir, catalog_path)
    eligible = [
        gate.id
        for gate in gates
        if status[gate.id] == "pending"
        and all(status[dependency] == "passed" for dependency in gate.depends_on)
    ]
    failed = [gate.id for gate in gates if status[gate.id] == "failed"]
    return {
        "run_id": metadata["run_id"],
        "commit": metadata["commit"],
        "image_digest": metadata["image_digest"],
        "environment": metadata["environment"],
        "gate_status": status,
        "eligible_gates": eligible if not failed else [],
        "failed_gates": failed,
        "release_closed": status.get("RELEASE_CLOSED") == "passed",
        "public_access_authorized": False,
        "real_customer_data_authorized": False,
    }


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("validate-catalog")

    start = subparsers.add_parser("start")
    start.add_argument("--runs-root", type=Path, required=True)
    start.add_argument("--commit", required=True)
    start.add_argument("--image", required=True)
    start.add_argument("--environment", default="cloud-synthetic")
    start.add_argument("--operator", required=True)

    status = subparsers.add_parser("status")
    status.add_argument("--run", type=Path, required=True)

    verify = subparsers.add_parser("verify")
    verify.add_argument("--run", type=Path, required=True)

    record = subparsers.add_parser("record")
    record.add_argument("--run", type=Path, required=True)
    record.add_argument("--gate", required=True)
    record.add_argument("--outcome", choices=("passed", "failed"), required=True)
    record.add_argument("--evidence", required=True)
    record.add_argument("--operator", required=True)
    record.add_argument("--mutation-performed", action="store_true")
    record.add_argument("--authorization-reference", default="")
    record.add_argument("--failure-classification", default="")
    record.add_argument("--remediation", default="")
    record.add_argument("--safe-next-action", default="")
    return parser


def main(arguments: Sequence[str] | None = None) -> int:
    selected = _parser().parse_args(arguments)
    if selected.command == "validate-catalog":
        gates = load_catalog()
        print(
            json.dumps(
                {
                    "catalog_valid": True,
                    "gate_count": len(gates),
                    "ordered_gate_ids": [gate.id for gate in gates],
                    "cloud_mutation_executed": False,
                },
                sort_keys=True,
            )
        )
        return 0
    if selected.command == "start":
        run_dir = start_release(
            selected.runs_root,
            commit=selected.commit,
            image_digest=selected.image,
            environment=selected.environment,
            operator=selected.operator,
        )
        print(json.dumps(release_summary(run_dir), sort_keys=True))
        print(f"RUN_DIRECTORY={run_dir.resolve()}")
        return 0
    if selected.command == "status":
        print(json.dumps(release_summary(selected.run), indent=2, sort_keys=True))
        return 0
    if selected.command == "verify":
        metadata = verify_run(selected.run)
        print(
            json.dumps(
                {
                    "run_id": metadata["run_id"],
                    "evidence_chain_valid": True,
                    "cloud_mutation_executed_by_controller": False,
                },
                sort_keys=True,
            )
        )
        return 0

    event = record_gate(
        selected.run,
        gate_id=selected.gate,
        outcome=selected.outcome,
        evidence_reference=selected.evidence,
        operator=selected.operator,
        mutation_performed=selected.mutation_performed,
        authorization_reference=selected.authorization_reference,
        failure_classification=selected.failure_classification,
        remediation=selected.remediation,
        safe_next_action=selected.safe_next_action,
    )
    print(json.dumps(event, sort_keys=True))
    print(json.dumps(release_summary(selected.run), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
