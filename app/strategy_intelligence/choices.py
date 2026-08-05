"""Deterministic objective and strategic-choice validation."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum

from app.strategy_intelligence.models import StrategyDecision
from app.strategy_intelligence.situation import SituationReport


def _required(value: str, name: str) -> str:
    if not isinstance(value, str):
        raise TypeError(f"{name} must be a string.")
    value = value.strip()
    if not value:
        raise ValueError(f"{name} is required.")
    return value


class ObjectiveReadiness(StrEnum):
    READY = "ready"
    INCOMPLETE = "incomplete"


@dataclass(frozen=True, slots=True)
class MeasurableObjective:
    objective_id: str
    outcome: str
    metric: str
    target: str
    timeframe: str
    method: str
    source_refs: tuple[str, ...]
    baseline: str = ""

    def __post_init__(self) -> None:
        for name in (
            "objective_id",
            "outcome",
            "metric",
            "target",
            "timeframe",
            "method",
        ):
            object.__setattr__(self, name, _required(getattr(self, name), name))
        if not self.source_refs:
            raise ValueError("objective requires source references.")


@dataclass(frozen=True, slots=True)
class StrategicChoice:
    choice_id: str
    decision: str
    rationale: str
    source_refs: tuple[str, ...]
    confidence: float
    non_choices: tuple[str, ...] = field(default_factory=tuple)
    constraints: tuple[str, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        for name in ("choice_id", "decision", "rationale"):
            object.__setattr__(self, name, _required(getattr(self, name), name))
        if not self.source_refs:
            raise ValueError("strategic choice requires source references.")
        if isinstance(self.confidence, bool) or not isinstance(
            self.confidence, (int, float)
        ):
            raise TypeError("confidence must be a number.")
        confidence = float(self.confidence)
        if not 0 <= confidence <= 1:
            raise ValueError("confidence must be between 0 and 1.")
        object.__setattr__(self, "confidence", confidence)
        if not self.non_choices:
            raise ValueError(
                "strategic choice requires at least one explicit non-choice."
            )


@dataclass(frozen=True, slots=True)
class ChoiceGap:
    field_name: str
    reason: str


@dataclass(frozen=True, slots=True)
class ChoiceReport:
    readiness: ObjectiveReadiness
    objectives: tuple[MeasurableObjective, ...]
    choices: tuple[StrategicChoice, ...]
    gaps: tuple[ChoiceGap, ...]
    limitations: tuple[str, ...]


class StrategicChoiceEvaluator:
    def evaluate(
        self,
        *,
        strategy: StrategyDecision,
        situation: SituationReport,
        objectives: list[MeasurableObjective],
        choices: list[StrategicChoice],
    ) -> ChoiceReport:
        if (
            situation.strategy_id != strategy.strategy_id
            or situation.strategy_version != strategy.version
        ):
            raise ValueError("situation report belongs to another strategy version.")
        if any(not isinstance(item, MeasurableObjective) for item in objectives):
            raise TypeError("objectives must contain MeasurableObjective objects.")
        if any(not isinstance(item, StrategicChoice) for item in choices):
            raise TypeError("choices must contain StrategicChoice objects.")
        gaps: list[ChoiceGap] = []
        if not objectives:
            gaps.append(
                ChoiceGap("objectives", "No measurable objective was supplied.")
            )
        if not choices:
            gaps.append(
                ChoiceGap("strategic_choices", "No strategic choice was supplied.")
            )
        known_refs = {
            ref
            for group in (
                situation.findings,
                situation.opportunities,
                situation.constraints,
                situation.risks,
            )
            for item in group
            for ref in item.source_refs
        }
        for objective in objectives:
            if not set(objective.source_refs).intersection(known_refs):
                gaps.append(
                    ChoiceGap(
                        f"objective.{objective.objective_id}.evidence",
                        "Objective is not linked to the situation evidence.",
                    )
                )
        for choice in choices:
            if not set(choice.source_refs).intersection(known_refs):
                gaps.append(
                    ChoiceGap(
                        f"choice.{choice.choice_id}.evidence",
                        "Choice is not linked to the situation evidence.",
                    )
                )
        readiness = (
            ObjectiveReadiness.READY if not gaps else ObjectiveReadiness.INCOMPLETE
        )
        return ChoiceReport(
            readiness,
            tuple(objectives),
            tuple(choices),
            tuple(gaps),
            ("Targets are recorded human inputs, not forecasts or promised outcomes.",),
        )
