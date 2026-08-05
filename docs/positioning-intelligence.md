# Positioning Intelligence

MLAI-028.1 establishes the trustworthy storage and lifecycle boundary for
Positioning Intelligence. MLAI-028.2 adds deterministic target-product
reference validation and relevance explanations. MLAI-028.3 adds governed
differentiation and proof selection. It does not generate final positioning
automatically.

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

## Target-product relevance

MLAI-028.2 resolves a segment, persona, or ICP from Customer Intelligence and a
product and optional offer from tenant-scoped Product Intelligence. It compares
recorded customer needs, outcomes, or criteria with recorded features and
benefits using transparent normalized term intersections. Each match preserves
both original statements and the shared terms; no opaque relevance score is
invented.

Missing target context, missing product value, absent proof, no supported
intersection, and the currently unmodelled product-use-case field remain
explicit gaps. Product and offer limitations and prohibited claims flow into
the result without being interpreted as benefits.

## Differentiation and proof

MLAI-028.3 evaluates proposed differentiators against the selected product's
recorded features, benefits, proof points, and prohibited claims. Comparative
distinctions additionally require verified evidence for an alternative named
by the positioning decision. Unreviewed, rejected, or undeclared alternative
evidence cannot support selection.

Every selected differentiator preserves product support, proof points,
alternative evidence, review status, and source provenance. Unsupported,
unproven, prohibited, and comparative claims without reviewed alternative
evidence remain explicit gaps. The evaluator neither invents competitor facts
nor treats lexical overlap as market proof.

## Next increment

MLAI-028.4 will build evidence-grounded value propositions and positioning
decisions from governed relevance and differentiation results. Selection in
MLAI-028.3 remains candidate decision support, not approval or market
validation.
