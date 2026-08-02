# ADR-0004 — Marketing Intelligence Hierarchy

## Status

Accepted

## Date

2026-08-02

## Context

MarketingLabAI has established foundational capabilities for:

- Company Brain;
- institutional memory;
- prompt composition;
- AI provider orchestration;
- campaign generation;
- preventative compliance guidance;
- post-generation compliance evaluation;
- persistence and audit metadata.

The next product capabilities include customer personas, product intelligence,
positioning, strategy, learning, analytics, forecasting, and executive
decision support.

Without a formal hierarchy, these capabilities could be implemented in an
order that produces unsupported reasoning, duplicated knowledge, or premature
analytics.

## Decision

MarketingLabAI will use the following intelligence hierarchy:

1. Company Intelligence
2. Customer Intelligence
3. Product Intelligence
4. Positioning Intelligence
5. Marketing Strategy Intelligence
6. Campaign Intelligence and Generation
7. Compliance and Governance
8. Learning Intelligence
9. Executive Intelligence

Higher layers should consume the strongest validated outputs available from
lower layers.

The hierarchy defines preferred dependency and delivery order. It does not
require every workflow to have complete data at every layer. Missing context
must remain explicit and must not be silently invented.

## Generation Principle

AI generation is an output of structured intelligence.

The preferred workflow is:

```text
Company
    -> Customer
    -> Product
    -> Positioning
    -> Strategy
    -> Generation
    -> Compliance
    -> Execution
    -> Learning
```

## Deterministic-First Principle

MarketingLabAI will prefer:

1. verified source data;
2. deterministic calculations;
3. explicit rules;
4. structured AI reasoning;
5. generative output.

AI-generated assumptions must not be represented as verified Company Brain
knowledge.

## Delivery Waves

### Wave 1 — Strategic Intelligence

- Customer Intelligence
- Product Intelligence
- Positioning Intelligence
- Marketing Strategy Intelligence
- Governed Campaign Execution

### Wave 2 — Learning and Executive Intelligence

- Campaign Learning
- Experiment Planning
- Marketing Analytics
- Attribution
- Forecasting
- Budget Optimization
- Executive Decision Support

Wave 2 requires sufficient real execution data.

## Domain Architecture

Major intelligence domains should use established platform patterns where
their complexity justifies them:

- validated domain models;
- repository and service boundaries;
- deterministic builders or evaluators;
- generic prompt adapters;
- tests;
- documentation;
- auditable metadata.

The platform will avoid creating abstractions that do not yet have
demonstrated lifecycle, querying, or integration requirements.

## Prompt Boundary

Prompt builders format and present intelligence.

They must not become the source of business strategy, domain validation, or
unsupported commercial reasoning.

## Company Brain Boundary

Company Brain remains the governed source of organizational marketing
knowledge.

New intelligence domains should extend its structured knowledge architecture
rather than create disconnected brain systems.

## Alternatives Considered

### Build Marketing Strategy first

Rejected because strategy requires explicit customer, product, and positioning
context.

### Build Product Intelligence before Customer Intelligence

Rejected as the default sequence because product relevance and benefit
priority depend on the intended customer.

### Build forecasting and optimization before pilots

Rejected because meaningful forecasting and optimization require real
execution and outcome data.

### Continue generation using campaign briefs only

Rejected because it would preserve MarketingLabAI as primarily a content
generator rather than an intelligence operating system.

## Consequences

### Positive

- Establishes a coherent product identity.
- Makes roadmap dependencies explicit.
- Reduces premature analytics and synthetic learning.
- Connects engineering work to customer value.
- Creates a repeatable pattern for future intelligence engines.
- Strengthens buyer and enterprise readiness.

### Negative

- Adds discipline before generation, which can increase workflow complexity.
- Requires explicit handling of incomplete context.
- Delays advanced analytics until meaningful data exists.
- Requires governance documents and capability maturity to remain current.

## Success Criteria

- New roadmap items identify their intelligence layer.
- Customer Intelligence precedes Product and Positioning Intelligence.
- Product and Persona context feed Positioning Intelligence.
- Strategy consumes available Company, Customer, Product, and Positioning
  context.
- Generated content remains independently compliance-checked.
- Learning claims rely on real evidence.
- Capability maturity is maintained in the Product Capability Map.

## Related Documents

- governance/product-constitution.md
- governance/product-capability-map.md
- docs/intelligence_roadmap.md
- docs/product_vision.md
- docs/architecture/ARCHITECTURE_PRINCIPLES.md
- governance/development-methodology.md
- governance/definition-of-done.md
- governance/quality-gates.md
