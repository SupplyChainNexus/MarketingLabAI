"""Governed Strategy Intelligence workflow integration tests."""

import tempfile
import unittest
from pathlib import Path

from app.application import CanonicalApplication
from app.database.connection import SQLiteDatabase
from app.positioning_intelligence import (
    PositioningDecision,
    PositioningEvidence,
    PositioningStatus,
    TargetKind,
)
from app.strategy_intelligence import (
    StrategyDecision,
    StrategyEvidence,
    StrategyStatus,
)


class StrategyWorkflowIntegrationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.folder = tempfile.TemporaryDirectory()
        self.application = CanonicalApplication.build(
            SQLiteDatabase(Path(self.folder.name) / "db.sqlite")
        )
        self.application.brands.save(
            {"brand_id": "brand-one", "tenant_id": "default", "name": "One"}
        )
        self.application.positioning_intelligence.save(
            PositioningDecision(
                positioning_id="positioning-one",
                version=1,
                tenant_id="default",
                brand_id="brand-one",
                target_kind=TargetKind.SEGMENT,
                target_id="segment-one",
                product_id="product-one",
                value_proposition="A verified synthetic value proposition.",
                evidence=[PositioningEvidence("Synthetic", "Reviewed", 0.9, True)],
                status=PositioningStatus.APPROVED,
                approved_at="2026-08-06T00:00:00+00:00",
            )
        )

    def tearDown(self) -> None:
        self.folder.cleanup()

    def save_strategy(self, *, version: int = 1) -> StrategyDecision:
        decision = StrategyDecision(
            strategy_id="strategy-one",
            version=version,
            tenant_id="default",
            brand_id="brand-one",
            positioning_id="positioning-one",
            positioning_version=1,
            status=StrategyStatus.APPROVED,
            business_objectives=["Increase qualified synthetic enquiries"],
            strategic_choices=["Prioritise verified high-intent segments"],
            explicit_non_choices=["Do not optimise for unqualified reach"],
            evidence=[StrategyEvidence("Synthetic", "Reviewed objective", 0.9, True)],
            approved_at=f"2026-08-0{5 + version}T00:00:00+00:00",
        )
        self.application.strategy_intelligence.save(decision)
        return decision

    def test_canonical_context_is_traceable_and_provider_neutral(self) -> None:
        strategy = self.save_strategy()
        context = self.application.build_context_assembler().build(
            tenant_id="default",
            brand_id="brand-one",
            positioning_id="positioning-one",
            positioning_version=1,
            strategy_id=strategy.strategy_id,
            strategy_version=strategy.version,
        )
        self.assertTrue(context.strategy_intelligence_included)
        self.assertIn("Strategy reference: strategy-one v1", context.strategy_context)
        self.assertIn("Explicit non-choices", context.strategy_context)

    def test_stale_strategy_context_is_rejected(self) -> None:
        self.save_strategy(version=1)
        self.save_strategy(version=2)
        with self.assertRaisesRegex(ValueError, "stale"):
            self.application.build_context_assembler().build(
                tenant_id="default",
                brand_id="brand-one",
                strategy_id="strategy-one",
                strategy_version=1,
            )


if __name__ == "__main__":
    unittest.main()
