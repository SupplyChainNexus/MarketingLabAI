"""Tests for the permanent read-only Google Cloud preflight executor."""

from __future__ import annotations

import copy
import json
import subprocess
import unittest

from tools.release_control.cloud_preflight import (
    CloudJsonResult,
    GcloudJsonReader,
    run_cloud_preflight,
)
from tools.release_control.config import load_config
from tools.release_control.store import canonical_json, sha256_bytes

IMAGE = (
    "africa-south1-docker.pkg.dev/marketinglabai-identity-dev/"
    "mlai-synthetic/marketinglabai-pilot@sha256:" + "a" * 64
)
RUNTIME = "mlai-synthetic-runtime@marketinglabai-identity-dev.iam.gserviceaccount.com"
BUILDER = "mlai-synthetic-builder@marketinglabai-identity-dev.iam.gserviceaccount.com"
ACCOUNT = "info@supplychainnexus.co.za"
PROJECT = "marketinglabai-identity-dev"


def passing_payloads(*, image_digest: str = IMAGE) -> dict[str, object]:
    required_apis = load_config().payload["cloud_preflight"]["required_apis"]
    payloads: dict[str, object] = {
        "project": {
            "projectId": "marketinglabai-identity-dev",
            "lifecycleState": "ACTIVE",
        },
        "enabled_apis": [
            {"config": {"name": name}, "state": "ENABLED"} for name in required_apis
        ],
        "runtime_identity": {"email": RUNTIME, "disabled": False},
        "builder_identity": {"email": BUILDER, "disabled": False},
        "artifact_repository": {
            "format": "DOCKER",
            "dockerConfig": {"immutableTags": True},
        },
        "artifact_image": {
            "image_summary": {"digest": image_digest.rsplit("@", 1)[-1]}
        },
        "cloud_sql": {
            "name": "mlai-synthetic-pg18-jhb",
            "state": "RUNNABLE",
            "region": "africa-south1",
            "databaseVersion": "POSTGRES_18",
        },
        "project_iam": {
            "bindings": [
                {
                    "role": "roles/cloudsql.client",
                    "members": [f"serviceAccount:{RUNTIME}"],
                }
            ]
        },
        "cloud_run_services": [],
    }
    for secret in load_config().payload["cloud_preflight"]["secrets"]:
        payloads[f"secret_{secret}"] = {"name": f"projects/123/secrets/{secret}"}
        payloads[f"secret_versions_{secret}"] = [
            {"name": f"projects/123/secrets/{secret}/versions/1", "state": "ENABLED"}
        ]
        payloads[f"secret_iam_{secret}"] = {
            "bindings": [
                {
                    "role": "roles/secretmanager.secretAccessor",
                    "members": [f"serviceAccount:{RUNTIME}"],
                }
            ]
        }
    return payloads


class FakeCloudReader:
    def __init__(
        self,
        payloads: dict[str, object] | None = None,
        *,
        image_digest: str = IMAGE,
    ):
        self.payloads = payloads or passing_payloads(image_digest=image_digest)
        self.calls: list[tuple[str, tuple[str, ...]]] = []

    def doctor(self):
        return {
            "schema_version": 1,
            "result": "CLOUD_CLI_DOCTOR_PASSED",
            "adapter": "synthetic-cloud-reader-v1",
            "account": ACCOUNT,
            "configuration": "default",
            "project": PROJECT,
            "cloud_mutation_performed": False,
        }

    def read(self, label: str, arguments) -> CloudJsonResult:
        self.calls.append((label, tuple(arguments)))
        payload = self.payloads[label]
        return CloudJsonResult(payload, sha256_bytes(canonical_json(payload)))


class CloudPreflightTests(unittest.TestCase):
    def setUp(self):
        self.configuration = load_config().payload["cloud_preflight"]

    def test_passes_without_secret_values_or_cloud_mutation(self):
        reader = FakeCloudReader()
        result = run_cloud_preflight(
            self.configuration,
            image_digest=IMAGE,
            reader=reader,
        )
        self.assertEqual("CLOUD_PREFLIGHT_PASSED", result["result"])
        self.assertEqual("ABSENT", result["cloud_run"]["service_state"])
        self.assertEqual(
            "FIRST_PRIVATE_REVISION",
            result["cloud_run"]["revision_creation_plan"]["creation_mode"],
        )
        self.assertFalse(result["secret_values_read"])
        self.assertFalse(result["cloud_mutation_performed"])
        self.assertFalse(result["deployment_authorized"])
        flattened = " ".join(
            argument for _, arguments in reader.calls for argument in arguments
        )
        self.assertNotIn("versions access", flattened)
        self.assertNotIn("deploy", flattened)

    def test_disabled_api_fails_closed(self):
        payloads = passing_payloads()
        payloads["enabled_apis"] = payloads["enabled_apis"][:-1]
        with self.assertRaisesRegex(ValueError, "disabled"):
            run_cloud_preflight(
                self.configuration,
                image_digest=IMAGE,
                reader=FakeCloudReader(payloads),
            )

    def test_public_target_fails_closed(self):
        payloads = passing_payloads()
        payloads["cloud_run_services"] = [
            {
                "metadata": {
                    "name": "marketinglabai-velani-pilot",
                    "annotations": {
                        "run.googleapis.com/ingress": "internal-and-cloud-load-balancing"
                    },
                }
            }
        ]
        payloads["cloud_run_target_iam"] = {
            "bindings": [{"role": "roles/run.invoker", "members": ["allUsers"]}]
        }
        with self.assertRaisesRegex(ValueError, "refused"):
            run_cloud_preflight(
                self.configuration,
                image_digest=IMAGE,
                reader=FakeCloudReader(payloads),
            )

    def test_missing_runtime_secret_access_fails_closed(self):
        payloads = copy.deepcopy(passing_payloads())
        payloads["secret_iam_mlai-database-url"] = {"bindings": []}
        with self.assertRaisesRegex(ValueError, "cannot access"):
            run_cloud_preflight(
                self.configuration,
                image_digest=IMAGE,
                reader=FakeCloudReader(payloads),
            )

    def test_mutating_command_is_rejected_before_execution(self):
        reader = GcloudJsonReader(
            "gcloud.cmd",
            account=ACCOUNT,
            configuration="default",
            project=PROJECT,
        )
        with self.assertRaisesRegex(ValueError, "read-only allowlist"):
            reader.read("forbidden", ("run", "deploy", "service"))
        with self.assertRaisesRegex(ValueError, "read-only allowlist"):
            reader.read(
                "nested_forbidden",
                ("iam", "service-accounts", "delete", RUNTIME),
            )

    def test_windows_batch_adapter_preserves_space_path_and_pins_context(self):
        calls = []

        def runner(arguments, **keywords):
            calls.append((arguments, keywords))
            return subprocess.CompletedProcess(
                arguments,
                0,
                stdout=json.dumps({"projectId": PROJECT, "lifecycleState": "ACTIVE"}),
                stderr="",
            )

        reader = GcloudJsonReader(
            r"C:\Program Files\Google\Cloud SDK\gcloud.cmd",
            account=ACCOUNT,
            configuration="default",
            project=PROJECT,
            platform_name="nt",
            runner=runner,
        )
        reader.read("project", ("projects", "describe", PROJECT))
        command, keywords = calls[0]
        self.assertIsInstance(command, str)
        self.assertIn('"C:\\Program Files\\Google\\Cloud SDK\\gcloud.cmd"', command)
        self.assertIn(f"--account={ACCOUNT}", command)
        self.assertIn("--configuration=default", command)
        self.assertIn(f"--project={PROJECT}", command)
        self.assertTrue(keywords["shell"])

    def test_cloud_doctor_uses_same_adapter_and_requires_exact_context(self):
        calls = []

        def runner(arguments, **keywords):
            calls.append(arguments)
            selected = str(arguments)
            payload = (
                [{"account": ACCOUNT, "status": "ACTIVE"}]
                if "auth list" in selected
                else {
                    "name": "default",
                    "properties": {"core": {"account": ACCOUNT, "project": PROJECT}},
                }
            )
            return subprocess.CompletedProcess(
                arguments, 0, stdout=json.dumps(payload), stderr=""
            )

        reader = GcloudJsonReader(
            r"C:\Program Files\Google\Cloud SDK\gcloud.cmd",
            account=ACCOUNT,
            configuration="default",
            project=PROJECT,
            platform_name="nt",
            runner=runner,
        )
        result = reader.doctor()
        self.assertEqual("CLOUD_CLI_DOCTOR_PASSED", result["result"])
        self.assertEqual("windows-gcloud-cmd-v2", result["adapter"])
        self.assertEqual(2, len(calls))
        self.assertFalse(result["cloud_mutation_performed"])

    def test_adapter_rejects_shell_metacharacters_and_owned_flags(self):
        reader = GcloudJsonReader(
            "gcloud.cmd",
            account=ACCOUNT,
            configuration="default",
            project=PROJECT,
        )
        with self.assertRaisesRegex(ValueError, "unsafe"):
            reader.read("project", ("projects", "describe", "project&whoami"))
        with self.assertRaisesRegex(ValueError, "adapter-owned"):
            reader.read("project", ("projects", "describe", PROJECT, "--quiet"))


if __name__ == "__main__":
    unittest.main()
