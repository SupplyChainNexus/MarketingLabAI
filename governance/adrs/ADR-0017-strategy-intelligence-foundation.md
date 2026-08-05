# ADR-0017 - Marketing Strategy Intelligence Foundation

## Status

Accepted

## Date

2026-08-06

## Context

Company, Customer, Product, and Positioning Intelligence now provide governed
inputs, but Campaign Plans and Marketing Briefs cannot act as the strategic
authority. PDR-0003 requires explicit objectives, evidence, choices, coherent
marketing-mix decisions, uncertainty, measurement, and human approval.

## Decision

Introduce provider-neutral `app.strategy_intelligence`. A strategy decision is
tenant- and brand-owned, references one immutable Positioning Intelligence
version, and stores objectives, choices, explicit non-choices, assumptions,
unknowns, evidence, confidence, and lifecycle metadata separately.

Store immutable strategy versions in SQLite migration 15. Creation begins at
draft version 1. Revision creates a new draft. Approval creates another
immutable version and requires at least one business objective, verified
evidence, an approval timestamp, and a matching approved positioning version.
Retirement preserves history.

MLAI-029.1 establishes only the decision and lifecycle foundation. Situation
synthesis, environmental evidence, opportunity analysis, objectives,
marketing mix, measurement, generation context, API, and workspace integration
follow in stories MLAI-029.2 through MLAI-029.6.

## Dependency direction

Models have no provider, persistence, prompt, authentication, or interface
dependency. The repository depends on SQLite and verifies brand ownership. The
service owns lifecycle rules and validates the approved positioning dependency.
Future interfaces must enter through the canonical application boundary.

## Evidence and security boundaries

Strategy confidence is recorded judgment, not predicted effectiveness. Missing
research remains unknown. Synthetic evidence is test data, not market
validation or organizational learning. All reads are tenant-scoped, and the
customer pilot remains founder-frozen.

## Alternatives considered

### Put strategy fields directly in Campaign Plans

Rejected because execution artifacts would become competing strategic authority.

### Generate a strategy entirely inside a prompt

Rejected because evidence, assumptions, gaps, and approval would be hidden.

### Activate the customer workspace with the foundation

Rejected because a model and repository do not satisfy identity, privacy,
deployment, support, or customer-facing readiness gates.

## Consequences

- Marketing Strategy receives a versioned source of truth.
- Approved positioning remains authoritative and traceable.
- Later strategy reasoning can evolve without coupling to an AI provider.
- The customer-pilot freeze remains unchanged through MLAI-029.1.

## Validation

Model invariants, serialization, immutable persistence, stale-write rejection,
approved-positioning enforcement, tenant isolation, idempotent migration 15,
continuity, formatting, lint, and complete regression are required.
