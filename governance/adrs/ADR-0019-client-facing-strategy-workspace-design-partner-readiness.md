# ADR-0019: Client-Facing Strategy Workspace and Design-Partner Readiness

## Status

Accepted for MLAI-029.6.

## Context

Approved Strategy Intelligence was integrated with planning and generation, but
the guided workspace did not expose the decision or provide a controlled way to
assess whether a founder design partner could safely use real customer data.
Operational readiness alone does not authorize a customer pilot.

## Decision

- Extend the same-origin pilot workspace and authorized API with a transport-safe
  view of the exact approved Strategy used by the plan and brief.
- Require matching current Strategy, Positioning, Plan, and Brief versions before
  generation is reported ready.
- Add a deterministic Founder Design Partner readiness evaluator covering founder
  approval, privacy choices, deployed identity, recovery rehearsal, support
  ownership, and accepted data boundaries.
- Record Strand Auto Parts only as the proposed first Founder Design Partner.
- Give the proposed founder account full feature access with billing disabled;
  this entitlement does not authorize real customer data.
- Keep `real_data_activation_authorized` false until a separate founder-approved
  pilot decision is recorded outside this evaluator.

## Consequences

The customer-facing workflow can explain Strategy and surface readiness blockers
without leaking tenant or evidence internals. A fully satisfied checklist means
ready for a founder activation decision, not activated. Synthetic work is not
market validation, performance evidence, or learning.
