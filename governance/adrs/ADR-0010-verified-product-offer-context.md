# ADR-0010 - Verified Product and Offer Context

## Status

Accepted

## Date

2026-08-05

## Context

The canonical pilot workflow can compose Company and Customer Intelligence,
but it has no governed source for product identity, offer facts, limitations,
proof, warranties, availability, or claims that must not be made. Generation
without that boundary could invent or overstate commercially important facts.

## Decision

Introduce a provider-neutral `app.product_intelligence` domain with:

- tenant- and brand-owned Product Intelligence profiles;
- evidence-backed product and service records;
- separate identity, feature, benefit, proof, limitation, and prohibited-claim
  fields;
- offers whose price, availability, and warranty are either verified or
  explicitly unknown;
- tenant-scoped SQLite persistence under schema migration 10;
- deterministic prompt rendering through `AIContextAssembler`; and
- inclusion audit metadata on provider requests.

Product records require a named evidence source. Time-sensitive offer facts
cannot carry values when unknown and cannot be marked verified without a value.
The context builder renders missing offer facts as `Unknown`.

The canonical repository stores one current profile snapshot per tenant and
brand. Versioned offer history is deferred until pilot evidence defines the
required review, expiry, and approval lifecycle.

## Dependency direction

Product models do not import persistence, provider SDKs, interfaces, or
authentication. The SQLite repository depends on the domain model. The context
provider depends on the repository and deterministic builder. The canonical
composition root injects that provider into provider-neutral AI orchestration.

## Security and data boundaries

MLAI-027.2 does not establish authenticated tenant authorization. Therefore no
real customer data is authorised. Tests and pilot proof use synthetic context.
Future interfaces must enter through `CanonicalApplication` after MLAI-027.3.

## Alternatives considered

### Reuse the legacy brand products list

Rejected because it cannot distinguish evidence, unknown offer facts,
limitations, proof, or prohibited claims and is not tenant-scoped authority.

### Put Product facts directly in prompts

Rejected because prompt text would become an unaudited second source of truth.

### Build the complete Product roadmap now

Rejected because Positioning, Strategy, catalogue ingestion, offer expiry, and
historical approval are separate capabilities. This story establishes only the
minimum trustworthy pilot boundary.

## Consequences

### Positive

- Generated work can consume product and offer facts without silent invention.
- Unknown price, availability, and warranty remain visible.
- Prohibited claims and limitations remain distinct from benefits and proof.
- Tenant ownership is enforced in persistence and reads.
- Product context participates in canonical prompt and audit boundaries.

### Negative

- Offer history and expiry are not yet modelled.
- Evidence sources are recorded but not independently verified by an external
  authority.
- Identity and authorization remain mandatory before real customer use.

## Validation

- model invariants and serialization round trips;
- explicit unknown and evidence rendering;
- tenant ownership and cross-tenant denial;
- idempotent schema migration 10;
- AI prompt assembly and inclusion metadata; and
- shared canonical SQLite composition.
