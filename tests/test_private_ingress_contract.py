import unittest
from pathlib import Path

from deployment.private_synthetic_bootstrap import (
    APPROVED_INGRESS,
    CANONICAL_SERVICE,
    BootstrapObservation,
    RevisionCreationMode,
    ServiceState,
    plan_revision_creation,
)
from deployment.private_synthetic_manifest import validate_template

ROOT = Path(__file__).resolve().parents[1]
TEMPLATE = ROOT / "deployment" / "cloud-run.private-synthetic.yaml.template"
INGRESS_PREFIX = "run.googleapis.com/ingress:"


class PrivateIngressContractTests(unittest.TestCase):
    def setUp(self):
        self.template = TEMPLATE.read_text(encoding="utf-8")
        self.canonical_line = f"{INGRESS_PREFIX} {APPROVED_INGRESS}"

    def test_committed_template_uses_one_approved_ingress(self):
        report = validate_template(self.template)
        self.assertTrue(report["template_valid"])
        self.assertEqual(self.template.count(self.canonical_line), 1)
        self.assertEqual(report["ingress"], APPROVED_INGRESS)

    def test_public_ingress_is_rejected(self):
        changed = self.template.replace(APPROVED_INGRESS, "all")
        with self.assertRaisesRegex(ValueError, "ingress"):
            validate_template(changed)

    def test_internal_only_ingress_is_rejected(self):
        changed = self.template.replace(APPROVED_INGRESS, "internal")
        with self.assertRaisesRegex(ValueError, "ingress"):
            validate_template(changed)

    def test_missing_ingress_is_rejected(self):
        changed = self.template.replace(f"    {self.canonical_line}\n", "")
        with self.assertRaisesRegex(ValueError, "ingress"):
            validate_template(changed)

    def test_duplicate_ingress_is_rejected(self):
        changed = self.template.replace(
            f"    {self.canonical_line}\n",
            f"    {self.canonical_line}\n    {self.canonical_line}\n",
        )
        with self.assertRaisesRegex(ValueError, "ingress"):
            validate_template(changed)

    def test_malformed_ingress_is_rejected(self):
        changed = self.template.replace(
            APPROVED_INGRESS, "internal_and_cloud_load_balancing"
        )
        with self.assertRaisesRegex(ValueError, "ingress"):
            validate_template(changed)

    def test_manifest_and_first_service_planner_share_ingress_authority(self):
        observation = BootstrapObservation(
            canonical_service_name=CANONICAL_SERVICE,
            service_state=ServiceState.ABSENT,
            cloud_run_baseline_sha256="a" * 64,
            immutable_image_digest=(
                "africa-south1-docker.pkg.dev/marketinglabai-identity-dev/"
                "mlai-synthetic/marketinglabai-pilot@sha256:" + "b" * 64
            ),
            ingress=None,
            public_principal_count=0,
            pilot_invoker_grant_count=0,
        )
        plan = plan_revision_creation(observation)
        report = validate_template(self.template)
        self.assertEqual(
            plan.creation_mode, RevisionCreationMode.FIRST_PRIVATE_REVISION
        )
        self.assertTrue(plan.deployable)
        self.assertEqual(plan.required_ingress, APPROVED_INGRESS)
        self.assertEqual(report["ingress"], plan.required_ingress)


if __name__ == "__main__":
    unittest.main()
