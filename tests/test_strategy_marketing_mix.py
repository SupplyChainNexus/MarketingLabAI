import unittest

from app.strategy_intelligence import (
    ChannelRole,
    ChoiceReport,
    MarketingMixEvaluator,
    MeasurableObjective,
    MeasurementPlan,
    MixDecision,
    MixElement,
    ObjectiveReadiness,
    StrategicChoice,
    StrategyDecision,
)


class MarketingMixTests(unittest.TestCase):
    def choices(self) -> ChoiceReport:
        objective = MeasurableObjective(
            "o1", "Grow", "leads", "20", "90 days", "CRM", ("source",)
        )
        choice = StrategicChoice("c1", "Focus", "Reason", ("source",), 0.7, ("Other",))
        return ChoiceReport(ObjectiveReadiness.READY, (objective,), (choice,), (), ())

    def decisions(self) -> list[MixDecision]:
        return [
            MixDecision(item, "Decision", "Reason", ("source",))
            for item in (
                MixElement.PRODUCT,
                MixElement.PRICE,
                MixElement.PLACE,
                MixElement.PROMOTION,
            )
        ]

    def strategy(self) -> StrategyDecision:
        return StrategyDecision("s1", 1, "t1", "b1", "p1", 2)

    def test_complete_mix_is_ready(self) -> None:
        report = MarketingMixEvaluator().evaluate(
            strategy=self.strategy(),
            choices=self.choices(),
            decisions=self.decisions(),
            channels=[ChannelRole("Search", "Capture demand", ("o1",), ("source",))],
            measurements=[MeasurementPlan("o1", "leads", "CRM", "weekly", "owner")],
        )
        self.assertTrue(report.ready)
        self.assertIn("not forecasts", report.limitations[0])

    def test_missing_mix_and_measurement_are_gaps(self) -> None:
        report = MarketingMixEvaluator().evaluate(
            strategy=self.strategy(),
            choices=self.choices(),
            decisions=[],
            channels=[],
            measurements=[],
        )
        self.assertFalse(report.ready)
        self.assertEqual(len(report.gaps), 5)

    def test_unknown_channel_objective_is_gap(self) -> None:
        report = MarketingMixEvaluator().evaluate(
            strategy=self.strategy(),
            choices=self.choices(),
            decisions=self.decisions(),
            channels=[ChannelRole("Email", "Retain", ("missing",), ("source",))],
            measurements=[MeasurementPlan("o1", "leads", "CRM", "weekly", "owner")],
        )
        self.assertFalse(report.ready)

    def test_incomplete_choices_are_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "ready objectives"):
            MarketingMixEvaluator().evaluate(
                strategy=self.strategy(),
                choices=ChoiceReport(ObjectiveReadiness.INCOMPLETE, (), (), (), ()),
                decisions=[],
                channels=[],
                measurements=[],
            )


if __name__ == "__main__":
    unittest.main()
