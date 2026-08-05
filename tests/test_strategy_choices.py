import unittest

from app.strategy_intelligence import (
    MeasurableObjective,
    ObjectiveReadiness,
    SituationFinding,
    SituationReport,
    StrategicChoice,
    StrategicChoiceEvaluator,
    StrategyDecision,
)


class StrategyChoiceTests(unittest.TestCase):
    def strategy(self):
        return StrategyDecision("s1", 1, "t1", "b1", "p1", 2)

    def situation(self):
        finding = SituationFinding(
            "business_goal", "Grow enquiries", ("business:b1:now",)
        )
        return SituationReport("s1", 1, "p1", 2, opportunities=(finding,))

    def objective(self, refs=("business:b1:now",)):
        return MeasurableObjective(
            "o1",
            "Grow enquiries",
            "qualified enquiries",
            "20 per month",
            "90 days",
            "CRM count",
            refs,
        )

    def choice(self, refs=("business:b1:now",)):
        return StrategicChoice(
            "c1",
            "Prioritise qualified demand",
            "Supports the recorded goal",
            refs,
            0.7,
            ("Broad awareness",),
            ("Limited team",),
        )

    def test_ready_choices_are_traceable_and_preserve_limitations(self):
        report = StrategicChoiceEvaluator().evaluate(
            strategy=self.strategy(),
            situation=self.situation(),
            objectives=[self.objective()],
            choices=[self.choice()],
        )
        self.assertEqual(report.readiness, ObjectiveReadiness.READY)
        self.assertIn("not forecasts", report.limitations[0])

    def test_missing_and_unlinked_inputs_remain_gaps(self):
        empty = StrategicChoiceEvaluator().evaluate(
            strategy=self.strategy(),
            situation=self.situation(),
            objectives=[],
            choices=[],
        )
        self.assertEqual(empty.readiness, ObjectiveReadiness.INCOMPLETE)
        unlinked = StrategicChoiceEvaluator().evaluate(
            strategy=self.strategy(),
            situation=self.situation(),
            objectives=[self.objective(("unknown",))],
            choices=[self.choice(("unknown",))],
        )
        self.assertEqual(len(unlinked.gaps), 2)

    def test_rejects_wrong_situation_version(self):
        with self.assertRaisesRegex(ValueError, "another strategy"):
            StrategicChoiceEvaluator().evaluate(
                strategy=self.strategy(),
                situation=SituationReport("s1", 2, "p1", 2),
                objectives=[],
                choices=[],
            )

    def test_objective_and_choice_contracts_are_strict(self):
        with self.assertRaisesRegex(ValueError, "source references"):
            self.objective(())
        with self.assertRaisesRegex(ValueError, "non-choice"):
            StrategicChoice("c1", "Choose", "Reason", ("source",), 0.5)
        with self.assertRaisesRegex(ValueError, "between 0 and 1"):
            StrategicChoice("c1", "Choose", "Reason", ("source",), 1.2, ("Other",))


if __name__ == "__main__":
    unittest.main()
