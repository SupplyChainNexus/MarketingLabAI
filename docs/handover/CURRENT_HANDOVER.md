# MarketingLabAI Current Handover

## Checkpoint

- Branch: `feature/tenant-architecture`
- Installation baseline: `5c89dc0`
- Remote state before this story: synchronized with
  `origin/feature/tenant-architecture`
- Last completed epic: MLAI-027 Secure Pilot Vertical Slice
- Active epic: MLAI-028 Positioning Intelligence
- Active story: MLAI-028.1 Positioning Intelligence Foundation
- Validation target: positioning, persistence, continuity, and full regression

## Product direction

MarketingLabAI remains a Marketing Intelligence Operating System and the AI
Marketing Department for growing businesses. PDR-0001 through PDR-0003 remain
authoritative. Positioning follows Company, Customer, and Product Intelligence
and must precede Marketing Strategy Intelligence.

## Current implementation

MLAI-027.1 through MLAI-027.6 form one canonical synthetic journey over SQLite,
tenant authorization, external identity boundaries, a retry-safe API, thin
workspace, independent compliance, operational recovery, and release gates.

MLAI-028.1 adds a provider-neutral Positioning Intelligence foundation with
tenant- and brand-owned decisions, explicit target and product references,
separate evidence, assumptions, and unknowns, immutable versions, controlled
approval, and SQLite migration 14.

## Architectural boundary

Positioning is a decision domain, not a Campaign Plan field or prompt-writing
shortcut. Approval requires a recorded value proposition and verified evidence,
but does not claim market effectiveness. Future relevance and differentiation
logic must be deterministic-first and consume established Customer and Product
Intelligence rather than copying their records.

## Release state

The customer pilot remains explicitly founder-frozen. MLAI-028.1 uses synthetic
fixtures and does not add a customer interface, live research, identity vendor,
hosting selection, real customer data, outreach, or pilot activation.

Before reconsideration, require a customer-facing checkpoint, selected live
identity deployment, controlled membership bootstrap, privacy/legal choices,
deployment and restore rehearsal, support ownership, and a new founder-approved
decision. Remind the founder at that point, as requested.

## Remaining constraints

- Positioning references are structurally explicit but not yet checked against
  Customer and Product Intelligence repositories.
- Relevance, differentiation, proof selection, and value-proposition builders
  remain future MLAI-028 increments.
- Marketing Strategy must not begin until the Positioning dependency is ready.
- Direct publishing, billing, public self-service, learning, attribution,
  Calendar, and Executive Intelligence remain deferred.

## Next engineer's first action

Run the complete MLAI-028.1 validator. Then begin MLAI-028.2 by validating
target and product references and producing evidence-grounded deterministic
relevance explanations without silently generating missing research.
