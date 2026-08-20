import json
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
THREAT_MODEL = "docs/architecture/session-lifecycle-threat-model.md"


class SessionLifecycleGovernanceTests(unittest.TestCase):
    def read(self, relative_path: str) -> str:
        return (ROOT / relative_path).read_text(encoding="utf-8")

    def test_story_manifest_and_governance_identifiers_are_consistent(self):
        manifest = json.loads(self.read("story_packages/MLAI-031.18C.json"))
        self.assertEqual(manifest["schema_version"], 2)
        self.assertEqual(manifest["story_id"], "MLAI-031.18C")
        self.assertEqual(
            manifest["adr"],
            "governance/adrs/"
            "ADR-0051-defense-in-depth-customer-identity-session-and-platform-security.md",
        )
        self.assertEqual(
            len(
                re.findall(
                    r"^### LDR-066\b",
                    self.read("governance/locked-decision-register.md"),
                    re.MULTILINE,
                )
            ),
            1,
        )
        self.assertEqual(
            len(
                re.findall(
                    r"^\| RISK-039 \|",
                    self.read("governance/registers/risk-register.md"),
                    re.MULTILINE,
                )
            ),
            1,
        )
        self.assertEqual(
            len(
                re.findall(
                    r"^\| TD-042 \|",
                    self.read("governance/registers/technical-debt-register.md"),
                    re.MULTILINE,
                )
            ),
            1,
        )

    def test_threat_model_preserves_required_boundaries(self):
        threat_model = self.read(THREAT_MODEL)
        for required in (
            "Identity and provider-token boundary",
            "Opaque server-session boundary",
            "Tenant authorization boundary",
            "15 minutes idle",
            "60 minutes absolute",
            "created_at",
            "expires_at",
            "revoked_at",
            "compare-and-swap",
            "default deny",
            "routing and context only",
            "All parts commit or roll back together",
        ):
            self.assertIn(required, threat_model)

    def test_privacy_contract_forbids_sensitive_lifecycle_evidence(self):
        threat_model = self.read(THREAT_MODEL)
        for prohibited_evidence in (
            "plaintext session IDs",
            "token hashes",
            "CSRF values or hashes",
            "provider credentials",
            "refresh credentials",
        ):
            self.assertIn(prohibited_evidence, threat_model)

    def test_unimplemented_invalidation_is_explicitly_deferred(self):
        combined = "\n".join(
            (
                self.read(THREAT_MODEL),
                self.read("governance/registers/risk-register.md"),
                self.read("governance/registers/technical-debt-register.md"),
            )
        )
        for deferred in (
            "provider-global",
            "cross-tenant",
            "MFA",
            "recovery",
            "security-engine",
        ):
            self.assertIn(deferred, combined)

    def test_story_requires_no_schema_migration_or_parallel_store(self):
        manifest = json.loads(self.read("story_packages/MLAI-031.18C.json"))
        self.assertIn(
            "schema migration or parallel session persistence",
            manifest["out_of_scope"],
        )
        sessions = self.read("app/operations/sessions.py")
        self.assertIn("INSERT INTO pilot_sessions", sessions)
        self.assertNotIn("ALTER TABLE pilot_sessions", sessions)


if __name__ == "__main__":
    unittest.main()
