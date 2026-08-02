# MarketingLabAI Product Constitution

## Status

Locked

## Effective Date

2026-08-02

## Purpose

This constitution records the enduring product principles that guide
MarketingLabAI's architecture, roadmap, engineering priorities, and customer
value.

Changes to these principles require deliberate review and, where they affect
architecture, an Architecture Decision Record.

## 1. Product Identity

MarketingLabAI is a Marketing Intelligence Operating System.

It is not primarily:

- an AI copywriting tool;
- a social-media caption generator;
- a generic chatbot;
- a single-provider AI wrapper.

Its purpose is to combine structured organizational knowledge, deterministic
reasoning, governed AI generation, compliance, workflow execution, memory, and
continuous learning to help organizations make and execute better marketing
decisions.

## 2. Core Product Promise

MarketingLabAI helps a business:

1. Understand itself.
2. Understand its customers.
3. Understand its products and services.
4. Determine relevant positioning.
5. Develop an evidence-grounded marketing strategy.
6. Generate governed marketing assets.
7. Validate those assets.
8. Learn from real outcomes.
9. Improve future decisions.

## 3. Marketing Intelligence Hierarchy

The platform evolves through the following intelligence layers:

1. Company Intelligence
2. Customer Intelligence
3. Product Intelligence
4. Positioning Intelligence
5. Marketing Strategy Intelligence
6. Campaign Intelligence and Generation
7. Compliance and Governance
8. Learning Intelligence
9. Executive Intelligence

Each higher layer should consume validated knowledge from the layers beneath it.

A layer may operate with incomplete lower-layer context when necessary, but:

- missing context must be explicit;
- unsupported facts must not be invented;
- confidence and limitations should be visible where relevant;
- bypassing foundational intelligence must not become the default design.

## 4. Generation Philosophy

Generation is an output of intelligence, not a substitute for intelligence.

The preferred workflow is:

Company understanding
    -> Customer understanding
    -> Product understanding
    -> Positioning
    -> Strategy
    -> Generation
    -> Compliance validation
    -> Approval and execution
    -> Learning

MarketingLabAI must use the strongest verified context available before asking
an AI provider to generate content.

## 5. Deterministic-First Principle

The platform uses the following order of trust:

1. Verified business data
2. Deterministic calculations
3. Explicit rules and configured policies
4. Structured AI reasoning
5. AI-generated content

AI must not silently replace missing verified data with invented claims.

Derived intelligence must be traceable to its source inputs or declared rules.

## 6. Company Brain Principle

Company Brain is the governed source of organizational marketing knowledge.

It evolves through composable intelligence domains rather than one
ever-expanding object or multiple disconnected brain systems.

Current and planned domains include:

- commercial intelligence;
- market intelligence;
- operational intelligence;
- growth intelligence;
- competitive intelligence;
- strategic objectives;
- customer intelligence;
- product intelligence;
- positioning intelligence;
- campaign learning.

## 7. Domain Architecture Principle

A major intelligence domain should normally include, where justified:

- domain models;
- validation;
- persistence or repository boundaries;
- application services;
- deterministic builders or evaluators;
- prompt adapters;
- automated tests;
- documentation;
- an ADR for material architectural decisions.

Not every small feature requires every component. Architecture must remain
proportionate to demonstrated requirements.

## 8. Prompt Architecture Principle

Prompt builders are presentation adapters.

They may:

- select verified information;
- organize information;
- format instructions;
- omit empty information;
- produce generic prompt sections.

They must not become the primary home of business rules, commercial
calculations, strategy decisions, or domain validation.

Business reasoning belongs in domain models, services, evaluators, and
intelligence builders.

## 9. Compliance Principle

Compliance is both preventative and evaluative.

The system should:

1. Guide generation with applicable requirements.
2. Generate content using those requirements.
3. Evaluate the resulting content independently.
4. Preserve the resulting compliance report and audit trail.

Prompt guidance does not replace post-generation validation.

## 10. Learning Principle

MarketingLabAI will not represent synthetic assumptions as organizational
learning.

Learning Intelligence must be grounded in evidence such as:

- campaign delivery;
- audience engagement;
- conversion events;
- revenue outcomes;
- approval and rejection history;
- compliance findings;
- experiments;
- customer feedback.

## 11. Human Accountability Principle

MarketingLabAI augments marketing capability but does not remove human
accountability.

Human judgment remains important for:

- business priorities;
- final approvals;
- legal interpretation;
- ethical decisions;
- creative direction;
- exceptional circumstances;
- high-impact budget decisions.

## 12. Buyer-Readiness Principle

The platform must remain understandable and transferable.

Buyer readiness requires:

- clean and documented architecture;
- original and traceable intellectual property;
- strong automated tests;
- clear dependency boundaries;
- auditable AI use;
- maintained ADRs;
- documented risks and technical debt;
- a coherent capability roadmap.

## 13. Customer Value Test

Before a major capability is approved, it should answer:

1. Which marketing capability does it improve?
2. Which traditional marketing role or workflow does it augment?
3. Which measurable customer outcome does it support?
4. How does it fit the intelligence hierarchy?
5. How will its quality and value be verified?
6. Does it strengthen the long-term platform?

## 14. Locked Delivery Waves

### Wave 1 — Strategic Intelligence

1. Customer Intelligence
2. Product Intelligence
3. Positioning Intelligence
4. Marketing Strategy Intelligence
5. Governed campaign execution

### Wave 2 — Learning and Decision Intelligence

1. Campaign Learning
2. Experiment Planning
3. Performance Attribution
4. KPI Forecasting
5. Marketing Analytics
6. Budget Optimization
7. Executive Intelligence

Wave 2 capabilities should be implemented when sufficient real execution data
exists to make them meaningful.
