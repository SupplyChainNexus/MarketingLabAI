from __future__ import annotations

import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from tools.release_control.auth_execution import (
    CloudAuthExecutionBoundary,
    CloudAuthExecutionConfig,
    validate_auth_execution_payload,
)


def _payload() -> dict[str, object]:
    return {
        "cloud_cli": {
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
    }


class Completed:
    def __init__(self, stdout: str, returncode: int = 0, stderr: str = ""):
        self.stdout = stdout
        self.returncode = returncode
        self.stderr = stderr


class NonInteractiveCloudAuthTests(unittest.TestCase):
    def test_auth_execution_payload_is_pinned(self) -> None:
        report = validate_auth_execution_payload(_payload())
        self.assertTrue(report["non_interactive_auth_execution_valid"])
        self.assertFalse(report["service_account_key_files_allowed"])
        self.assertEqual(
            "mlai-synthetic-release-executor@marketinglabai-identity-dev.iam.gserviceaccount.com",
            report["executor_service_account"],
        )

    def test_service_account_key_files_are_forbidden(self) -> None:
        config = CloudAuthExecutionConfig.from_payload(_payload())
        with tempfile.TemporaryDirectory() as temporary:
            executable = Path(temporary) / "gcloud.cmd"
            executable.write_text("", encoding="utf-8")
            boundary = CloudAuthExecutionBoundary(config, executable=str(executable))
            with patch.dict(
                os.environ,
                {"GOOGLE_APPLICATION_CREDENTIALS": "C:/unsafe/key.json"},
            ):
                with self.assertRaisesRegex(ValueError, "key-file"):
                    boundary.assert_no_key_file_credentials()

    def test_command_includes_operator_and_impersonated_executor(self) -> None:
        config = CloudAuthExecutionConfig.from_payload(_payload())
        with tempfile.TemporaryDirectory() as temporary:
            executable = Path(temporary) / "gcloud.cmd"
            executable.write_text("", encoding="utf-8")
            boundary = CloudAuthExecutionBoundary(config, executable=str(executable))
            command = boundary.command(
                ("run", "services", "replace", "manifest.yaml"),
                json_output=False,
            )
        self.assertIn("--account=info@supplychainnexus.co.za", command)
        self.assertIn("--project=marketinglabai-identity-dev", command)
        self.assertIn(
            "--impersonate-service-account=mlai-synthetic-release-executor@marketinglabai-identity-dev.iam.gserviceaccount.com",
            command,
        )
        self.assertNotIn("--format=json", command)

    def test_adapter_owns_identity_flags(self) -> None:
        config = CloudAuthExecutionConfig.from_payload(_payload())
        with tempfile.TemporaryDirectory() as temporary:
            executable = Path(temporary) / "gcloud.cmd"
            executable.write_text("", encoding="utf-8")
            boundary = CloudAuthExecutionBoundary(config, executable=str(executable))
            with self.assertRaisesRegex(ValueError, "adapter-owned"):
                boundary.command(("--account=somebody@example.com",))

    def test_doctor_is_non_mutating_and_hashes_metadata(self) -> None:
        config = CloudAuthExecutionConfig.from_payload(_payload())
        calls: list[object] = []

        def runner(*args: object, **kwargs: object) -> Completed:
            calls.append(args[0])
            if "print-access-token" in str(args[0]):
                return Completed("redacted-token")
            return Completed(json.dumps({"ok": True}))

        with tempfile.TemporaryDirectory() as temporary:
            executable = Path(temporary) / "gcloud.cmd"
            executable.write_text("", encoding="utf-8")
            boundary = CloudAuthExecutionBoundary(
                config,
                executable=str(executable),
                runner=runner,
            )
            report = boundary.doctor()
        self.assertEqual("NON_INTERACTIVE_CLOUD_AUTH_DOCTOR_PASSED", report["result"])
        self.assertTrue(report["impersonated_token_probe_passed"])
        self.assertFalse(report["cloud_mutation_performed"])
        self.assertFalse(report["release_state_modified"])
        self.assertEqual(2, len(calls))


if __name__ == "__main__":
    unittest.main()
