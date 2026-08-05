"""Tests for deterministic situation and opportunity synthesis."""

import unittest

from app.intelligence.models import BusinessIntelligenceProfile
from app.positioning_intelligence import (
    PositioningDecision,
    PositioningEvidence,
    PositioningStatus,
    TargetKind,
)
from app.product_intelligence import ProductIntelligenceProfile
from app.strategy_intelligence import (
    EnvironmentalFactor,
    EnvironmentalSignal,
    SignalEffect,
    SituationSynthesizer,
    StrategyDecision,
)


class StrategySituationTests(unittest.TestCase):
    def positioning(self, **changes: object) -> PositioningDecision:
        values: dict[str, object] = {
            "positioning_id": "positioning-one",
            "version": 2,
            "tenant_id": "tenant-one",
            "brand_id": "brand-one",
            "target_kind": TargetKind.SEGMENT,
            "target_id": "segment-one",
            "product_id": "product-one",
            "status": PositioningStatus.APPROVED,
            "value_proposition": "Evidence-grounded value",
            "differentiators": ["Governed workflow"],
            "evidence": [
                PositioningEvidence("Synthetic", "Synthetic proof", 0.8, True)
            ],
            "approved_at": "2026-08-06T10:00:00+00:00",
        }
        values.update(changes)
        return PositioningDecision(**values)

    def strategy(self, **changes: object) -> StrategyDecision:
        values: dict[str, object] = {
            "strategy_id": "strategy-one",
            "version": 1,
            "tenant_id": "tenant-one",
            "brand_id": "brand-one",
            "positioning_id": "positioning-one",
            "positioning_version": 2,
        }
        values.update(changes)
        return StrategyDecision(**values)

    def signal(
        self, effect: SignalEffect = SignalEffect.OPPORTUNITY
    ) -> EnvironmentalSignal:
        return EnvironmentalSignal(
            EnvironmentalFactor.ECONOMIC,
            effect,
            "Recorded demand signal",
            "Founder-supplied synthetic research",
            "2026-08-06T10:00:00+00:00",
            0.7,
            True,
        )

    def test_synthesizes_recorded_goals_constraints_positioning_and_signals(
        self,
    ) -> None:
        report = SituationSynthesizer().synthesize(
            strategy=self.strategy(),
            positioning=self.positioning(),
            business=BusinessIntelligenceProfile(
                "brand-one",
                business_goals=["Increase qualified enquiries"],
                capacity_constraints=["One-person marketing team"],
            ),
            product=ProductIntelligenceProfile("tenant-one", "brand-one"),
            environmental_signals=[self.signal()],
        )
        self.assertEqual(report.strategy_id, "strategy-one")
        self.assertIn(
            "Increase qualified enquiries",
            [item.statement for item in report.opportunities],
        )
        self.assertIn(
            "Recorded demand signal", [item.statement for item in report.opportunities]
        )
        self.assertEqual(report.constraints[0].statement, "One-person marketing team")
        self.assertTrue(
            any(item.field_name == "environment.legal" for item in report.gaps)
        )
        self.assertIn("not a forecast", report.limitations[0])

    def test_threat_is_a_risk_and_missing_context_stays_explicit(self) -> None:
        report = SituationSynthesizer().synthesize(
            strategy=self.strategy(),
            positioning=self.positioning(),
            environmental_signals=[self.signal(SignalEffect.THREAT)],
        )
        self.assertEqual(report.risks[0].statement, "Recorded demand signal")
        fields = {item.field_name for item in report.gaps}
        self.assertTrue(
            {"company_context", "customer_context", "product_context"}.issubset(fields)
        )

    def test_rejects_unapproved_or_wrong_positioning_version(self) -> None:
        with self.assertRaisesRegex(ValueError, "approved positioning"):
            SituationSynthesizer().synthesize(
                strategy=self.strategy(),
                positioning=self.positioning(
                    status=PositioningStatus.DRAFT, approved_at=""
                ),
            )
        with self.assertRaisesRegex(ValueError, "reference"):
            SituationSynthesizer().synthesize(
                strategy=self.strategy(positioning_version=3),
                positioning=self.positioning(),
            )

    def test_cross_tenant_product_context_is_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "another tenant"):
            SituationSynthesizer().synthesize(
                strategy=self.strategy(),
                positioning=self.positioning(),
                product=ProductIntelligenceProfile("tenant-two", "brand-one"),
            )

    def test_environmental_signal_requires_timestamp_and_bounded_confidence(
        self,
    ) -> None:
        with self.assertRaisesRegex(ValueError, "observed_at"):
            EnvironmentalSignal(
                EnvironmentalFactor.SOCIAL,
                SignalEffect.NEUTRAL,
                "Signal",
                "Source",
                "",
                0.5,
            )
        with self.assertRaisesRegex(ValueError, "between 0 and 1"):
            EnvironmentalSignal(
                EnvironmentalFactor.SOCIAL,
                SignalEffect.NEUTRAL,
                "Signal",
                "Source",
                "timestamp",
                1.2,
            )


if __name__ == "__main__":
    unittest.main()
