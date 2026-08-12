"""Regression tests for the one-plan release control plane."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from deployment.release_controller import record_gate, start_release
from tests.test_cloud_preflight import FakeCloudReader
from tools.release_control.config import (
    ROOT,
    canonical_dependency_lock_sha256,
    load_config,
    validate_repository,
)
from tools.release_control.control_plane import ReleaseControlPlane
from tools.release_control.store import write_json_atomic

COMMIT = "22392443177c67b7252ae51182b335e7491357f5"
IMAGE = (
    "africa-south1-docker.pkg.dev/marketinglabai-identity-dev/"
    "mlai-synthetic/marketinglabai-pilot@sha256:"
    "2f20534cff7b7ae8e6fdaef6272b8cee793317b3113f88958bd69889e9213486"
)
BUILD_ID = "f9ad9f0d-b93d-429e-9ea9-f89b538ebea8"
EXECUTOR_PROVENANCE = {
    "control_plane_version": "1.3",
    "repository_commit": "b" * 40,
    "executor_contract_sha256": "c" * 64,
    "platform_adapter": "windows-gcloud-cmd-v2",
}
ORIGIN = "https://marketinglabai-velani-pilot-123456.africa-south1.run.app"
BROWSER_API_KEY = "AIza" + "A" * 32
OAUTH_CLIENT_ID = "1234567890-" + "a" * 32 + ".apps.googleusercontent.com"


class ReleaseControlPlaneTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.runs_root = self.root / "observational-runs"
        self.state_root = self.root / "release-control"
        self.run = start_release(
            self.runs_root,
            commit=COMMIT,
            image_digest=IMAGE,
            operator="synthetic-operator",
        )
        for gate in ("SOURCE_VERIFIED", "CI_PASSED", "ARTIFACT_VERIFIED"):
            record_gate(
                self.run,
                gate_id=gate,
                outcome="passed",
                evidence_reference=f"synthetic://{gate.lower()}",
                operator="synthetic-operator",
            )
        self.build_summary = self.root / "controlled-build-summary.json"
        self.build_summary.write_text(
            json.dumps(
                {
                    "result": "CONTROLLED_CLOUD_BUILD_PASSED",
                    "build_id": BUILD_ID,
                    "qualified_digest": IMAGE,
                }
            ),
            encoding="utf-8",
        )
        self.assessment = self.root / "post-build-evidence-assessment.json"
        self.assessment.write_text(
            json.dumps({"result": "POST_BUILD_EVIDENCE_ASSESSMENT_PASSED_READ_ONLY"}),
            encoding="utf-8",
        )
        self.control = ReleaseControlPlane(
            load_config(),
            self.state_root,
            executor_provenance=EXECUTOR_PROVENANCE,
        )

    def tearDown(self):
        self.temporary.cleanup()

    def adopt(self):
        return self.control.adopt(
            run_dir=self.run,
            build_summary_path=self.build_summary,
            post_build_assessment_path=self.assessment,
            operator="synthetic-operator",
        )

    def test_repository_runtime_and_authority_contract_is_pinned(self):
        report = validate_repository(load_config())
        self.assertTrue(report["repository_valid"])
        self.assertTrue(report["python"]["supported"])
        self.assertEqual("shadow", report["policy_mode"])
        self.assertEqual("utf8-sig-lf-v1", report["dependency_lock_hash_mode"])
        self.assertEqual(
            "external-zero-trust-binary-authorization",
            report["authority_separation"]["admission"],
        )

    def test_dependency_lock_hash_is_independent_of_windows_line_endings(self):
        lf_path = self.root / "lf-requirements.txt"
        crlf_path = self.root / "crlf-requirements.txt"
        bom_path = self.root / "bom-requirements.txt"
        lf_path.write_bytes(b"black==26.3.1\nruff==0.15.6\n")
        crlf_path.write_bytes(b"black==26.3.1\r\nruff==0.15.6\r\n")
        bom_path.write_bytes(b"\xef\xbb\xbfblack==26.3.1\r\nruff==0.15.6\r\n")
        expected = canonical_dependency_lock_sha256(lf_path)
        self.assertEqual(expected, canonical_dependency_lock_sha256(crlf_path))
        self.assertEqual(expected, canonical_dependency_lock_sha256(bom_path))

    def test_adoption_is_idempotent_and_does_not_authorize_deployment(self):
        first = self.adopt()
        second = self.adopt()
        self.assertEqual(first, second)
        self.assertFalse(first["controller_authoritative"])
        self.assertFalse(first["deployment_authorized"])
        self.assertEqual(BUILD_ID, first["release"]["build_id"])
        self.assertEqual(
            "CONFIGURATION_VALIDATED", self.control.status()["next_eligible_gate"]
        )

    def test_plan_is_deterministic_and_approval_is_bound_to_it(self):
        self.adopt()
        first = self.control.plan()
        second = self.control.plan()
        self.assertEqual(first, second)
        self.assertEqual("CONFIGURATION_VALIDATED", first["gate"])
        self.assertFalse(first["may_mutate_cloud"])
        self.assertEqual(EXECUTOR_PROVENANCE, first["executor_provenance"])
        approval = self.control.approve(
            plan_digest=first["plan_digest"],
            operator="synthetic-approver",
            authorization_reference="AUTH-SYNTHETIC-CONFIGURATION",
        )
        self.assertEqual(first["plan_digest"], approval["plan_digest"])
        self.assertFalse(approval["admission_authority"])

    def test_apply_and_resume_are_idempotent(self):
        self.adopt()
        plan = self.control.plan()
        self.control.approve(
            plan_digest=plan["plan_digest"],
            operator="synthetic-approver",
            authorization_reference="AUTH-SYNTHETIC-CONFIGURATION",
        )
        first = self.control.apply(plan_digest=plan["plan_digest"])
        second = self.control.apply(plan_digest=plan["plan_digest"])
        resumed = self.control.resume()
        self.assertEqual(first, second)
        self.assertEqual("awaiting_approval", resumed["state"])
        self.assertEqual("CLOUD_PREFLIGHT_PASSED", resumed["next_eligible_gate"])
        self.assertEqual("completed", first["status"])
        self.assertEqual("CLOUD_PREFLIGHT_PASSED", first["next_eligible_gate"])
        self.assertFalse(first["cloud_mutation_performed"])

    def test_cloud_preflight_apply_and_resume_are_idempotent(self):
        self.control.cloud_reader = FakeCloudReader(image_digest=IMAGE)
        self.adopt()
        configuration_plan = self.control.plan()
        self.control.approve(
            plan_digest=configuration_plan["plan_digest"],
            operator="synthetic-approver",
            authorization_reference="AUTH-SYNTHETIC-CONFIGURATION",
        )
        self.control.apply(plan_digest=configuration_plan["plan_digest"])
        preflight_plan = self.control.plan()
        self.assertEqual("CLOUD_PREFLIGHT_PASSED", preflight_plan["gate"])
        self.assertFalse(preflight_plan["may_mutate_cloud"])
        self.control.approve(
            plan_digest=preflight_plan["plan_digest"],
            operator="synthetic-approver",
            authorization_reference="AUTH-SYNTHETIC-CLOUD-PREFLIGHT",
        )
        first = self.control.apply(plan_digest=preflight_plan["plan_digest"])
        second = self.control.apply(plan_digest=preflight_plan["plan_digest"])
        resumed = self.control.resume()
        self.assertEqual(first, second)
        self.assertEqual(first, resumed)
        self.assertEqual("REVISION_CREATED", first["next_eligible_gate"])
        self.assertFalse(first["cloud_mutation_performed"])
        audit = self.control.status(audit=True)["audit"]
        indexed_kinds = {record["kind"] for record in audit["evidence_records"]}
        self.assertIn("gate_evidence:CONFIGURATION_VALIDATED", indexed_kinds)
        self.assertIn("gate_evidence:CLOUD_PREFLIGHT_PASSED", indexed_kinds)
        self.assertTrue(self.control.verify()["indexed_evidence_valid"])

    def test_revision_preparation_is_manifest_bound_without_cloud_mutation(self):
        self.control.cloud_reader = FakeCloudReader(image_digest=IMAGE)
        self.adopt()
        configuration_plan = self.control.plan()
        self.control.approve(
            plan_digest=configuration_plan["plan_digest"],
            operator="synthetic-approver",
            authorization_reference="AUTH-SYNTHETIC-CONFIGURATION",
        )
        self.control.apply(plan_digest=configuration_plan["plan_digest"])
        preflight_plan = self.control.plan()
        self.control.approve(
            plan_digest=preflight_plan["plan_digest"],
            operator="synthetic-approver",
            authorization_reference="AUTH-SYNTHETIC-CLOUD-PREFLIGHT",
        )
        self.control.apply(plan_digest=preflight_plan["plan_digest"])
        prepared = self.control.prepare_revision(
            output_root=self.root / "revision-output",
            origin=ORIGIN,
            browser_api_key=BROWSER_API_KEY,
            oauth_client_id=OAUTH_CLIENT_ID,
        )
        self.assertEqual("REVISION_CREATION_PREPARED", prepared["result"])
        self.assertEqual("REVISION_CREATED", prepared["gate"])
        self.assertEqual("FIRST_PRIVATE_REVISION", prepared["expected_creation_mode"])
        self.assertEqual(100, prepared["expected_new_revision_traffic_percent"])
        self.assertFalse(prepared["cloud_cli_executed"])
        self.assertFalse(prepared["cloud_mutation_performed"])
        self.assertFalse(prepared["deployment_authorized"])
        self.assertFalse(prepared["traffic_routing_authorized"])
        self.assertTrue(Path(str(prepared["manifest_path"])).is_file())
        self.assertTrue(Path(str(prepared["revision_plan_path"])).is_file())
        manifest = Path(str(prepared["manifest_path"])).read_text(encoding="utf-8")
        self.assertIn(IMAGE, manifest)
        self.assertIn("internal-and-cloud-load-balancing", manifest)

    def test_revision_preparation_refuses_repository_output(self):
        self.control.cloud_reader = FakeCloudReader(image_digest=IMAGE)
        self.adopt()
        configuration_plan = self.control.plan()
        self.control.approve(
            plan_digest=configuration_plan["plan_digest"],
            operator="synthetic-approver",
            authorization_reference="AUTH-SYNTHETIC-CONFIGURATION",
        )
        self.control.apply(plan_digest=configuration_plan["plan_digest"])
        preflight_plan = self.control.plan()
        self.control.approve(
            plan_digest=preflight_plan["plan_digest"],
            operator="synthetic-approver",
            authorization_reference="AUTH-SYNTHETIC-CLOUD-PREFLIGHT",
        )
        self.control.apply(plan_digest=preflight_plan["plan_digest"])
        with self.assertRaisesRegex(ValueError, "outside the repository"):
            self.control.prepare_revision(
                output_root=ROOT / "tmp-revision-output",
                origin=ORIGIN,
                browser_api_key=BROWSER_API_KEY,
                oauth_client_id=OAUTH_CLIENT_ID,
            )

    def test_resume_waits_for_one_approval(self):
        self.adopt()
        result = self.control.resume()
        self.assertEqual("awaiting_approval", result["state"])
        self.assertEqual(64, len(result["plan_digest"]))

    def test_indexed_evidence_modification_is_detected(self):
        self.adopt()
        self.build_summary.write_text("{}", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "evidence"):
            self.control.verify()

    def test_state_inside_repository_is_refused(self):
        with self.assertRaisesRegex(ValueError, "outside the repository"):
            ReleaseControlPlane(load_config(), ROOT / "release-control")

    def test_cloud_doctor_is_same_reader_and_does_not_modify_release_state(self):
        reader = FakeCloudReader(image_digest=IMAGE)
        self.control.cloud_reader = reader
        result = self.control.doctor_cloud()
        self.assertEqual("CLOUD_CLI_DOCTOR_PASSED", result["result"])
        self.assertEqual(EXECUTOR_PROVENANCE, result["executor_provenance"])
        self.assertFalse(result["release_state_modified"])
        self.assertFalse(self.state_root.exists())

    def test_failed_cloud_doctor_does_not_create_operation_journal(self):
        class FailingDoctorReader(FakeCloudReader):
            def doctor(self):
                raise ValueError("synthetic adapter failure")

        self.control.cloud_reader = FailingDoctorReader(image_digest=IMAGE)
        self.adopt()
        configuration_plan = self.control.plan()
        self.control.approve(
            plan_digest=configuration_plan["plan_digest"],
            operator="synthetic-approver",
            authorization_reference="AUTH-SYNTHETIC-CONFIGURATION",
        )
        self.control.apply(plan_digest=configuration_plan["plan_digest"])
        preflight_plan = self.control.plan()
        self.control.approve(
            plan_digest=preflight_plan["plan_digest"],
            operator="synthetic-approver",
            authorization_reference="AUTH-SYNTHETIC-CLOUD-PREFLIGHT",
        )
        with self.assertRaisesRegex(ValueError, "synthetic adapter failure"):
            self.control.apply(plan_digest=preflight_plan["plan_digest"])
        operation = (
            self.state_root / "operations" / f"{preflight_plan['plan_digest']}.json"
        )
        self.assertFalse(operation.exists())

    def test_executor_change_requires_formal_supersession_and_new_plan(self):
        self.adopt()
        plan = self.control.plan()
        approval = self.control.approve(
            plan_digest=plan["plan_digest"],
            operator="synthetic-approver",
            authorization_reference="AUTH-SYNTHETIC-CONFIGURATION",
        )
        operation_path = self.state_root / "operations" / f"{plan['plan_digest']}.json"
        write_json_atomic(
            operation_path,
            {
                "schema_version": 1,
                "plan_digest": plan["plan_digest"],
                "approval_digest": approval["approval_digest"],
                "gate": plan["gate"],
                "status": "running",
                "started_at": "2026-08-12T21:26:16+00:00",
                "cloud_mutation_performed": False,
            },
        )
        replacement_provenance = {
            **EXECUTOR_PROVENANCE,
            "executor_contract_sha256": "d" * 64,
        }
        repaired = ReleaseControlPlane(
            load_config(),
            self.state_root,
            executor_provenance=replacement_provenance,
        )
        with self.assertRaisesRegex(ValueError, "formally superseded"):
            repaired.apply(plan_digest=plan["plan_digest"])
        closed = repaired.supersede_operation(
            plan_digest=plan["plan_digest"],
            operator="synthetic-operator",
            reason="Windows Cloud SDK adapter contract was replaced.",
            authorization_reference="AUTH-SYNTHETIC-SUPERSEDE",
        )
        self.assertEqual("superseded", closed["status"])
        self.assertFalse(closed["release_gate_modified"])
        self.assertFalse(closed["cloud_mutation_performed"])
        resumed = repaired.resume()
        self.assertEqual("awaiting_approval", resumed["state"])
        self.assertNotEqual(plan["plan_digest"], resumed["plan_digest"])

    def test_story_numbered_state_path_is_absent_from_configuration(self):
        text = (ROOT / "tools" / "release_control_plane.json").read_text(
            encoding="utf-8"
        )
        self.assertNotRegex(text, r"MLAI-\d+")
        self.assertIn("MarketingLabAI\\\\release-control", text)

    def test_legacy_operator_script_has_no_orchestration(self):
        legacy = (ROOT / "scripts" / "release_private_synthetic.ps1").read_text(
            encoding="utf-8-sig"
        )
        self.assertIn("legacy observational-controller interface is retired", legacy)
        self.assertNotIn("deployment.release_controller", legacy)
        self.assertNotIn("MLAI-031.3_release_runs", legacy)

    def test_powershell_launcher_is_thin_and_uses_join_path(self):
        launcher = (ROOT / "scripts" / "mlai_release.ps1").read_text(
            encoding="utf-8-sig"
        )
        self.assertIn("Join-Path $ProjectRoot", launcher)
        self.assertIn("-m tools.release_control", launcher)
        self.assertNotIn("ConvertFrom-Json", launcher)
        self.assertNotIn("gcloud", launcher)

    def test_control_plane_is_not_packaged_into_the_application_image(self):
        dockerfile = (ROOT / "Dockerfile").read_text(encoding="utf-8-sig")
        dockerignore = (ROOT / ".dockerignore").read_text(encoding="utf-8-sig")
        self.assertNotIn("COPY tools", dockerfile)
        self.assertRegex(dockerignore, r"(?m)^tools$")


if __name__ == "__main__":
    unittest.main()
