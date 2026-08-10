import unittest

from deployment.private_synthetic_bootstrap import (
    APPROVED_INGRESS,
    CANONICAL_SERVICE,
    BootstrapObservation,
    RevisionCreationMode,
    ServiceState,
    plan_revision_creation,
    validate_revision_evidence,
)

IMAGE = (
    "africa-south1-docker.pkg.dev/marketinglabai-identity-dev/"
    "mlai-synthetic/marketinglabai-pilot@sha256:" + "a" * 64
)
HASH = "b" * 64


def observation(**changes):
    values = {
        "canonical_service_name": CANONICAL_SERVICE,
        "service_state": ServiceState.ABSENT,
        "cloud_run_baseline_sha256": HASH,
        "immutable_image_digest": IMAGE,
        "ingress": None,
        "public_principal_count": 0,
        "pilot_invoker_grant_count": 0,
    }
    values.update(changes)
    return BootstrapObservation(**values)


def evidence(**changes):
    values = {
        "authorization_id": "AUTH-1",
        "pre_mutation_baseline_sha256": HASH,
        "post_mutation_state_sha256": "c" * 64,
        "created_revision": "marketinglabai-velani-pilot-00001-abc",
        "service_existed_before": "false",
        "creation_mode": "FIRST_PRIVATE_REVISION",
        "image_digest": IMAGE,
        "mutation_count": "1",
        "ingress": APPROVED_INGRESS,
        "public_principals": "0",
        "pilot_invoker_grants": "0",
        "created_revision_traffic_percent": "100",
        "cloud_run_operation_id": "operation-1",
        "configuration_evidence_sha256": "d" * 64,
    }
    values.update(changes)
    return values


class BootstrapPlanningTests(unittest.TestCase):
    def test_absent_service_uses_private_first_revision(self):
        plan = plan_revision_creation(observation())
        self.assertTrue(plan.deployable)
        self.assertEqual(
            RevisionCreationMode.FIRST_PRIVATE_REVISION, plan.creation_mode
        )
        self.assertEqual(100, plan.expected_new_revision_traffic_percent)

    def test_existing_private_service_uses_zero_traffic(self):
        plan = plan_revision_creation(
            observation(
                service_state=ServiceState.EXISTING_PRIVATE,
                ingress=APPROVED_INGRESS,
            )
        )
        self.assertEqual(RevisionCreationMode.ZERO_TRAFFIC_REVISION, plan.creation_mode)
        self.assertEqual(0, plan.expected_new_revision_traffic_percent)

    def test_public_ambiguous_and_public_principal_states_fail_closed(self):
        selected = (
            observation(service_state=ServiceState.EXISTING_PUBLIC),
            observation(service_state=ServiceState.AMBIGUOUS),
            observation(public_principal_count=1),
        )
        for item in selected:
            with self.subTest(item=item):
                self.assertFalse(plan_revision_creation(item).deployable)

    def test_bootstrap_refuses_pilot_grant(self):
        self.assertFalse(
            plan_revision_creation(observation(pilot_invoker_grant_count=1)).deployable
        )

    def test_invalid_image_and_baseline_fail_closed(self):
        self.assertFalse(
            plan_revision_creation(
                observation(immutable_image_digest="tag:latest")
            ).deployable
        )
        self.assertFalse(
            plan_revision_creation(
                observation(cloud_run_baseline_sha256="bad")
            ).deployable
        )

    def test_first_revision_evidence_is_valid(self):
        validate_revision_evidence(evidence())

    def test_existing_revision_requires_zero_traffic(self):
        validate_revision_evidence(
            evidence(
                service_existed_before="true",
                creation_mode="ZERO_TRAFFIC_REVISION",
                created_revision_traffic_percent="0",
            )
        )
        with self.assertRaisesRegex(ValueError, "zero traffic"):
            validate_revision_evidence(
                evidence(
                    service_existed_before="true",
                    creation_mode="ZERO_TRAFFIC_REVISION",
                    created_revision_traffic_percent="100",
                )
            )

    def test_evidence_rejects_missing_fields_and_extra_mutations(self):
        selected = evidence()
        selected.pop("authorization_id")
        with self.assertRaisesRegex(ValueError, "incomplete"):
            validate_revision_evidence(selected)
        with self.assertRaisesRegex(ValueError, "Exactly one"):
            validate_revision_evidence(evidence(mutation_count="2"))

    def test_evidence_rejects_public_or_pilot_bootstrap_access(self):
        with self.assertRaisesRegex(ValueError, "Public"):
            validate_revision_evidence(evidence(public_principals="1"))
        with self.assertRaisesRegex(ValueError, "contradictory"):
            validate_revision_evidence(evidence(pilot_invoker_grants="1"))


if __name__ == "__main__":
    unittest.main()
