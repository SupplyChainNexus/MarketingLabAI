"""Regression tests for dependency-aware private synthetic release automation."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from deployment.release_controller import (
    EVENTS_FILE,
    gate_status,
    load_catalog,
    record_gate,
    release_summary,
    start_release,
    verify_run,
)

COMMIT = "5bd8e9d5e043b5a87782a2a62dac0ef70d0a92e6"
IMAGE = (
    "africa-south1-docker.pkg.dev/marketinglabai-identity-dev/"
    "mlai-synthetic/marketinglabai-pilot@sha256:"
    "660f8aeb11b1e572e4e37a1db2d835c01b168f98ef2ae91339116d60f64636ba"
)
REVISION_EVIDENCE = ";".join(
    (
        "authorization_id=AUTH-TEST",
        "pre_mutation_baseline_sha256=" + "a" * 64,
        "post_mutation_state_sha256=" + "b" * 64,
        "created_revision=marketinglabai-velani-pilot-00001-abc",
        "service_existed_before=false",
        "creation_mode=FIRST_PRIVATE_REVISION",
        "image_digest=" + IMAGE,
        "mutation_count=1",
        "ingress=internal-and-cloud-load-balancing",
        "public_principals=0",
        "pilot_invoker_grants=0",
        "created_revision_traffic_percent=100",
        "cloud_run_operation_id=operation-1",
        "configuration_evidence_sha256=" + "c" * 64,
    )
)


class ReleaseControllerTests(unittest.TestCase):
    def start(self, root: str) -> Path:
        return start_release(
            Path(root),
            commit=COMMIT,
            image_digest=IMAGE,
            operator="synthetic-test-operator",
        )

    def pass_gate(self, run: Path, gate_id: str) -> None:
        record_gate(
            run,
            gate_id=gate_id,
            outcome="passed",
            evidence_reference=f"synthetic://{gate_id.lower()}",
            operator="synthetic-test-operator",
        )

    def test_catalog_is_ordered_and_separates_checks_from_phases(self):
        gates = load_catalog()
        self.assertEqual("SOURCE_VERIFIED", gates[0].id)
        self.assertEqual("RELEASE_CLOSED", gates[-1].id)
        known = set()
        for gate in gates:
            self.assertTrue(set(gate.depends_on).issubset(known), gate.id)
            known.add(gate.id)
        mutation_gates = {gate.id for gate in gates if gate.may_mutate_cloud}
        self.assertEqual({"REVISION_CREATED", "PRIVATE_TRAFFIC_ROUTED"}, mutation_gates)

    def test_start_creates_unique_external_runs_with_frozen_boundaries(self):
        with tempfile.TemporaryDirectory() as directory:
            first = self.start(directory)
            second = self.start(directory)
            self.assertNotEqual(first, second)
            for run in (first, second):
                metadata = verify_run(run)
                self.assertEqual(COMMIT, metadata["commit"])
                self.assertEqual(IMAGE, metadata["image_digest"])
                self.assertFalse(metadata["public_access_authorized"])
                self.assertFalse(metadata["real_customer_data_authorized"])

    def test_gate_cannot_run_before_its_dependencies(self):
        with tempfile.TemporaryDirectory() as directory:
            run = self.start(directory)
            with self.assertRaisesRegex(ValueError, "blocked by prerequisites"):
                self.pass_gate(run, "CONFIGURATION_VALIDATED")
            self.pass_gate(run, "SOURCE_VERIFIED")
            self.assertEqual("passed", gate_status(run)["SOURCE_VERIFIED"])
            self.assertEqual("pending", gate_status(run)["CI_PASSED"])

    def test_failed_gate_requires_complete_operator_guidance(self):
        with tempfile.TemporaryDirectory() as directory:
            run = self.start(directory)
            with self.assertRaisesRegex(ValueError, "require classification"):
                record_gate(
                    run,
                    gate_id="SOURCE_VERIFIED",
                    outcome="failed",
                    evidence_reference="synthetic://failure",
                    operator="synthetic-test-operator",
                )
            record_gate(
                run,
                gate_id="SOURCE_VERIFIED",
                outcome="failed",
                evidence_reference="synthetic://failure",
                operator="synthetic-test-operator",
                failure_classification="repository baseline mismatch",
                remediation="synchronize and create a new release run",
                safe_next_action="do not continue this failed run",
            )
            summary = release_summary(run)
            self.assertEqual(["SOURCE_VERIFIED"], summary["failed_gates"])
            self.assertEqual([], summary["eligible_gates"])

    def test_non_mutating_gate_cannot_claim_cloud_mutation(self):
        with tempfile.TemporaryDirectory() as directory:
            run = self.start(directory)
            with self.assertRaisesRegex(ValueError, "may not record"):
                record_gate(
                    run,
                    gate_id="SOURCE_VERIFIED",
                    outcome="passed",
                    evidence_reference="synthetic://source",
                    operator="synthetic-test-operator",
                    mutation_performed=True,
                    authorization_reference="synthetic authorization",
                )

    def test_mutation_gate_requires_dependencies_and_authorization(self):
        with tempfile.TemporaryDirectory() as directory:
            run = self.start(directory)
            for gate in (
                "SOURCE_VERIFIED",
                "CI_PASSED",
                "ARTIFACT_VERIFIED",
                "CONFIGURATION_VALIDATED",
                "CLOUD_PREFLIGHT_PASSED",
            ):
                self.pass_gate(run, gate)
            with self.assertRaisesRegex(ValueError, "authorization reference"):
                record_gate(
                    run,
                    gate_id="REVISION_CREATED",
                    outcome="passed",
                    evidence_reference=REVISION_EVIDENCE,
                    operator="synthetic-test-operator",
                    mutation_performed=True,
                )
            record_gate(
                run,
                gate_id="REVISION_CREATED",
                outcome="passed",
                evidence_reference=REVISION_EVIDENCE,
                operator="synthetic-test-operator",
                mutation_performed=True,
                authorization_reference="founder-approved synthetic revision",
            )
            self.assertEqual("passed", gate_status(run)["REVISION_CREATED"])

    def test_event_ledger_detects_modification(self):
        with tempfile.TemporaryDirectory() as directory:
            run = self.start(directory)
            self.pass_gate(run, "SOURCE_VERIFIED")
            ledger = run / EVENTS_FILE
            event = json.loads(ledger.read_text(encoding="utf-8"))
            event["evidence_reference"] = "synthetic://modified"
            ledger.write_text(json.dumps(event) + "\n", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "modified"):
                verify_run(run)

    def test_run_root_inside_repository_is_refused(self):
        repository_root = Path(__file__).resolve().parents[1]
        with self.assertRaisesRegex(ValueError, "outside the repository"):
            self.start(str(repository_root / "release-runs"))


if __name__ == "__main__":
    unittest.main()
