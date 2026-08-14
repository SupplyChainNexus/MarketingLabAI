"""Read-only discovery and deterministic planning for the release executor."""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Mapping, Protocol, Sequence

from tools.release_control.store import (
    canonical_json,
    sha256_bytes,
    sha256_file,
    write_json_atomic,
)

EXPECTED_OPERATOR = "info@supplychainnexus.co.za"
EXPECTED_PROJECT = "marketinglabai-identity-dev"
EXPECTED_EXECUTOR_ID = "mlai-synthetic-release-executor"
EXPECTED_EXECUTOR = "mlai-synthetic-release-executor@marketinglabai-identity-dev.iam.gserviceaccount.com"
TOKEN_CREATOR_ROLE = "roles/iam.serviceAccountTokenCreator"
SAFE_ARGUMENT = re.compile(r"^[A-Za-z0-9@._:/=,+-]+$")
READ_ONLY_COMMANDS = frozenset(
    {
        ("auth", "list"),
        ("projects", "describe"),
        ("projects", "get-iam-policy"),
        ("iam", "service-accounts", "describe"),
        ("iam", "service-accounts", "get-iam-policy"),
        ("iam", "service-accounts", "keys", "list"),
    }
)
REAUTHENTICATION_MARKERS = (
    "reauthentication failed",
    "cannot prompt during non-interactive execution",
    "gcloud auth login",
)
NOT_FOUND_MARKERS = (
    "not_found",
    "not found",
    "does not exist",
    "gaia id not found",
)


class CommandResult(Protocol):
    stdout: str
    stderr: str
    returncode: int


@dataclass(frozen=True, slots=True)
class ExecutorIdentityConfig:
    operator_account: str
    executor_service_account: str
    executor_account_id: str
    configuration: str
    project: str
    executable_environment_variable: str
    platform_adapter: str
    service_account_key_files_allowed: bool

    @classmethod
    def from_payload(cls, payload: Mapping[str, object]) -> "ExecutorIdentityConfig":
        cloud_cli = payload.get("cloud_cli")
        if not isinstance(cloud_cli, dict):
            raise ValueError("Cloud CLI configuration is missing.")
        auth = cloud_cli.get("auth_execution")
        if not isinstance(auth, dict):
            raise ValueError("Cloud auth execution configuration is missing.")
        config = cls(
            operator_account=str(cloud_cli.get("account", "")),
            executor_service_account=str(
                auth.get("release_executor_service_account", "")
            ),
            executor_account_id=EXPECTED_EXECUTOR_ID,
            configuration=str(cloud_cli.get("configuration", "")),
            project=str(cloud_cli.get("project", "")),
            executable_environment_variable=str(
                cloud_cli.get("executable_environment_variable", "")
            ),
            platform_adapter=str(cloud_cli.get("platform_adapter", "")),
            service_account_key_files_allowed=bool(
                auth.get("service_account_key_files_allowed", True)
            ),
        )
        config.validate()
        return config

    def validate(self) -> None:
        if self.operator_account != EXPECTED_OPERATOR:
            raise ValueError("Pinned release operator account has drifted.")
        if self.project != EXPECTED_PROJECT:
            raise ValueError("Pinned release project has drifted.")
        if self.executor_service_account != EXPECTED_EXECUTOR:
            raise ValueError("Pinned release executor identity has drifted.")
        if self.service_account_key_files_allowed:
            raise ValueError("Service-account key files must remain forbidden.")
        if self.platform_adapter != "windows-gcloud-cmd-v2":
            raise ValueError("Unexpected Cloud CLI platform adapter.")


def _mapping(value: object, label: str) -> Mapping[str, object]:
    if not isinstance(value, dict):
        raise ValueError(f"Expected JSON object for {label}.")
    return value


def _sequence(value: object, label: str) -> Sequence[object]:
    if not isinstance(value, list):
        raise ValueError(f"Expected JSON array for {label}.")
    return value


def _members_by_role(policy: object) -> dict[str, set[str]]:
    selected = _mapping(policy, "IAM policy")
    bindings = selected.get("bindings", [])
    result: dict[str, set[str]] = {}
    for item in _sequence(bindings, "IAM bindings"):
        binding = _mapping(item, "IAM binding")
        role = str(binding.get("role", ""))
        members = binding.get("members", [])
        if role and isinstance(members, list):
            result.setdefault(role, set()).update(str(member) for member in members)
    return result


class ReadOnlyExecutorIdentityInspector:
    """Inspect bootstrap state with direct operator auth and no impersonation."""

    def __init__(
        self,
        config: ExecutorIdentityConfig,
        *,
        executable: str | None = None,
        runner: Callable[..., CommandResult] = subprocess.run,
    ):
        config.validate()
        configured = os.environ.get(config.executable_environment_variable, "").strip()
        selected = (
            executable
            or configured
            or shutil.which("gcloud.cmd")
            or shutil.which("gcloud")
        )
        if not selected:
            raise ValueError(
                "Cloud SDK executable not found; set "
                f"{config.executable_environment_variable}."
            )
        self.config = config
        self.executable = str(Path(selected).resolve())
        self.runner = runner

    def _command(self, arguments: Sequence[str]) -> list[str]:
        selected = tuple(str(item) for item in arguments)
        prefix = next(
            (
                candidate
                for candidate in READ_ONLY_COMMANDS
                if selected[: len(candidate)] == candidate
            ),
            None,
        )
        if prefix is None:
            raise ValueError("Executor identity inspection command is not read-only.")
        for argument in selected:
            if not argument or not SAFE_ARGUMENT.fullmatch(argument):
                raise ValueError(
                    "Executor identity inspection contains an unsafe argument."
                )
            if argument.startswith("--impersonate-service-account"):
                raise ValueError(
                    "Bootstrap inspection may not impersonate the absent executor."
                )
        return [
            self.executable,
            *selected,
            f"--account={self.config.operator_account}",
            f"--configuration={self.config.configuration}",
            f"--project={self.config.project}",
            "--quiet",
            "--format=json",
        ]

    def _execute(
        self,
        label: str,
        arguments: Sequence[str],
        *,
        not_found_allowed: bool = False,
    ) -> tuple[object | None, str | None]:
        command = self._command(arguments)
        invocation: str | list[str] = command
        use_shell = False
        if self.config.platform_adapter == "windows-gcloud-cmd-v2":
            invocation = subprocess.list2cmdline(command)
            use_shell = True
        completed = self.runner(
            invocation,
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=90,
            shell=use_shell,
        )
        if completed.returncode != 0:
            detail = completed.stderr.strip() or "no diagnostic was returned"
            lowered = detail.casefold()
            if any(marker in lowered for marker in REAUTHENTICATION_MARKERS):
                raise ValueError(
                    "Operator reauthentication is required before read-only identity "
                    "inspection; no automatic retry was performed."
                )
            if not_found_allowed and any(
                marker in lowered for marker in NOT_FOUND_MARKERS
            ):
                return None, None
            raise ValueError(
                f"Read-only executor inspection failed for {label}: {detail}"
            )
        try:
            payload = json.loads(completed.stdout)
        except json.JSONDecodeError as error:
            raise ValueError(
                f"Read-only executor inspection returned invalid JSON for {label}."
            ) from error
        return payload, sha256_bytes(canonical_json(payload))

    def inspect(self) -> dict[str, object]:
        accounts, accounts_sha256 = self._execute(
            "authenticated accounts", ("auth", "list")
        )
        active = [
            _mapping(item, "authenticated account")
            for item in _sequence(accounts, "authenticated accounts")
            if str(_mapping(item, "authenticated account").get("status", "")).upper()
            == "ACTIVE"
        ]
        if (
            len(active) != 1
            or str(active[0].get("account", "")) != self.config.operator_account
        ):
            raise ValueError("Pinned operator is not the one active Cloud CLI account.")

        project, project_sha256 = self._execute(
            "project", ("projects", "describe", self.config.project)
        )
        project_mapping = _mapping(project, "project")
        if str(project_mapping.get("projectId", "")) != self.config.project:
            raise ValueError(
                "Read-only project identity does not match the pinned project."
            )

        service_account, service_account_sha256 = self._execute(
            "release executor service account",
            (
                "iam",
                "service-accounts",
                "describe",
                self.config.executor_service_account,
            ),
            not_found_allowed=True,
        )
        exists = service_account is not None
        token_creator_present = False
        user_managed_key_count = 0
        service_account_policy_sha256: str | None = None
        user_managed_keys_sha256: str | None = None
        if exists:
            account_mapping = _mapping(service_account, "release executor")
            if (
                str(account_mapping.get("email", ""))
                != self.config.executor_service_account
            ):
                raise ValueError(
                    "Observed release executor identity does not match the pin."
                )
            policy, service_account_policy_sha256 = self._execute(
                "release executor IAM policy",
                (
                    "iam",
                    "service-accounts",
                    "get-iam-policy",
                    self.config.executor_service_account,
                ),
            )
            token_creator_present = (
                f"user:{self.config.operator_account}"
                in _members_by_role(policy).get(TOKEN_CREATOR_ROLE, set())
            )
            keys, user_managed_keys_sha256 = self._execute(
                "release executor user-managed keys",
                (
                    "iam",
                    "service-accounts",
                    "keys",
                    "list",
                    f"--iam-account={self.config.executor_service_account}",
                    "--managed-by=user",
                ),
            )
            user_managed_key_count = len(_sequence(keys, "user-managed keys"))

        project_policy, project_policy_sha256 = self._execute(
            "project IAM policy",
            ("projects", "get-iam-policy", self.config.project),
        )
        executor_member = f"serviceAccount:{self.config.executor_service_account}"
        executor_roles = sorted(
            role
            for role, members in _members_by_role(project_policy).items()
            if executor_member in members
        )
        return {
            "schema_version": 1,
            "kind": "release-executor-identity-inspection",
            "result": "RELEASE_EXECUTOR_IDENTITY_INSPECTION_COMPLETED",
            "operator_account": self.config.operator_account,
            "project": self.config.project,
            "executor_service_account": self.config.executor_service_account,
            "service_account_exists": exists,
            "operator_token_creator_binding_present": token_creator_present,
            "user_managed_key_count": user_managed_key_count,
            "executor_project_roles": executor_roles,
            "authenticated_accounts_sha256": accounts_sha256,
            "project_metadata_sha256": project_sha256,
            "service_account_metadata_sha256": service_account_sha256,
            "service_account_policy_sha256": service_account_policy_sha256,
            "user_managed_keys_sha256": user_managed_keys_sha256,
            "project_iam_policy_sha256": project_policy_sha256,
            "operator_direct_read_only": True,
            "cloud_cli_executed": True,
            "cloud_resource_inspection_performed": True,
            "cloud_mutation_performed": False,
            "iam_mutation_performed": False,
            "service_account_created": False,
            "service_account_key_created": False,
            "release_state_modified": False,
            "automatic_retry_performed": False,
        }


def write_inspection(path: Path, inspection: Mapping[str, object]) -> str:
    return write_json_atomic(path, inspection)


def _validate_inspection(inspection: Mapping[str, object]) -> None:
    expected = {
        "schema_version": 1,
        "kind": "release-executor-identity-inspection",
        "result": "RELEASE_EXECUTOR_IDENTITY_INSPECTION_COMPLETED",
        "operator_account": EXPECTED_OPERATOR,
        "project": EXPECTED_PROJECT,
        "executor_service_account": EXPECTED_EXECUTOR,
        "cloud_mutation_performed": False,
        "iam_mutation_performed": False,
        "service_account_created": False,
        "service_account_key_created": False,
        "release_state_modified": False,
    }
    for key, value in expected.items():
        if inspection.get(key) != value:
            raise ValueError(f"Executor inspection contract mismatch: {key}.")
    key_count = inspection.get("user_managed_key_count")
    if not isinstance(key_count, int) or isinstance(key_count, bool) or key_count < 0:
        raise ValueError("Executor inspection key count is invalid.")
    if key_count:
        raise ValueError(
            "Release executor has user-managed key files; bootstrap planning is blocked."
        )


def prepare_identity_bootstrap_plan(
    inspection: Mapping[str, object],
    *,
    inspection_sha256: str,
    repository_commit: str,
) -> dict[str, object]:
    """Create a deterministic plan; this function cannot execute Cloud CLI."""

    _validate_inspection(inspection)
    if not re.fullmatch(r"[0-9a-f]{64}", inspection_sha256):
        raise ValueError("Inspection SHA-256 is invalid.")
    if not re.fullmatch(r"[0-9a-f]{40}", repository_commit):
        raise ValueError("Repository commit must be a full Git commit SHA.")

    actions: list[dict[str, object]] = []
    if inspection.get("service_account_exists") is not True:
        actions.append(
            {
                "sequence": len(actions) + 1,
                "action": "create_release_executor_service_account",
                "mutation_scope": "service-account-create",
                "command": [
                    "gcloud",
                    "iam",
                    "service-accounts",
                    "create",
                    EXPECTED_EXECUTOR_ID,
                    f"--project={EXPECTED_PROJECT}",
                    "--display-name=MarketingLabAI Synthetic Release Executor",
                    "--description=Non-interactive executor for controlled synthetic releases",
                ],
            }
        )
    if inspection.get("operator_token_creator_binding_present") is not True:
        actions.append(
            {
                "sequence": len(actions) + 1,
                "action": "grant_operator_token_creator_on_release_executor",
                "mutation_scope": "service-account-iam-binding",
                "command": [
                    "gcloud",
                    "iam",
                    "service-accounts",
                    "add-iam-policy-binding",
                    EXPECTED_EXECUTOR,
                    f"--member=user:{EXPECTED_OPERATOR}",
                    f"--role={TOKEN_CREATOR_ROLE}",
                    f"--project={EXPECTED_PROJECT}",
                ],
            }
        )

    plan_without_digest: dict[str, object] = {
        "schema_version": 1,
        "kind": "release-executor-identity-bootstrap-plan",
        "story": "MLAI-031.16",
        "adr": "ADR-0049",
        "operator_account": EXPECTED_OPERATOR,
        "project": EXPECTED_PROJECT,
        "executor_service_account": EXPECTED_EXECUTOR,
        "inspection_sha256": inspection_sha256,
        "repository_commit": repository_commit,
        "status": (
            "ready_for_plan_bound_approval" if actions else "already_bootstrapped"
        ),
        "approval_required": bool(actions),
        "actions": actions,
        "maximum_iam_mutation_count": len(actions),
        "service_account_key_files_allowed": False,
        "execution_permission_grants_included": False,
        "execution_permission_contract": "separate-evidence-bound-authorization-required",
        "workload_identity_configuration_included": False,
        "may_mutate_iam_when_separately_authorized": bool(actions),
        "cloud_cli_executed_during_planning": False,
        "cloud_mutation_performed": False,
        "iam_mutation_performed": False,
        "service_account_created": False,
        "service_account_key_created": False,
        "release_state_modified": False,
        "deployment_performed": False,
    }
    digest = sha256_bytes(canonical_json(plan_without_digest))
    return {**plan_without_digest, "plan_digest": digest}


def prepare_identity_bootstrap_plan_from_file(
    inspection_path: Path,
    *,
    repository_commit: str,
) -> dict[str, object]:
    payload = json.loads(inspection_path.read_text(encoding="utf-8-sig"))
    if not isinstance(payload, dict):
        raise ValueError("Executor inspection evidence must be a JSON object.")
    return prepare_identity_bootstrap_plan(
        payload,
        inspection_sha256=sha256_file(inspection_path),
        repository_commit=repository_commit,
    )


def write_identity_bootstrap_plan(path: Path, plan: Mapping[str, object]) -> str:
    expected = plan.get("plan_digest")
    unsigned = {key: value for key, value in plan.items() if key != "plan_digest"}
    actual = sha256_bytes(canonical_json(unsigned))
    if expected != actual:
        raise ValueError("Release executor bootstrap plan digest is invalid.")
    return write_json_atomic(path, plan)
