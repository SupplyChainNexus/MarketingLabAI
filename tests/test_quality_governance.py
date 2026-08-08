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

    def test_privacy_decision_is_versioned_and_does_not_activate_real_data(self):
        decision = self.read(
            "governance/adrs/ADR-0025-pilot-privacy-data-boundaries.md"
        )
        handling = self.read("docs/privacy-and-data-handling.md")

        for required in (
            "default-deny",
            "atomically",
            "real_data_activation_authorized",
            "real-data periods unset",
        ):
            self.assertIn(required, decision)
        self.assertIn("Real-data retention and deletion periods", handling)
        self.assertIn("must approve jurisdiction", handling)

    def test_production_security_readiness_requires_evidence_without_activation(self):
        decision = self.read(
            "governance/adrs/ADR-0026-production-identity-security-readiness.md"
        )

        for required in (
            "fresh Google authentication",
            "Missing or false evidence is a blocker",
            "permits founder activation assessment only",
            "real customer data",
        ):
            self.assertIn(required, decision)
        self.assertRegex(decision, r"active\s+tenant membership")

    def test_operational_readiness_preserves_failures_and_activation_boundary(self):
        decision = self.read(
            "governance/adrs/ADR-0027-recovery-monitoring-support-readiness.md"
        )
        normalized = " ".join(decision.split())
        for required in (
            "unsupported configuration booleans",
            "Failed results require a failure classification",
            "different environment or commit",
            "permits MLAI-030.6 acceptance rehearsal only",
            "never authorizes real data",
        ):
            self.assertIn(required, normalized)

    def test_partner_acceptance_is_tenant_bound_and_never_activates(self):
        decision = self.read(
            "governance/adrs/ADR-0028-design-partner-acceptance-rehearsal.md"
        )
        normalized = " ".join(decision.split())
        for required in (
            "separately for each approved partner tenant",
            "authenticated tenant must match",
            "Request-supplied booleans are not acceptance evidence",
            "does not authorize external invitations",
            "real data",
        ):
            self.assertIn(required, normalized)

    def test_controlled_hosting_refuses_unsafe_sqlite_deployment(self):
        decision = self.read(
            "governance/adrs/ADR-0030-controlled-hosting-durable-persistence.md"
        )
        normalized = " ".join(decision.split())
        for required in (
            "must not be deployed",
            "PostgreSQL",
            "external secret bindings",
            "explicit founder decisions",
            "never authorizes an external invitation or real data",
        ):
            self.assertIn(required, normalized)

    def test_postgresql_compatibility_requires_live_evidence(self):
        decision = self.read(
            "governance/adrs/ADR-0031-repository-wide-postgresql-compatibility.md"
        )
        normalized = " ".join(decision.split())
        for required in (
            "21-table schema",
            "preserves and hashes the source",
            "Any mismatch rolls back",
            "cannot substitute for a live PostgreSQL rehearsal",
            "does not delete or mutate the SQLite source",
            "No Google API",
        ):
            self.assertIn(required, normalized)

    def test_private_synthetic_deployment_preserves_activation_boundaries(self):
        decision = self.read(
            "governance/adrs/ADR-0032-controlled-private-synthetic-deployment.md"
        )
        normalized = " ".join(decision.split())
        for required in (
            "IAM-authenticated",
            "digest-pinned container",
            "dedicated least-privilege runtime identity",
            "no parallel application path",
            "unauthenticated invocation are refused",
            "real-customer data",
            "billing",
            "real-data learning remain frozen",
        ):
            self.assertIn(required, normalized)

    def test_durable_remediation_is_binding_and_ci_enforced(self):
        sources = (
            "AGENTS.md",
            "governance/product-constitution.md",
            "governance/locked-decision-register.md",
            "governance/definition-of-done.md",
            "governance/adrs/ADR-0033-durable-remediation-directive.md",
        )

        for source in sources:
            self.assertIn("Durable Remediation", self.read(source), source)

        decision = self.read(
            "governance/adrs/ADR-0033-durable-remediation-directive.md"
        )
        normalized = " ".join(decision.split())
        for required in (
            "authoritative source",
            "automated prevention",
            "Temporary containment",
            "cannot close the defect",
            "Manual reconstruction",
        ):
            self.assertIn(required, normalized)

        workflow = self.read(".github/workflows/quality.yml")
        self.assertIn("validate_private_synthetic_deployment.ps1", workflow)


if __name__ == "__main__":
    unittest.main()
