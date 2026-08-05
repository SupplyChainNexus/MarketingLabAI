"""Deterministic situation and opportunity synthesis."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum

from app.customer_intelligence.models import CustomerIntelligenceProfile
from app.intelligence.models import BusinessIntelligenceProfile
from app.positioning_intelligence import PositioningDecision, PositioningStatus
from app.product_intelligence.models import ProductIntelligenceProfile
from app.strategy_intelligence.models import StrategyDecision


def _text(value: str, name: str) -> str:
    if not isinstance(value, str):
        raise TypeError(f"{name} must be a string.")
    value = value.strip()
    if not value:
        raise ValueError(f"{name} is required.")
    return value


class EnvironmentalFactor(StrEnum):
    POLITICAL = "political"
    ECONOMIC = "economic"
    SOCIAL = "social"
    TECHNOLOGICAL = "technological"
    LEGAL = "legal"
    ENVIRONMENTAL = "environmental"


class SignalEffect(StrEnum):
    OPPORTUNITY = "opportunity"
    THREAT = "threat"
    NEUTRAL = "neutral"


@dataclass(frozen=True, slots=True)
class EnvironmentalSignal:
    factor: EnvironmentalFactor
    effect: SignalEffect
    statement: str
    source: str
    observed_at: str
    confidence: float
    verified: bool = False

    def __post_init__(self) -> None:
        object.__setattr__(self, "factor", EnvironmentalFactor(self.factor))
        object.__setattr__(self, "effect", SignalEffect(self.effect))
        object.__setattr__(self, "statement", _text(self.statement, "statement"))
        object.__setattr__(self, "source", _text(self.source, "source"))
        object.__setattr__(self, "observed_at", _text(self.observed_at, "observed_at"))
        if isinstance(self.confidence, bool) or not isinstance(
            self.confidence, (int, float)
        ):
            raise TypeError("confidence must be a number.")
        confidence = float(self.confidence)
        if not 0 <= confidence <= 1:
            raise ValueError("confidence must be between 0 and 1.")
        object.__setattr__(self, "confidence", confidence)


@dataclass(frozen=True, slots=True)
class SituationFinding:
    category: str
    statement: str
    source_refs: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class SituationGap:
    field_name: str
    reason: str


@dataclass(frozen=True, slots=True)
class SituationReport:
    strategy_id: str
    strategy_version: int
    positioning_id: str
    positioning_version: int
    findings: tuple[SituationFinding, ...] = field(default_factory=tuple)
    opportunities: tuple[SituationFinding, ...] = field(default_factory=tuple)
    constraints: tuple[SituationFinding, ...] = field(default_factory=tuple)
    risks: tuple[SituationFinding, ...] = field(default_factory=tuple)
    gaps: tuple[SituationGap, ...] = field(default_factory=tuple)
    limitations: tuple[str, ...] = field(default_factory=tuple)


class SituationSynthesizer:
    """Synthesize only recorded inputs; never infer absent market facts."""

    def synthesize(
        self,
        *,
        strategy: StrategyDecision,
        positioning: PositioningDecision,
        business: BusinessIntelligenceProfile | None = None,
        customer: CustomerIntelligenceProfile | None = None,
        product: ProductIntelligenceProfile | None = None,
        environmental_signals: list[EnvironmentalSignal] | None = None,
    ) -> SituationReport:
        if not isinstance(strategy, StrategyDecision):
            raise TypeError("strategy must be a StrategyDecision.")
        if not isinstance(positioning, PositioningDecision):
            raise TypeError("positioning must be a PositioningDecision.")
        if (
            strategy.tenant_id != positioning.tenant_id
            or strategy.brand_id != positioning.brand_id
        ):
            raise ValueError("strategy and positioning ownership differ.")
        if (
            strategy.positioning_id != positioning.positioning_id
            or strategy.positioning_version != positioning.version
        ):
            raise ValueError(
                "strategy must reference the supplied positioning version."
            )
        if positioning.status is not PositioningStatus.APPROVED:
            raise ValueError("situation synthesis requires approved positioning.")
        if business is not None and business.brand_id != strategy.brand_id:
            raise ValueError("business context belongs to another brand.")
        if customer is not None and customer.brand_id != strategy.brand_id:
            raise ValueError("customer context belongs to another brand.")
        if product is not None and (
            product.tenant_id != strategy.tenant_id
            or product.brand_id != strategy.brand_id
        ):
            raise ValueError("product context belongs to another tenant or brand.")
        signals = environmental_signals or []
        if any(not isinstance(item, EnvironmentalSignal) for item in signals):
            raise TypeError(
                "environmental_signals must contain EnvironmentalSignal objects."
            )

        findings: list[SituationFinding] = []
        opportunities: list[SituationFinding] = []
        constraints: list[SituationFinding] = []
        risks: list[SituationFinding] = []
        gaps: list[SituationGap] = []

        if positioning.value_proposition:
            findings.append(
                SituationFinding(
                    "positioning",
                    positioning.value_proposition,
                    (
                        f"positioning:{positioning.positioning_id}:v{positioning.version}",
                    ),
                )
            )
        for value in positioning.differentiators:
            findings.append(
                SituationFinding(
                    "strength",
                    value,
                    (
                        f"positioning:{positioning.positioning_id}:v{positioning.version}",
                    ),
                )
            )

        if business is None:
            gaps.append(
                SituationGap(
                    "company_context", "Business Intelligence was not supplied."
                )
            )
        else:
            for goal in business.business_goals:
                opportunities.append(
                    SituationFinding(
                        "business_goal",
                        goal,
                        (f"business:{business.brand_id}:{business.updated_at}",),
                    )
                )
            for constraint in business.capacity_constraints:
                constraints.append(
                    SituationFinding(
                        "capacity",
                        constraint,
                        (f"business:{business.brand_id}:{business.updated_at}",),
                    )
                )
            if not business.business_goals:
                gaps.append(
                    SituationGap(
                        "business_goals", "No recorded business goals are available."
                    )
                )

        if customer is None:
            gaps.append(
                SituationGap(
                    "customer_context", "Customer Intelligence was not supplied."
                )
            )
        elif not (
            customer.segments or customer.ideal_customer_profiles or customer.personas
        ):
            gaps.append(
                SituationGap(
                    "target_context", "No customer target records are available."
                )
            )

        if product is None:
            gaps.append(
                SituationGap(
                    "product_context", "Product Intelligence was not supplied."
                )
            )
        elif not product.products:
            gaps.append(
                SituationGap("products", "No verified product records are available.")
            )

        covered = {signal.factor for signal in signals}
        for signal in signals:
            finding = SituationFinding(
                f"environment:{signal.factor.value}",
                signal.statement,
                (f"environment:{signal.source}:{signal.observed_at}",),
            )
            findings.append(finding)
            if signal.effect is SignalEffect.OPPORTUNITY:
                opportunities.append(finding)
            elif signal.effect is SignalEffect.THREAT:
                risks.append(finding)
        for factor in EnvironmentalFactor:
            if factor not in covered:
                gaps.append(
                    SituationGap(
                        f"environment.{factor.value}",
                        "No user-supplied evidence was recorded.",
                    )
                )

        return SituationReport(
            strategy.strategy_id,
            strategy.version,
            positioning.positioning_id,
            positioning.version,
            tuple(findings),
            tuple(opportunities),
            tuple(constraints),
            tuple(risks),
            tuple(gaps),
            (
                "Deterministic synthesis of supplied records; not a forecast or market validation.",
            ),
        )
