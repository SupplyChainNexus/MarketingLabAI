# ADR-0015 - Positioning Intelligence Foundation

## Status

Accepted

## Date

2026-08-06

## Context

MarketingLabAI has governed Company, Customer, Product, Campaign, Generation,
Compliance, and synthetic operational capabilities, but it lacks the decision
layer that explains why a specific offer should be preferred by a selected
customer. Campaign Plans and Marketing Briefs must not become an accidental
substitute for Positioning Intelligence.

PDR-0003 requires segmentation and target selection to precede final
positioning and strategy, with evidence, assumptions, uncertainty, and unknowns
kept distinct. The customer pilot remains founder-frozen.

## Decision

Introduce a provider-neutral `app.positioning_intelligence` domain. A
positioning decision is tenant- and brand-owned and explicitly references a
target kind and identifier, product identifier, and optional offer identifier.

Positioning decisions preserve customer problem, frame of reference, value
proposition, differentiators, proof, alternatives, assumptions, unknowns, and
evidence as separate fields. Evidence records source, summary, confidence, and
verification state.

Store immutable versions in SQLite under migration 14. New and revised
decisions are drafts. Approval creates a new immutable version and requires a
non-empty value proposition, verified evidence, and approval timestamp.

MLAI-028.1 establishes the domain and lifecycle boundary only. Deterministic
target-product relevance, differentiation, positioning builders, prompt
adapters, and application integration follow in dependency order.

## Dependency direction

Positioning models contain no persistence, provider, interface, authentication,
or prompt dependency. The repository depends on the models and SQLite. The
lifecycle service depends on the repository. Future integration must enter
through the canonical application boundary.

## Security and evidence boundaries

Repository writes verify tenant ownership of the brand. Reads require tenant
scope. No interface exposure, live research ingestion, or real customer data is
authorized. Synthetic evidence may exercise the workflow but may not be
represented as market validation or organizational learning.

## Alternatives considered

### Put positioning fields in Campaign Plans or Marketing Briefs

Rejected because execution artifacts would become competing strategic
authority and historical positioning decisions would be difficult to audit.

### Generate positioning directly in prompts

Rejected because prompts would hide business reasoning, evidence gaps, and
approval state.

### Build Positioning and Strategy together

Rejected because Strategy depends on approved positioning and owns different
decisions, including objectives, marketing mix, channels, and measurement.

## Consequences

- Positioning receives an explicit, versioned source of truth.
- Evidence, assumptions, and unknowns remain distinguishable.
- Approval does not imply market effectiveness.
- Integration remains intentionally incomplete until later MLAI-028 stories.
- The customer-pilot freeze remains unchanged.

## Validation

Model invariants, serialization, immutable version history, controlled
approval, stale revision rejection, tenant ownership, cross-tenant reads,
idempotent migration 14, continuity, and complete regression are automated.
