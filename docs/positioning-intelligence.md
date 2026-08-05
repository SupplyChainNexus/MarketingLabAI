# Positioning Intelligence

MLAI-028.1 establishes the trustworthy storage and lifecycle boundary for
Positioning Intelligence. It does not yet calculate customer-product fit or
generate positioning automatically.

## Domain boundary

A `PositioningDecision` belongs to one tenant and brand and identifies:

- one selected segment, persona, or Ideal Customer Profile;
- one verified product and an optional offer;
- the customer problem and market frame being considered;
- a proposed value proposition, differentiators, proof, and alternatives;
- evidence with confidence and verification state;
- assumptions that still require confirmation; and
- explicit unknown fields with reasons.

Unknowns, assumptions, and evidence are intentionally separate. Synthetic or
AI-generated analysis cannot silently become verified positioning knowledge.

## Lifecycle

Every stored version is immutable. New decisions begin as draft version 1.
Revision creates another draft version. Approval creates a new approved version
and requires both a value proposition and verified evidence. Historical
versions remain available for audit.

Approval in this foundation confirms that a human accepted the recorded
positioning decision; it does not prove market effectiveness. Effectiveness
requires later real outcome evidence.

## Persistence and security

Schema migration 14 adds `positioning_decisions`. Repository reads include the
tenant identifier, saves verify brand ownership, and cross-tenant reads return
no decision. This story does not expose a new interface and authorizes no real
customer data.

## Next increment

MLAI-028.2 will validate target and product references against established
Customer and Product Intelligence and produce deterministic relevance
explanations before differentiation or value-proposition automation begins.
