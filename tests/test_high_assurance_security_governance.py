import json
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ADR = (
    "governance/adrs/"
    "ADR-0051-defense-in-depth-customer-identity-session-and-platform-security.md"
)


class HighAssuranceSecurityGovernanceTests(unittest.TestCase):
    def read(self, relative_path: str) -> str:
        return (ROOT / relative_path).read_text(encoding="utf-8")

    def test_story_and_identifiers_are_unique_and_consistent(self):
        manifest = json.loads(self.read("story_packages/MLAI-031.18B.json"))
        self.assertEqual(manifest["schema_version"], 2)
        self.assertEqual(manifest["story_id"], "MLAI-031.18B")
        self.assertEqual(manifest["adr"], ADR)

        decision = self.read("governance/locked-decision-register.md")
        risk = self.read("governance/registers/risk-register.md")
        debt = self.read("governance/registers/technical-debt-register.md")
        self.assertEqual(len(re.findall(r"^### LDR-065\b", decision, re.MULTILINE)), 1)
        self.assertEqual(len(re.findall(r"^\| RISK-038 \|", risk, re.MULTILINE)), 1)
        self.assertEqual(len(re.findall(r"^\| TD-041 \|", debt, re.MULTILINE)), 1)

    def test_fourteen_layers_are_explicit(self):
        architecture = self.read("docs/high-assurance-saas-security-architecture.md")
        rows = re.findall(r"^\| (\d{1,2}) \|", architecture, re.MULTILINE)
        self.assertEqual(rows, [str(number) for number in range(1, 15)])

        adr = self.read(ADR)
        headings = re.findall(r"^(\d{1,2})\. \*\*", adr, re.MULTILINE)
        self.assertEqual(headings, [str(number) for number in range(1, 15)])

    def test_existing_architecture_is_preserved(self):
        combined = self.read(ADR) + self.read(
            "docs/high-assurance-saas-security-architecture.md"
        )
        for required in (
            "Google Cloud Identity Platform",
            "provider-neutral",
            "tenant authorization",
            "server session",
            "PostgreSQL",
            "Cloud SQL",
            "Cloud Run",
            "release controller is observational",
        ):
            self.assertIn(required, combined)

    def test_token_session_and_step_up_contract_is_complete(self):
        combined = self.read(ADR) + self.read(
            "docs/high-assurance-saas-security-architecture.md"
        )
        for required in (
            "short-lived",
            "refresh credentials",
            "idle and absolute expiry",
            "rotate",
            "CSRF",
            "replay",
            "revocation",
            "MFA",
            "step-up",
            "recent authentication",
        ):
            self.assertIn(required, combined)

    def test_detection_response_recovery_and_security_ci_are_required(self):
        architecture = self.read("docs/high-assurance-saas-security-architecture.md")
        for required in (
            "secret scanning",
            "SAST",
            "SBOM",
            "cross-tenant",
            "centralized",
            "Incident response",
            "evidence preservation",
            "isolated restore",
            "operationally_evidenced",
        ):
            self.assertIn(required, architecture)

    def test_governance_lock_does_not_claim_implementation_or_authority(self):
        manifest = json.loads(self.read("story_packages/MLAI-031.18B.json"))
        combined = self.read(ADR) + "\n" + "\n".join(manifest["out_of_scope"])
        for prohibited in (
            "no authentication",
            "cloud",
            "IAM",
            "Identity Platform",
            "Secret Manager",
            "database",
            "deployment",
            "release-state",
        ):
            self.assertIn(prohibited, combined)
        normalized = " ".join(self.read(ADR).split())
        self.assertIn("does not justify a claim of perfect security", normalized)


if __name__ == "__main__":
    unittest.main()
