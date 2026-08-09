import copy
import hashlib
import unittest

from deployment.zero_trust_supply_chain import (
    GATE_PREDICATE,
    IN_TOTO_STATEMENT,
    ReleaseIdentity,
    evaluate_shadow_release,
    load_policy,
)


class ZeroTrustSupplyChainTests(unittest.TestCase):
    def setUp(self):
        self.policy = load_policy()
        self.identity = ReleaseIdentity(
            run_id="run-20260809T133656Z-aab7d2be",
            git_commit="7e45958f4f99c5afa76ef3d4e9b7ba6cc87f4f62",
            image_digest=(
                "africa-south1-docker.pkg.dev/marketinglabai-identity-dev/"
                "mlai-synthetic/marketinglabai-pilot@sha256:" + "a" * 64
            ),
            environment="cloud-synthetic",
        )

    def statement(self, gate_id):
        digest = self.identity.image_digest.rsplit(":", 1)[1]
        return {
            "_type": IN_TOTO_STATEMENT,
            "subject": [{"name": "marketinglabai-pilot", "digest": {"sha256": digest}}],
            "predicateType": GATE_PREDICATE,
            "predicate": {
                "runId": self.identity.run_id,
                "gitCommit": self.identity.git_commit,
                "imageDigest": self.identity.image_digest,
                "environment": self.identity.environment,
                "gateId": gate_id,
                "outcome": "passed",
                "policyBundleDigest": "sha256:" + "b" * 64,
            },
        }

    def verification(self, statement):
        envelope = hashlib.sha256(repr(statement).encode()).hexdigest()
        return {
            "dsse_signature_verified": True,
            "rfc3161_timestamp_verified": True,
            "subject_digest_verified": True,
            "signer_identity_verified": True,
            "signed_envelope_sha256": envelope,
            "rfc3161_message_imprint_sha256": envelope,
        }

    def complete_evidence(self):
        statements = [self.statement(gate) for gate in self.policy["required_gates"]]
        return statements, [self.verification(item) for item in statements]

    def test_complete_evidence_is_still_shadow_only(self):
        statements, verifications = self.complete_evidence()
        result = evaluate_shadow_release(
            identity=self.identity,
            attestations=statements,
            verifications=verifications,
        )
        self.assertTrue(result["evidence_complete"])
        self.assertFalse(result["release_authorization_issued"])
        self.assertFalse(result["deployment_authorized"])

    def test_missing_gate_is_visible_and_never_authorizes(self):
        statements, verifications = self.complete_evidence()
        result = evaluate_shadow_release(
            identity=self.identity,
            attestations=statements[:-1],
            verifications=verifications[:-1],
        )
        self.assertFalse(result["evidence_complete"])
        self.assertEqual(result["missing_gates"], ["SMOKE_TESTS_PASSED"])
        self.assertFalse(result["deployment_authorized"])

    def test_commit_or_image_mismatch_is_rejected(self):
        statements, verifications = self.complete_evidence()
        statements[0] = copy.deepcopy(statements[0])
        statements[0]["predicate"]["gitCommit"] = "0" * 40
        with self.assertRaisesRegex(ValueError, "mismatched gitCommit"):
            evaluate_shadow_release(
                identity=self.identity,
                attestations=statements,
                verifications=verifications,
            )

    def test_timestamp_must_cover_exact_signed_envelope(self):
        statements, verifications = self.complete_evidence()
        verifications[0] = dict(verifications[0])
        verifications[0]["rfc3161_message_imprint_sha256"] = "0" * 64
        with self.assertRaisesRegex(ValueError, "does not cover"):
            evaluate_shadow_release(
                identity=self.identity,
                attestations=statements,
                verifications=verifications,
            )

    def test_legacy_controller_authority_is_disabled(self):
        legacy = self.policy["legacy"]
        self.assertFalse(legacy["controller_state_authoritative"])
        self.assertFalse(legacy["backfill_may_authorize_deployment"])
        self.assertFalse(legacy["historical_runs_deployable"])


if __name__ == "__main__":
    unittest.main()
