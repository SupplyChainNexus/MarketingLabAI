"""Structured, fail-closed, read-only Google Cloud preflight."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Mapping, Protocol, Sequence

from deployment.private_synthetic_bootstrap import (
    APPROVED_INGRESS,
    BootstrapObservation,
    ServiceState,
    plan_revision_creation,
)
from tools.release_control.store import canonical_json, sha256_bytes

READ_ONLY_COMMAND_PREFIXES = {
    ("projects", "describe"),
    ("projects", "get-iam-policy"),
    ("services", "list"),
    ("iam", "service-accounts", "describe"),
    ("artifacts", "repositories", "describe"),
    ("artifacts", "docker", "images", "describe"),
    ("sql", "instances", "describe"),
    ("secrets", "describe"),
    ("secrets", "versions", "list"),
    ("secrets", "get-iam-policy"),
    ("run", "services", "list"),
    ("run", "services", "get-iam-policy"),
}
PUBLIC_MEMBERS = {"allUsers", "allAuthenticatedUsers"}


@dataclass(frozen=True, slots=True)
class CloudJsonResult:
    payload: object
    sha256: str


class CloudJsonReader(Protocol):
    def read(self, label: str, arguments: Sequence[str]) -> CloudJsonResult: ...


class GcloudJsonReader:
    """Execute an explicit allowlist of JSON-producing read-only commands."""

    def __init__(self, executable: str, *, timeout_seconds: int = 90):
        self.executable = executable
        self.timeout_seconds = timeout_seconds

    @classmethod
    def from_environment(cls) -> "GcloudJsonReader":
        configured = os.environ.get("MLAI_GCLOUD_EXECUTABLE", "").strip()
        executable = configured or shutil.which("gcloud.cmd") or shutil.which("gcloud")
        if not executable:
            raise ValueError(
                "Pinned gcloud executable was not found; set MLAI_GCLOUD_EXECUTABLE."
            )
        return cls(str(Path(executable).resolve()))

    def read(self, label: str, arguments: Sequence[str]) -> CloudJsonResult:
        selected = tuple(str(item) for item in arguments)
        permitted = any(
            selected[: len(prefix)] == prefix for prefix in READ_ONLY_COMMAND_PREFIXES
        )
        if not permitted:
            raise ValueError(
                f"Cloud command is not on the read-only allowlist: {label}"
            )
        if any(item.startswith("--format") for item in selected):
            raise ValueError("Cloud command format is owned by the JSON reader.")
        completed = subprocess.run(
            [self.executable, *selected, "--format=json"],
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=self.timeout_seconds,
            shell=False,
        )
        if completed.returncode != 0:
            detail = completed.stderr.strip().splitlines()
            summary = detail[-1] if detail else "no diagnostic was returned"
            raise ValueError(
                f"Read-only cloud inspection failed for {label}: {summary}"
            )
        try:
            payload = json.loads(completed.stdout)
        except json.JSONDecodeError as error:
            raise ValueError(
                f"Cloud inspection returned invalid JSON: {label}"
            ) from error
        return CloudJsonResult(
            payload=payload,
            sha256=sha256_bytes(canonical_json(payload)),
        )


def _mapping(value: object, label: str) -> Mapping[str, object]:
    if not isinstance(value, dict):
        raise ValueError(f"Cloud preflight expected an object: {label}")
    return value


def _list(value: object, label: str) -> list[object]:
    if not isinstance(value, list):
        raise ValueError(f"Cloud preflight expected a list: {label}")
    return value


def _nested(value: Mapping[str, object], *keys: str) -> object:
    selected: object = value
    for key in keys:
        if not isinstance(selected, dict):
            return None
        selected = selected.get(key)
    return selected


def _bindings(policy: Mapping[str, object]) -> dict[str, set[str]]:
    result: dict[str, set[str]] = {}
    for item in _list(policy.get("bindings", []), "IAM bindings"):
        binding = _mapping(item, "IAM binding")
        role = str(binding.get("role", ""))
        members = {str(member) for member in _list(binding.get("members", []), role)}
        result.setdefault(role, set()).update(members)
    return result


def run_cloud_preflight(
    configuration: Mapping[str, object],
    *,
    image_digest: str,
    reader: CloudJsonReader,
) -> dict[str, object]:
    """Return minimized evidence or fail without mutating Google Cloud."""

    project = str(configuration["project"])
    region = str(configuration["region"])
    service = str(configuration["service"])
    repository = str(configuration["repository"])
    runtime = str(configuration["runtime_service_account"])
    builder = str(configuration["builder_service_account"])
    sql_instance = str(configuration["cloud_sql_instance"])
    required_apis = {str(item) for item in configuration["required_apis"]}
    secrets = tuple(str(item) for item in configuration["secrets"])
    observations: dict[str, str] = {}

    def inspect(label: str, *arguments: str) -> object:
        result = reader.read(label, arguments)
        observations[label] = result.sha256
        return result.payload

    project_state = _mapping(
        inspect("project", "projects", "describe", project), "project"
    )
    if project_state.get("lifecycleState") != "ACTIVE":
        raise ValueError("Google Cloud project is not ACTIVE.")

    service_rows = _list(
        inspect(
            "enabled_apis", "services", "list", "--enabled", f"--project={project}"
        ),
        "enabled APIs",
    )
    enabled_apis = {
        str(_nested(_mapping(row, "enabled API"), "config", "name"))
        for row in service_rows
    }
    missing_apis = sorted(required_apis - enabled_apis)
    if missing_apis:
        raise ValueError(f"Required Google APIs are disabled: {missing_apis}")

    accounts: dict[str, dict[str, object]] = {}
    for kind, email in (("runtime", runtime), ("builder", builder)):
        account = _mapping(
            inspect(
                f"{kind}_identity",
                "iam",
                "service-accounts",
                "describe",
                email,
                f"--project={project}",
            ),
            f"{kind} identity",
        )
        if account.get("disabled") is True or account.get("email") != email:
            raise ValueError(f"{kind.title()} service account is missing or disabled.")
        accounts[kind] = {"email": email, "disabled": False}

    repository_state = _mapping(
        inspect(
            "artifact_repository",
            "artifacts",
            "repositories",
            "describe",
            repository,
            f"--location={region}",
            f"--project={project}",
        ),
        "artifact repository",
    )
    if (
        repository_state.get("format") != "DOCKER"
        or _nested(repository_state, "dockerConfig", "immutableTags") is not True
    ):
        raise ValueError("Artifact repository is not immutable DOCKER storage.")

    image_state = _mapping(
        inspect(
            "artifact_image",
            "artifacts",
            "docker",
            "images",
            "describe",
            image_digest,
            f"--project={project}",
        ),
        "artifact image",
    )
    observed_digest = str(
        _nested(image_state, "image_summary", "digest") or image_state.get("digest", "")
    )
    if not image_digest.endswith(f"@{observed_digest}"):
        raise ValueError("Artifact Registry digest does not match the release index.")

    sql_state = _mapping(
        inspect(
            "cloud_sql",
            "sql",
            "instances",
            "describe",
            sql_instance,
            f"--project={project}",
        ),
        "Cloud SQL",
    )
    if (
        sql_state.get("state") != "RUNNABLE"
        or sql_state.get("region") != region
        or sql_state.get("databaseVersion") != configuration["cloud_sql_version"]
    ):
        raise ValueError("Cloud SQL state, region or PostgreSQL version has drifted.")

    project_policy = _mapping(
        inspect(
            "project_iam",
            "projects",
            "get-iam-policy",
            project,
        ),
        "project IAM",
    )
    project_bindings = _bindings(project_policy)
    runtime_member = f"serviceAccount:{runtime}"
    if runtime_member not in project_bindings.get("roles/cloudsql.client", set()):
        raise ValueError("Runtime identity does not have Cloud SQL Client authority.")

    secret_evidence: list[dict[str, object]] = []
    project_secret_access = runtime_member in project_bindings.get(
        "roles/secretmanager.secretAccessor", set()
    )
    for secret in secrets:
        metadata = _mapping(
            inspect(
                f"secret_{secret}",
                "secrets",
                "describe",
                secret,
                f"--project={project}",
            ),
            f"secret {secret}",
        )
        if not str(metadata.get("name", "")).endswith(f"/secrets/{secret}"):
            raise ValueError(f"Secret metadata identity mismatch: {secret}")
        versions = _list(
            inspect(
                f"secret_versions_{secret}",
                "secrets",
                "versions",
                "list",
                secret,
                f"--project={project}",
                "--filter=state=ENABLED",
            ),
            f"secret versions {secret}",
        )
        enabled_count = sum(
            1
            for version in versions
            if _mapping(version, f"secret version {secret}").get("state") == "ENABLED"
        )
        if enabled_count < 1:
            raise ValueError(f"Secret has no enabled version: {secret}")
        policy = _mapping(
            inspect(
                f"secret_iam_{secret}",
                "secrets",
                "get-iam-policy",
                secret,
                f"--project={project}",
            ),
            f"secret IAM {secret}",
        )
        direct_access = runtime_member in _bindings(policy).get(
            "roles/secretmanager.secretAccessor", set()
        )
        if not project_secret_access and not direct_access:
            raise ValueError(
                f"Runtime identity cannot access secret metadata target: {secret}"
            )
        secret_evidence.append({"name": secret, "enabled_version_count": enabled_count})

    cloud_run_rows = _list(
        inspect(
            "cloud_run_services",
            "run",
            "services",
            "list",
            f"--project={project}",
            f"--region={region}",
            "--platform=managed",
        ),
        "Cloud Run services",
    )
    targets = [
        _mapping(row, "Cloud Run service")
        for row in cloud_run_rows
        if str(_nested(_mapping(row, "Cloud Run service"), "metadata", "name"))
        == service
    ]
    if len(targets) > 1:
        raise ValueError("Canonical Cloud Run target is ambiguous.")
    public_count = 0
    invoker_count = 0
    ingress: str | None = None
    if targets:
        target = targets[0]
        ingress_value = _nested(target, "metadata", "annotations")
        annotations = ingress_value if isinstance(ingress_value, dict) else {}
        ingress = str(annotations.get("run.googleapis.com/ingress", "")) or None
        target_policy = _mapping(
            inspect(
                "cloud_run_target_iam",
                "run",
                "services",
                "get-iam-policy",
                service,
                f"--project={project}",
                f"--region={region}",
                "--platform=managed",
            ),
            "Cloud Run target IAM",
        )
        invokers = _bindings(target_policy).get("roles/run.invoker", set())
        public_count = len(invokers & PUBLIC_MEMBERS)
        invoker_count = len(invokers - PUBLIC_MEMBERS)
        state = (
            ServiceState.EXISTING_PUBLIC
            if public_count
            else (
                ServiceState.EXISTING_PRIVATE
                if ingress == APPROVED_INGRESS
                else ServiceState.AMBIGUOUS
            )
        )
    else:
        state = ServiceState.ABSENT

    baseline_sha256 = sha256_bytes(canonical_json(cloud_run_rows))
    bootstrap = plan_revision_creation(
        BootstrapObservation(
            canonical_service_name=service,
            service_state=state,
            cloud_run_baseline_sha256=baseline_sha256,
            immutable_image_digest=image_digest,
            ingress=ingress,
            public_principal_count=public_count,
            pilot_invoker_grant_count=invoker_count,
        )
    )
    if not bootstrap.deployable:
        raise ValueError(f"Cloud Run bootstrap is refused: {bootstrap.refusal_reason}")

    return {
        "schema_version": 1,
        "result": "CLOUD_PREFLIGHT_PASSED",
        "project": {"project_id": project, "lifecycle_state": "ACTIVE"},
        "required_apis": sorted(required_apis),
        "service_accounts": accounts,
        "artifact": {
            "repository": repository,
            "format": "DOCKER",
            "immutable_tags": True,
            "image_digest": image_digest,
        },
        "cloud_sql": {
            "instance": sql_instance,
            "region": region,
            "state": "RUNNABLE",
            "database_version": configuration["cloud_sql_version"],
        },
        "secrets": secret_evidence,
        "iam": {
            "runtime_cloud_sql_client": True,
            "runtime_secret_accessor": True,
            "public_invoker_count": public_count,
        },
        "cloud_run": {
            "service": service,
            "service_state": state.value,
            "baseline_sha256": baseline_sha256,
            "ingress": ingress,
            "pilot_invoker_grant_count": invoker_count,
            "revision_creation_plan": {
                **asdict(bootstrap),
                "creation_mode": bootstrap.creation_mode.value,
            },
        },
        "observation_sha256": observations,
        "secret_values_read": False,
        "cloud_mutation_performed": False,
        "deployment_authorized": False,
    }
