import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class QualityGovernanceTests(unittest.TestCase):
    def read(self, relative_path: str) -> str:
        return (ROOT / relative_path).read_text(encoding="utf-8-sig")

    def test_quality_mandate_preserves_authority_and_reservations(self):
        decision = self.read(
            "governance/adrs/ADR-0023-constitution-preserving-quality-mandate.md"
        )

        for required in (
            "necessary adjacent paths",
            "never be weakened merely to obtain a passing result",
            "real customer data",
            "paid services",
            "destructive migrations",
            "Product Constitution",
        ):
            self.assertIn(required, decision)

    def test_integrity_protocol_uses_evidence_backed_expected_scope(self):
        protocol = self.read("governance/repository-integrity-protocol.md")

        self.assertIn("expected-path allowlist", protocol)
        self.assertIn("classify every failure", protocol)
        self.assertIn("necessary adjacent", protocol)
        self.assertIn("local/remote commit equality", protocol)

    def test_audit_separates_damage_from_intentional_constraints(self):
        audit = self.read("governance/audits/2026-08-06-governance-drag-audit.md")

        for classification in (
            "Confirmed damage",
            "Probable governance drag",
            "Intentional constraint",
            "No evidence of damage",
        ):
            self.assertIn(classification, audit)

        self.assertIn("not evidence of broad", audit)
        self.assertIn("No real-data activation", audit)

    def test_definition_of_done_covers_product_experience_quality(self):
        done = self.read("governance/definition-of-done.md")
        gates = self.read("governance/quality-gates.md")

        for quality in (
            "usability",
            "accessibility",
            "browser-journey",
            "failure-recovery",
        ):
            self.assertIn(quality, done)
            self.assertIn(quality, gates)

    def test_development_unfreeze_preserves_real_data_boundary(self):
        decision = self.read(
            "governance/adrs/ADR-0024-controlled-pilot-development-unfreeze.md"
        )

        self.assertIn("Engineering and quality development — authorized", decision)
        self.assertIn(
            "Controlled synthetic design-partner rehearsal — authorized", decision
        )
        self.assertIn("Real-customer activation — frozen", decision)
        self.assertIn("real_data_activation_frozen", decision)
        self.assertIn("external design-partner invitations", decision)


if __name__ == "__main__":
    unittest.main()
