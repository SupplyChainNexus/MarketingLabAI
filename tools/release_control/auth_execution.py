"""Non-interactive Cloud SDK execution boundary for release operations."""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Mapping, Protocol, Sequence

from tools.release_control.store import canonical_json, sha256_bytes

SAFE_ARGUMENT = re.compile(r"^[A-Za-z0-9@._:/=,+-]+$")
FORBIDDEN_KEY_FILE_ENVIRONMENT = (
    "GOOGLE_APPLICATION_CREDENTIALS",
    "CLOUDSDK_AUTH_CREDENTIAL_FILE_OVERRIDE",
)
OWNED_GLOBAL_FLAG_PREFIXES = (
    "--account",
    "--configuration",
    "--format",
    "--impersonate-service-account",
    "--project",
    "--quiet",
)


@dataclass(frozen=True, slots=True)
class CloudAuthExecutionConfig:
    operator_account: str
    executor_service_account: str
    configuration: str
    project: str
    executable_environment_variable: str
    platform_adapter: str
    service_account_key_files_allowed: bool
    phase: str

    @classmethod
    def from_payload(cls, payload: Mapping[str, object]) -> "CloudAuthExecutionConfig":
        cloud_cli = payload.get("cloud_cli")
        if not isinstance(cloud_cli, dict):
            raise ValueError("Cloud CLI configuration is missing.")
        auth = cloud_cli.get("auth_execution")
        if not isinstance(auth, dict):
            raise ValueError("Cloud auth execution boundary is missing.")
        return cls(
            operator_account=str(cloud_cli["account"]),
            executor_service_account=str(auth["release_executor_service_account"]),
            configuration=str(cloud_cli["configuration"]),
            project=str(cloud_cli["project"]),
            executable_environment_variable=str(
                cloud_cli["executable_environment_variable"]
            ),
            platform_adapter=str(cloud_cli["platform_adapter"]),
            service_account_key_files_allowed=bool(
                auth["service_account_key_files_allowed"]
            ),
            phase=str(auth["phase"]),
        )


class JsonCommandResult(Protocol):
    stdout: str
    stderr: str
    returncode: int


class CloudAuthExecutionBoundary:
    """Build and verify release Cloud SDK commands with impersonation."""

    def __init__(
        self,
        config: CloudAuthExecutionConfig,
        *,
        executable: str | None = None,
        runner: Callable[..., JsonCommandResult] = subprocess.run,
    ):
        self.config = config
        configured = os.environ.get(config.executable_environment_variable, "").strip()
        selected = (
            executable
            or configured
            or shutil.which("gcloud.cmd")
            or shutil.which("gcloud")
        )
        if not selected:
            raise ValueError(
                f"Cloud SDK executable not found; set {config.executable_environment_variable}."
            )
        self.executable = str(Path(selected).resolve())
        self.runner = runner

    def assert_no_key_file_credentials(self) -> None:
        if self.config.service_account_key_files_allowed:
            raise ValueError("Service-account key files must remain forbidden.")
        present = [
            name
            for name in FORBIDDEN_KEY_FILE_ENVIRONMENT
            if os.environ.get(name, "").strip()
        ]
        if present:
            raise ValueError(
                "Service-account key-file environment variables are forbidden: "
                + ", ".join(present)
            )

    def _validate_arguments(self, arguments: Sequence[str]) -> tuple[str, ...]:
        selected = tuple(str(item) for item in arguments)
        for argument in selected:
            if not argument or not SAFE_ARGUMENT.fullmatch(argument):
                raise ValueError("Cloud command contains an unsafe argument.")
            if argument.startswith(OWNED_GLOBAL_FLAG_PREFIXES):
                raise ValueError("Cloud command contains adapter-owned global flags.")
        return selected

    def command(
        self, arguments: Sequence[str], *, json_output: bool = True
    ) -> list[str]:
        selected = self._validate_arguments(arguments)
        command = [
            self.executable,
            *selected,
            f"--account={self.config.operator_account}",
            f"--configuration={self.config.configuration}",
            f"--project={self.config.project}",
            f"--impersonate-service-account={self.config.executor_service_account}",
            "--quiet",
        ]
        if json_output:
            command.append("--format=json")
        return command

    def run_json(self, label: str, arguments: Sequence[str]) -> tuple[object, str]:
        self.assert_no_key_file_credentials()
        command = self.command(arguments, json_output=True)
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
            raise ValueError(
                f"Non-interactive auth command failed for {label}: {detail}"
            )
        try:
            payload = json.loads(completed.stdout)
        except json.JSONDecodeError as error:
            raise ValueError(
                f"Non-interactive auth command returned invalid JSON for {label}."
            ) from error
        return payload, sha256_bytes(canonical_json(payload))

    def probe_impersonated_token(self) -> None:
        self.assert_no_key_file_credentials()
        command = self.command(("auth", "print-access-token"), json_output=False)
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
            raise ValueError(f"Impersonated token probe failed: {detail}")
        if not completed.stdout.strip():
            raise ValueError("Impersonated token probe returned no token.")

    def doctor(self) -> dict[str, object]:
        self.assert_no_key_file_credentials()
        operator_payload, operator_sha256 = self.run_json(
            "operator account", ("auth", "list")
        )
        self.probe_impersonated_token()
        return {
            "schema_version": 1,
            "result": "NON_INTERACTIVE_CLOUD_AUTH_DOCTOR_PASSED",
            "phase": self.config.phase,
            "operator_account": self.config.operator_account,
            "executor_service_account": self.config.executor_service_account,
            "project": self.config.project,
            "configuration": self.config.configuration,
            "platform_adapter": self.config.platform_adapter,
            "service_account_key_files_allowed": False,
            "operator_metadata_sha256": operator_sha256,
            "impersonated_token_probe_passed": True,
            "cloud_mutation_performed": False,
            "release_state_modified": False,
            "deployment_performed": False,
            "secret_value_accessed": False,
            "workload_identity_phase": "phase-2-ci-cd",
        }


def validate_auth_execution_payload(payload: Mapping[str, object]) -> dict[str, object]:
    config = CloudAuthExecutionConfig.from_payload(payload)
    expected_executor = "mlai-synthetic-release-executor@marketinglabai-identity-dev.iam.gserviceaccount.com"
    if config.executor_service_account != expected_executor:
        raise ValueError("Pinned release executor service account has drifted.")
    if config.service_account_key_files_allowed:
        raise ValueError("Service-account key files must remain forbidden.")
    if config.phase != "local-operator-auth-service-account-impersonation":
        raise ValueError("Unexpected non-interactive auth execution phase.")
    return {
        "schema_version": 1,
        "non_interactive_auth_execution_valid": True,
        "operator_account": config.operator_account,
        "executor_service_account": config.executor_service_account,
        "service_account_key_files_allowed": False,
        "phase": config.phase,
        "workload_identity_next_phase": "ci-cd-workload-identity",
    }
