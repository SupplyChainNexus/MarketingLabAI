# ADR-0003 — Composable Company Brain Intelligence

## Status

Accepted

## Date

2026-08-02

## Context

Company Brain business intelligence is stored as a structured
BusinessIntelligenceProfile and injected into AI requests through
CompanyBrainPromptBuilder and AIContextAssembler.

The original prompt builder rendered all profile fields through one flat
field-label collection. As Company Brain grows, continuing this pattern would
make the builder increasingly monolithic and difficult to extend.

## Decision

Refactor CompanyBrainPromptBuilder into an orchestrator of focused
IntelligenceSectionBuilder components.

Initial builders are:

- CommercialIntelligenceBuilder
- GrowthIntelligenceBuilder
- MarketIntelligenceBuilder
- OperationalIntelligenceBuilder
- CompetitiveIntelligenceBuilder
- StrategicObjectiveBuilder

BusinessIntelligenceProfile remains the aggregate input.

AIContextAssembler remains the single integration point for Company Brain
prompt context.

## Deterministic intelligence

Growth calculations may be derived only from verified profile values.

The builders must not:

- invent missing data;
- infer unsupported commercial conclusions;
- make autonomous recommendations;
- change persisted profile values.

## Alternatives considered

### Expand the flat field-label tuple

Rejected because it would preserve monolithic prompt rendering.

### Introduce generic knowledge-module persistence

Deferred because the current aggregate and repository already support the
available intelligence fields.

### Create separate repositories for every intelligence area

Rejected as premature. Persistence boundaries should be introduced when
independent lifecycle, querying or versioning requirements are demonstrated.

## Consequences

### Positive

- Company Brain rendering becomes modular.
- New intelligence sections can be introduced independently.
- Derived metrics remain deterministic and testable.
- Persistence, onboarding and AI orchestration remain unchanged.
- Empty sections are omitted automatically.

### Negative

- Prompt formatting changes from one flat list to titled sections.
- Exact prompt regression tests require deliberate updates.
- Builder ordering becomes part of the Company Brain contract.

## Success criteria

- Existing profile persistence remains unchanged.
- AIContextAssembler requires no modification.
- Empty intelligence sections are omitted.
- Builder ordering is deterministic.
- Derived values are based only on verified inputs.
- Existing Company Brain and orchestrator tests remain green.

## Related components

- app/intelligence/models.py
- app/intelligence/builders/
- app/ai/context.py
- app/ai/assembler.py
