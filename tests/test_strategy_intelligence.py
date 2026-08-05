"""Tests for evidence-grounded Marketing Strategy Intelligence models."""

import unittest

from app.strategy_intelligence import (
    StrategyDecision,
    StrategyEvidence,
    StrategyStatus,
    StrategyUnknown,
)


class StrategyIntelligenceTests(unittest.TestCase):
    def evidence(self, *, verified: bool = True) -> StrategyEvidence:
        return StrategyEvidence(
            source="Synthetic planning evidence",
            summary="Synthetic evidence supports a planning objective.",
            confidence=0.8,
            verified=verified,
        )

    def decision(self, **changes: object) -> StrategyDecision:
        values: dict[str, object] = {
            "strategy_id": "strategy-one",
            "version": 1,
            "tenant_id": "tenant-one",
            "brand_id": "brand-one",
            "positioning_id": "positioning-one",
            "positioning_version": 2,
            "business_objectives": ["Increase qualified enquiries"],
            "unknowns": [StrategyUnknown("budget", "Not yet approved")],
            "evidence": [self.evidence()],
            "confidence": 0.7,
        }
        values.update(changes)
        return StrategyDecision(**values)

    def test_round_trip_preserves_evidence_unknowns_and_status(self) -> None:
        decision = self.decision(assumptions=["Synthetic assumption"])
        self.assertEqual(StrategyDecision.from_dict(decision.to_dict()), decision)

    def test_approved_strategy_requires_objective_evidence_and_timestamp(self) -> None:
        with self.assertRaisesRegex(ValueError, "business objective"):
            self.decision(
                status=StrategyStatus.APPROVED,
                business_objectives=[],
                approved_at="timestamp",
            )
        with self.assertRaisesRegex(ValueError, "verified evidence"):
            self.decision(
                status=StrategyStatus.APPROVED,
                evidence=[self.evidence(verified=False)],
                approved_at="timestamp",
            )
        with self.assertRaisesRegex(ValueError, "approved_at"):
            self.decision(status=StrategyStatus.APPROVED)

    def test_draft_cannot_claim_approval_timestamp(self) -> None:
        with self.assertRaisesRegex(ValueError, "only approved"):
            self.decision(approved_at="timestamp")

    def test_confidence_versions_and_unique_unknowns_are_validated(self) -> None:
        with self.assertRaisesRegex(ValueError, "between 0 and 1"):
            self.decision(confidence=1.1)
        with self.assertRaisesRegex(ValueError, "positioning_version"):
            self.decision(positioning_version=0)
        unknown = StrategyUnknown("price", "Unknown")
        with self.assertRaisesRegex(ValueError, "unknown field names"):
            self.decision(unknowns=[unknown, unknown])


if __name__ == "__main__":
    unittest.main()
