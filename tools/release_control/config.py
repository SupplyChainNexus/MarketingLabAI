"""Versioned release-control configuration and reproducibility checks."""

from __future__ import annotations

import hashlib
import json
import os
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping

from deployment.private_synthetic_manifest import validate_template
from deployment.release_controller import load_catalog
from deployment.zero_trust_supply_chain import load_policy
from tools.release_control.auth_execution import validate_auth_execution_payload

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CONFIG = ROOT / "tools" / "release_control_plane.json"
DEPENDENCY_LOCK_HASH_MODE = "utf8-sig-lf-v1"


@dataclass(frozen=True, slots=True)
class ControlConfig:
    path: Path
    repository_root: Path
    payload: Mapping[str, object]

    @property
    def environment(self) -> str:
        return str(self.payload["environment"])

    @property
    def supported_apply_gates(self) -> frozenset[str]:
        return frozenset(str(item) for item in self.payload["supported_apply_gates"])

    def state_root(self, selected: Path | None = None) -> Path:
        if selected is not None:
            return selected.expanduser().resolve()
        variable = str(self.payload["state_root_environment_variable"])
        configured = os.environ.get(variable)
        if configured:
            return Path(configured).expanduser().resolve()
        if os.name == "nt":
            return Path(str(self.payload["default_windows_state_root"])).resolve()
        raise ValueError(
            f"State root is required outside Windows; pass --state-root or set {variable}."
        )


def load_config(path: Path = DEFAULT_CONFIG) -> ControlConfig:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload.get("schema_version") != 1:
        raise ValueError("Unsupported release-control configuration schema.")
    text = path.read_text(encoding="utf-8")
    if re.search(r"MLAI-\d+", text):
        raise ValueError(
            "Release-control configuration contains a story-numbered path."
        )
    if payload.get("environment") != "cloud-synthetic":
        raise ValueError("Only cloud-synthetic release control is supported.")
    authorities = payload.get("authorities")
    if not isinstance(authorities, dict):
        raise ValueError("Release-control authority separation is missing.")
    expected = {
        "orchestration": "tools.release_control",
        "observational_history": "deployment.release_controller",
        "admission": "external-zero-trust-binary-authorization",
    }
    if authorities != expected:
        raise ValueError("Release-control authority separation has drifted.")
    preflight = payload.get("cloud_preflight")
    if not isinstance(preflight, dict):
        raise ValueError("Cloud preflight configuration is missing.")
    expected_preflight = {
        "project": "marketinglabai-identity-dev",
        "region": "africa-south1",
        "service": "marketinglabai-velani-pilot",
        "repository": "mlai-synthetic",
        "runtime_service_account": (
            "mlai-synthetic-runtime@marketinglabai-identity-dev.iam.gserviceaccount.com"
        ),
        "builder_service_account": (
            "mlai-synthetic-builder@marketinglabai-identity-dev.iam.gserviceaccount.com"
        ),
        "cloud_sql_instance": "mlai-synthetic-pg18-jhb",
        "cloud_sql_version": "POSTGRES_18",
    }
    if any(preflight.get(key) != value for key, value in expected_preflight.items()):
        raise ValueError("Cloud preflight resource identities have drifted.")
    cloud_cli = payload.get("cloud_cli")
    expected_cloud_cli = {
        "account": "info@supplychainnexus.co.za",
        "configuration": "default",
        "project": "marketinglabai-identity-dev",
        "executable_environment_variable": "MLAI_GCLOUD_EXECUTABLE",
        "platform_adapter": "windows-gcloud-cmd-v2",
        "auth_execution": {
            "phase": "local-operator-auth-service-account-impersonation",
            "release_executor_service_account": (
                "mlai-synthetic-release-executor@marketinglabai-identity-dev.iam.gserviceaccount.com"
            ),
            "service_account_key_files_allowed": False,
            "phase_2": "ci-cd-workload-identity",
        },
    }
    if cloud_cli != expected_cloud_cli:
        raise ValueError("Pinned Cloud CLI execution context has drifted.")
    validate_auth_execution_payload(payload)
    revision_creation = payload.get("revision_creation")
    expected_revision_creation = {
        "project": "marketinglabai-identity-dev",
        "region": "africa-south1",
        "service": "marketinglabai-velani-pilot",
        "runtime_service_account": (
            "mlai-synthetic-runtime@marketinglabai-identity-dev.iam.gserviceaccount.com"
        ),
        "manifest_template": "deployment/cloud-run.private-synthetic.yaml.template",
        "command": "gcloud run services replace",
        "traffic_routing_authorized": False,
        "public_access_authorized": False,
        "secret_value_access_authorized": False,
    }
    if revision_creation != expected_revision_creation:
        raise ValueError("Cloud Run revision-creation contract has drifted.")
    required_apis = preflight.get("required_apis")
    secrets = preflight.get("secrets")
    if not isinstance(required_apis, list) or len(required_apis) != len(
        set(required_apis)
    ):
        raise ValueError("Cloud preflight API contract is invalid.")
    if (
        not isinstance(secrets, list)
        or len(secrets) != 4
        or len(secrets) != len(set(secrets))
    ):
        raise ValueError("Cloud preflight secret metadata contract is invalid.")
    forbidden = payload.get("forbidden_authority_claims")
    if not isinstance(forbidden, dict) or any(
        value is not False for value in forbidden.values()
    ):
        raise ValueError("Forbidden release-authority claims must remain false.")
    return ControlConfig(path=path, repository_root=ROOT, payload=payload)


def _python_version(config: ControlConfig) -> dict[str, object]:
    python = config.payload["python"]
    if not isinstance(python, dict):
        raise ValueError("Python runtime policy is missing.")
    minimum = tuple(int(item) for item in python["minimum"])
    maximum = tuple(int(item) for item in python["maximum_exclusive"])
    current = sys.version_info[:2]
    if current < minimum or current >= maximum:
        raise ValueError(
            f"Python {current[0]}.{current[1]} is outside the pinned supported range "
            f">={minimum[0]}.{minimum[1]}, <{maximum[0]}.{maximum[1]}."
        )
    return {
        "executable": str(Path(sys.executable).resolve()),
        "version": f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
        "supported": True,
    }


def canonical_dependency_lock_sha256(path: Path) -> str:
    """Hash dependency semantics without platform-specific text encoding drift."""

    text = path.read_text(encoding="utf-8-sig")
    canonical = text.replace("\r\n", "\n").replace("\r", "\n")
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def validate_repository(config: ControlConfig) -> dict[str, object]:
    if config.payload.get("dependency_lock_hash_mode") != DEPENDENCY_LOCK_HASH_MODE:
        raise ValueError("Dependency lock hash mode has drifted.")
    dependency_locks = config.payload["dependency_locks"]
    if not isinstance(dependency_locks, dict) or not dependency_locks:
        raise ValueError("Dependency lock hashes are missing.")
    verified_locks: dict[str, str] = {}
    for relative, expected in dependency_locks.items():
        path = config.repository_root / str(relative)
        actual = canonical_dependency_lock_sha256(path)
        if actual != expected:
            raise ValueError(f"Pinned dependency lock has drifted: {relative}")
        for line in path.read_text(encoding="utf-8-sig").splitlines():
            selected = line.strip()
            if (
                selected
                and not selected.startswith("#")
                and not selected.startswith("-r ")
            ):
                if "==" not in selected:
                    raise ValueError(f"Dependency is not exactly pinned: {selected}")
        verified_locks[str(relative)] = actual

    gates = load_catalog()
    policy = load_policy()
    template_path = (
        config.repository_root
        / "deployment"
        / "cloud-run.private-synthetic.yaml.template"
    )
    template_report = validate_template(template_path.read_text(encoding="utf-8-sig"))
    auth_execution = validate_auth_execution_payload(config.payload)
    return {
        "schema_version": 1,
        "repository_valid": True,
        "python": _python_version(config),
        "dependency_lock_hash_mode": DEPENDENCY_LOCK_HASH_MODE,
        "dependency_locks": verified_locks,
        "gate_count": len(gates),
        "policy_mode": policy["mode"],
        "template": template_report,
        "authority_separation": dict(config.payload["authorities"]),
        "cloud_cli": dict(config.payload["cloud_cli"]),
        "auth_execution": auth_execution,
        "revision_creation": dict(config.payload["revision_creation"]),
        "cloud_mutation_performed": False,
        "deployment_authorized": False,
    }
