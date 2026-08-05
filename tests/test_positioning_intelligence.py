"""Tests for evidence-grounded Positioning Intelligence models."""

import unittest

from app.positioning_intelligence import (
    PositioningDecision,
    PositioningEvidence,
    PositioningStatus,
    PositioningUnknown,
    TargetKind,
)


class PositioningIntelligenceTests(unittest.TestCase):
    def evidence(self, *, verified: bool = True) -> PositioningEvidence:
        return PositioningEvidence(
            source="Synthetic customer interview summary",
            summary="Synthetic operators value predictable approval workflows.",
            confidence=0.8,
            verified=verified,
        )

    def decision(self, **changes: object) -> PositioningDecision:
        values: dict[str, object] = {
            "positioning_id": "positioning-one",
            "version": 1,
            "tenant_id": "tenant-one",
            "brand_id": "brand-one",
            "target_kind": TargetKind.PERSONA,
            "target_id": "persona-one",
            "product_id": "product-one",
            "customer_problem": "Disconnected marketing decisions",
            "unknowns": [PositioningUnknown("competitor price", "Not yet researched")],
            "evidence": [self.evidence()],
        }
        values.update(changes)
        return PositioningDecision(**values)

    def test_round_trip_preserves_evidence_unknowns_and_enums(self) -> None:
        decision = self.decision(assumptions=["Synthetic assumption"])
        self.assertEqual(PositioningDecision.from_dict(decision.to_dict()), decision)

    def test_approved_positioning_requires_value_evidence_and_timestamp(self) -> None:
        with self.assertRaisesRegex(ValueError, "value proposition"):
            self.decision(status=PositioningStatus.APPROVED, approved_at="timestamp")
        with self.assertRaisesRegex(ValueError, "verified evidence"):
            self.decision(
                status=PositioningStatus.APPROVED,
                value_proposition="Evidence-grounded marketing decisions",
                evidence=[self.evidence(verified=False)],
                approved_at="timestamp",
            )
        with self.assertRaisesRegex(ValueError, "approved_at"):
            self.decision(
                status=PositioningStatus.APPROVED,
                value_proposition="Evidence-grounded marketing decisions",
            )

    def test_draft_cannot_claim_an_approval_timestamp(self) -> None:
        with self.assertRaisesRegex(ValueError, "only approved"):
            self.decision(approved_at="timestamp")

    def test_confidence_and_identifiers_are_validated(self) -> None:
        with self.assertRaisesRegex(ValueError, "between 0 and 1"):
            PositioningEvidence("source", "summary", 1.1)
        with self.assertRaisesRegex(ValueError, "version"):
            self.decision(version=0)

    def test_unknown_field_names_are_unique(self) -> None:
        unknown = PositioningUnknown("price", "Unknown")
        with self.assertRaisesRegex(ValueError, "unknown field names"):
            self.decision(unknowns=[unknown, unknown])


if __name__ == "__main__":
    unittest.main()
