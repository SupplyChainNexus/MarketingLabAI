"""Coherent marketing-mix and measurement-plan contracts."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum

from app.strategy_intelligence.choices import ChoiceReport, ObjectiveReadiness
from app.strategy_intelligence.models import StrategyDecision


def _required(value: str, name: str) -> str:
    if not isinstance(value, str):
        raise TypeError(f"{name} must be a string.")
    value = value.strip()
    if not value:
        raise ValueError(f"{name} is required.")
    return value


class MixElement(StrEnum):
    PRODUCT = "product"
    PRICE = "price"
    PLACE = "place"
    PROMOTION = "promotion"
    PEOPLE = "people"
    PROCESS = "process"
    PHYSICAL_EVIDENCE = "physical_evidence"


@dataclass(frozen=True, slots=True)
class MixDecision:
    element: MixElement
    decision: str
    rationale: str
    source_refs: tuple[str, ...]
    constraints: tuple[str, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        object.__setattr__(self, "element", MixElement(self.element))
        object.__setattr__(self, "decision", _required(self.decision, "decision"))
        object.__setattr__(self, "rationale", _required(self.rationale, "rationale"))
        if not self.source_refs:
            raise ValueError("mix decision requires source references.")


@dataclass(frozen=True, slots=True)
class ChannelRole:
    channel: str
    role: str
    objective_ids: tuple[str, ...]
    source_refs: tuple[str, ...]

    def __post_init__(self) -> None:
        object.__setattr__(self, "channel", _required(self.channel, "channel"))
        object.__setattr__(self, "role", _required(self.role, "role"))
        if not self.objective_ids:
            raise ValueError("channel role requires objective_ids.")
        if not self.source_refs:
            raise ValueError("channel role requires source references.")


@dataclass(frozen=True, slots=True)
class MeasurementPlan:
    objective_id: str
    metric: str
    method: str
    cadence: str
    owner: str

    def __post_init__(self) -> None:
        for name in ("objective_id", "metric", "method", "cadence", "owner"):
            object.__setattr__(self, name, _required(getattr(self, name), name))


@dataclass(frozen=True, slots=True)
class MixGap:
    field_name: str
    reason: str


@dataclass(frozen=True, slots=True)
class MarketingMixReport:
    ready: bool
    decisions: tuple[MixDecision, ...]
    channels: tuple[ChannelRole, ...]
    measurements: tuple[MeasurementPlan, ...]
    gaps: tuple[MixGap, ...]
    limitations: tuple[str, ...]


class MarketingMixEvaluator:
    def evaluate(
        self,
        *,
        strategy: StrategyDecision,
        choices: ChoiceReport,
        decisions: list[MixDecision],
        channels: list[ChannelRole],
        measurements: list[MeasurementPlan],
    ) -> MarketingMixReport:
        if not isinstance(strategy, StrategyDecision):
            raise TypeError("strategy must be a StrategyDecision.")
        if choices.readiness is not ObjectiveReadiness.READY:
            raise ValueError("marketing mix requires ready objectives and choices.")
        required = {
            MixElement.PRODUCT,
            MixElement.PRICE,
            MixElement.PLACE,
            MixElement.PROMOTION,
        }
        supplied = {item.element for item in decisions}
        gaps = [
            MixGap(
                f"mix.{element.value}",
                "Required marketing-mix decision is missing.",
            )
            for element in sorted(required - supplied, key=lambda item: item.value)
        ]
        objective_ids = {item.objective_id for item in choices.objectives}
        for channel in channels:
            if not set(channel.objective_ids).issubset(objective_ids):
                gaps.append(
                    MixGap(
                        f"channel.{channel.channel}",
                        "Channel references an unknown objective.",
                    )
                )
        measured = {item.objective_id for item in measurements}
        for objective_id in objective_ids - measured:
            gaps.append(
                MixGap(
                    f"measurement.{objective_id}",
                    "Objective has no measurement plan.",
                )
            )
        return MarketingMixReport(
            not gaps,
            tuple(decisions),
            tuple(channels),
            tuple(measurements),
            tuple(gaps),
            (
                "Budget, pricing and targets are recorded human inputs, "
                "not forecasts or attributed results.",
            ),
        )
