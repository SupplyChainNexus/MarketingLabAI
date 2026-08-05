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

## Value proposition and decision lifecycle

MLAI-028.4 builds a candidate only when target-product relevance, governed
differentiation, proof, and verified positioning evidence belong to the same
immutable version. Its confidence is the minimum confidence carried by the
verified positioning evidence, not an invented intelligence score. Assumptions,
unknown reasons, product limitations, prohibited claims, and source provenance
remain visible.

An incomplete candidate contains no value-proposition claim. A ready candidate
still requires human review, must be copied into a new immutable draft version,
and can then pass the existing approval boundary. Retirement creates another
immutable version. Replacement starts a new draft positioning identity for the
same tenant and brand, preserving the retired history.

## Governed workflow integration

MLAI-028.5 composes the Positioning repository, lifecycle service, and
provider-neutral context adapter through `CanonicalApplication`. Campaign Plans
and Marketing Briefs can reference one immutable positioning identity and
version while they are drafted. Governed generation requires both artifacts to
carry the same reference.

At generation time the referenced decision must belong to the authenticated
tenant and requested brand, be the latest version, and remain approved. Missing,
mismatched, stale, draft, and retired references stop before any AI provider is
called. The context adapter renders the reviewed value proposition, verified
evidence, proof, assumptions, and unknowns as a distinct prompt section.

The authorized API and thin workspace expose a transport-safe positioning
summary and readiness reason. They do not permit positioning mutation or bypass
its human approval lifecycle. Generation audit metadata records the immutable
positioning reference.

## Completion boundary

Positioning Intelligence is now integrated for governed generation. Marketing
Strategy Intelligence remains a separate, future domain and may consume this
approved context in its own story. The customer pilot remains explicitly
founder-frozen and all fixtures remain synthetic.
