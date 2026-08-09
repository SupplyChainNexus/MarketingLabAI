import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class MarketingEfficiencyGovernanceTests(unittest.TestCase):
    def read(self, relative_path: str) -> str:
        return (ROOT / relative_path).read_text(encoding="utf-8-sig")

    def normalized(self, relative_path: str) -> str:
        return " ".join(self.read(relative_path).split())

    def test_locked_target_is_consistent(self):
        for source in (
            "AGENTS.md",
            "governance/product-constitution.md",
            "governance/locked-decision-register.md",
            "governance/quality-gates.md",
            "governance/adrs/ADR-0036-simple-operator-and-measured-marketing-efficiency.md",
            "docs/marketing-efficiency-evidence-protocol.md",
        ):
            content = self.normalized(source)
            self.assertIn("5-10 hours saved per week", content, source)
            self.assertIn("40-60%", content, source)

    def test_claim_remains_qualified(self):
        decision = self.normalized(
            "governance/adrs/ADR-0036-simple-operator-and-measured-marketing-efficiency.md"
        )
        for required in (
            "designed to",
            "aims to",
            "targeting",
            "must not claim a guarantee",
            "Synthetic benchmarks remain synthetic",
        ):
            self.assertIn(required, decision)

    def test_simple_operator_rule_is_binding(self):
        for source in (
            "AGENTS.md",
            "governance/product-constitution.md",
            "governance/locked-decision-register.md",
            "governance/quality-gates.md",
        ):
            normalized = self.normalized(source).lower()
            self.assertIn("three meaningful", normalized, source)
            self.assertIn("progressive disclosure", normalized, source)

    def test_measurement_protocol_refuses_misleading_comparisons(self):
        protocol = self.normalized("docs/marketing-efficiency-evidence-protocol.md")
        for required in (
            "same start state",
            "mean, median and range",
            "Failed and abandoned runs",
            "Team-wide totals",
            "Time saved cannot be represented as revenue",
        ):
            self.assertIn(required, protocol)

    def test_story_is_queued_behind_active_hosting(self):
        backlog = self.read("backlog/MLAI-032.md")
        self.assertIn("must not interrupt active MLAI-031", backlog)
        self.assertIn(
            "Real-customer measurement remains separately authorized", backlog
        )

    def test_ci_executes_marketing_efficiency_gate(self):
        workflow = self.read(".github/workflows/quality.yml")
        self.assertIn("validate_marketing_efficiency_governance.ps1", workflow)


if __name__ == "__main__":
    unittest.main()
