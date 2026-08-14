from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from tools.release_control.executor_identity import (
    EXPECTED_EXECUTOR,
    EXPECTED_OPERATOR,
    EXPECTED_PROJECT,
    ExecutorIdentityConfig,
    ReadOnlyExecutorIdentityInspector,
    prepare_identity_bootstrap_plan,
    write_identity_bootstrap_plan,
)


def _configuration() -> dict[str, object]:
    return {
        "cloud_cli": {
            "account": EXPECTED_OPERATOR,
            "configuration": "default",
            "project": EXPECTED_PROJECT,
            "executable_environment_variable": "MLAI_GCLOUD_EXECUTABLE",
            "platform_adapter": "windows-gcloud-cmd-v2",
            "auth_execution": {
                "phase": "local-operator-auth-service-account-impersonation",
                "release_executor_service_account": EXPECTED_EXECUTOR,
                "service_account_key_files_allowed": False,
                "phase_2": "ci-cd-workload-identity",
            },
        }
    }


def _inspection(**overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "schema_version": 1,
        "kind": "release-executor-identity-inspection",
        "result": "RELEASE_EXECUTOR_IDENTITY_INSPECTION_COMPLETED",
        "operator_account": EXPECTED_OPERATOR,
        "project": EXPECTED_PROJECT,
        "executor_service_account": EXPECTED_EXECUTOR,
        "service_account_exists": False,
        "operator_token_creator_binding_present": False,
        "user_managed_key_count": 0,
        "cloud_mutation_performed": False,
        "iam_mutation_performed": False,
        "service_account_created": False,
        "service_account_key_created": False,
        "release_state_modified": False,
    }
    payload.update(overrides)
    return payload


class Completed:
    def __init__(self, stdout: str = "", stderr: str = "", returncode: int = 0):
        self.stdout = stdout
        self.stderr = stderr
        self.returncode = returncode


class ReleaseExecutorIdentityTests(unittest.TestCase):
    def _inspector(self, runner: object) -> ReadOnlyExecutorIdentityInspector:
        config = ExecutorIdentityConfig.from_payload(_configuration())
        temporary = tempfile.NamedTemporaryFile(suffix="gcloud.cmd", delete=False)
        temporary.close()
        self.addCleanup(Path(temporary.name).unlink, missing_ok=True)
        return ReadOnlyExecutorIdentityInspector(
            config,
            executable=temporary.name,
            runner=runner,  # type: ignore[arg-type]
        )

    def test_configuration_pins_operator_project_executor_and_no_keys(self) -> None:
        config = ExecutorIdentityConfig.from_payload(_configuration())
        self.assertEqual(EXPECTED_OPERATOR, config.operator_account)
        self.assertEqual(EXPECTED_PROJECT, config.project)
        self.assertEqual(EXPECTED_EXECUTOR, config.executor_service_account)
        self.assertFalse(config.service_account_key_files_allowed)

    def test_inspection_allowlist_rejects_mutation_and_impersonation(self) -> None:
        inspector = self._inspector(lambda *args, **kwargs: Completed("{}"))
        with self.assertRaisesRegex(ValueError, "not read-only"):
            inspector._command(("iam", "service-accounts", "create", "unsafe"))
        with self.assertRaisesRegex(ValueError, "may not impersonate"):
            inspector._command(
                (
                    "projects",
                    "describe",
                    EXPECTED_PROJECT,
                    f"--impersonate-service-account={EXPECTED_EXECUTOR}",
                )
            )

    def test_missing_service_account_is_valid_discovery_evidence(self) -> None:
        calls: list[str] = []

        def runner(*args: object, **kwargs: object) -> Completed:
            command = str(args[0])
            calls.append(command)
            if "auth list" in command:
                return Completed(
                    json.dumps([{"account": EXPECTED_OPERATOR, "status": "ACTIVE"}])
                )
            if "projects describe" in command:
                return Completed(json.dumps({"projectId": EXPECTED_PROJECT}))
            if "service-accounts describe" in command:
                return Completed(stderr="ERROR: NOT_FOUND", returncode=1)
            if "projects get-iam-policy" in command:
                return Completed(json.dumps({"bindings": []}))
            raise AssertionError(command)

        inspection = self._inspector(runner).inspect()
        self.assertFalse(inspection["service_account_exists"])
        self.assertFalse(inspection["operator_token_creator_binding_present"])
        self.assertEqual(0, inspection["user_managed_key_count"])
        self.assertFalse(inspection["cloud_mutation_performed"])
        self.assertEqual(4, len(calls))

    def test_existing_identity_reports_binding_keys_and_project_roles(self) -> None:
        member = f"user:{EXPECTED_OPERATOR}"
        executor_member = f"serviceAccount:{EXPECTED_EXECUTOR}"

        def runner(*args: object, **kwargs: object) -> Completed:
            command = str(args[0])
            if "auth list" in command:
                return Completed(
                    json.dumps([{"account": EXPECTED_OPERATOR, "status": "ACTIVE"}])
                )
            if "projects describe" in command:
                return Completed(json.dumps({"projectId": EXPECTED_PROJECT}))
            if "service-accounts describe" in command:
                return Completed(json.dumps({"email": EXPECTED_EXECUTOR}))
            if "service-accounts get-iam-policy" in command:
                return Completed(
                    json.dumps(
                        {
                            "bindings": [
                                {
                                    "role": "roles/iam.serviceAccountTokenCreator",
                                    "members": [member],
                                }
                            ]
                        }
                    )
                )
            if "service-accounts keys list" in command:
                return Completed("[]")
            if "projects get-iam-policy" in command:
                return Completed(
                    json.dumps(
                        {
                            "bindings": [
                                {"role": "roles/viewer", "members": [executor_member]}
                            ]
                        }
                    )
                )
            raise AssertionError(command)

        inspection = self._inspector(runner).inspect()
        self.assertTrue(inspection["service_account_exists"])
        self.assertTrue(inspection["operator_token_creator_binding_present"])
        self.assertEqual(["roles/viewer"], inspection["executor_project_roles"])

    def test_reauthentication_failure_is_classified_without_retry(self) -> None:
        def runner(*args: object, **kwargs: object) -> Completed:
            return Completed(
                stderr=(
                    "Reauthentication failed. cannot prompt during non-interactive "
                    "execution."
                ),
                returncode=1,
            )

        with self.assertRaisesRegex(ValueError, "reauthentication is required"):
            self._inspector(runner).inspect()

    def test_missing_identity_produces_exactly_two_ordered_mutations(self) -> None:
        first = prepare_identity_bootstrap_plan(
            _inspection(),
            inspection_sha256="a" * 64,
            repository_commit="b" * 40,
        )
        second = prepare_identity_bootstrap_plan(
            _inspection(),
            inspection_sha256="a" * 64,
            repository_commit="b" * 40,
        )
        self.assertEqual(first, second)
        self.assertEqual(2, first["maximum_iam_mutation_count"])
        actions = first["actions"]
        self.assertIsInstance(actions, list)
        self.assertEqual(
            "create_release_executor_service_account", actions[0]["action"]
        )
        self.assertEqual(
            "grant_operator_token_creator_on_release_executor",
            actions[1]["action"],
        )
        self.assertFalse(first["execution_permission_grants_included"])
        self.assertFalse(first["cloud_cli_executed_during_planning"])

    def test_existing_identity_and_binding_produce_no_mutation_plan(self) -> None:
        plan = prepare_identity_bootstrap_plan(
            _inspection(
                service_account_exists=True,
                operator_token_creator_binding_present=True,
            ),
            inspection_sha256="a" * 64,
            repository_commit="b" * 40,
        )
        self.assertEqual("already_bootstrapped", plan["status"])
        self.assertFalse(plan["approval_required"])
        self.assertEqual([], plan["actions"])

    def test_user_managed_keys_block_planning(self) -> None:
        with self.assertRaisesRegex(ValueError, "user-managed key files"):
            prepare_identity_bootstrap_plan(
                _inspection(user_managed_key_count=1),
                inspection_sha256="a" * 64,
                repository_commit="b" * 40,
            )

    def test_plan_digest_is_verified_before_write(self) -> None:
        plan = prepare_identity_bootstrap_plan(
            _inspection(),
            inspection_sha256="a" * 64,
            repository_commit="b" * 40,
        )
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "plan.json"
            digest = write_identity_bootstrap_plan(path, plan)
            self.assertEqual(64, len(digest))
            tampered = dict(plan)
            tampered["project"] = "wrong-project"
            with self.assertRaisesRegex(ValueError, "digest is invalid"):
                write_identity_bootstrap_plan(path, tampered)


if __name__ == "__main__":
    unittest.main()
