# PDR-0002 — Secure Pilot Vertical Slice

## Status

Accepted

## Date

2026-08-05

## Decision owner

Founder

## Context

The Launch Readiness and Vertical-Slice Review at checkpoint `db7a6c8` found a
strong tested domain core but no secure customer-usable journey through it. The
developer CLI still uses legacy persistence and generation paths, while newer
tenant-aware planning, brief, Prompt Pack, and governed compliance workflows
are not composed into an application entry point.

MLAI-026 Marketing Calendar is technically unblocked but does not address the
largest obstacle to customer evidence.

## Rabbit Rule classification

Core.

## Decision

Approve **MLAI-027 — Secure Pilot Vertical Slice** as the next epic and keep
MLAI-026 deferred.

MLAI-027 will deliver one controlled journey in which an authorized tenant can:

1. provide verified Company, Customer, and minimum Product/Offer context;
2. create and approve a Campaign Plan and Marketing Brief;
3. generate one governed marketing asset;
4. review compliance findings and explicit limitations; and
5. export the result with an audit trail.

The epic will compose existing domains through one canonical application
boundary and SQLite persistence. Legacy JSON workflows may remain migration or
compatibility inputs but may not be competing runtime authority.

The first target is a private controlled pilot, not public self-service SaaS.
Real customer data may not enter the pilot until identity, tenant authorization,
cross-tenant denial tests, secret management, backup/restore, and data-handling
gates pass.

## Delivery sequence

1. MLAI-027.1 — Canonical Application Composition
2. MLAI-027.2 — Verified Product and Offer Context
3. MLAI-027.3 — Identity and Tenant Authorization
4. MLAI-027.4 — Pilot API and Workflow Contract
5. MLAI-027.5 — Thin Pilot Workspace
6. MLAI-027.6 — Pilot Operations and Release Gate

## Explicit exclusions

- Marketing Calendar implementation
- Direct channel publishing
- Autonomous execution
- Billing and public self-service subscriptions
- Performance learning and attribution
- Marketing Intelligence Score
- Full Positioning, Strategy, or Executive Intelligence engines

## Alternatives considered

### Implement MLAI-026 next

Rejected because another planning domain would not make existing capabilities
usable by a customer.

### Build a user interface over the legacy CLI workflow

Rejected because it would make split persistence and architectural bypasses
more difficult to remove.

### Begin public SaaS launch immediately

Rejected because identity, authorization, deployment, monitoring, backup, and
commercial operations are not yet implemented.

## Consequences

- Engineering priority moves from isolated capability expansion to one customer
  outcome.
- Interface work is now justified, but only over the canonical application
  boundary.
- Security and operational foundations enter before real customer data.
- MLAI-026 remains preserved and may be reconsidered after pilot evidence.
- Existing Product, Positioning, and Strategy sequencing remains intact beyond
  the minimum verified Product/Offer context needed for the pilot.

## Approval

Founder: Approved, 2026-08-05
