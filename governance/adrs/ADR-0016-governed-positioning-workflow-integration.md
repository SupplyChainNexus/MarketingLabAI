# ADR-0016 - Governed Positioning Workflow Integration

## Status

Accepted

## Date

2026-08-06

## Context

MLAI-028.1 through MLAI-028.4 establish immutable, evidence-grounded
Positioning Intelligence, but the canonical application, planning artifacts,
generation, and pilot review surface do not yet consume it. Allowing prompts or
interfaces to select arbitrary positioning would bypass tenant ownership,
approval, version currency, and evidence boundaries.

## Decision

Compose `PositioningRepository`, `PositioningService`, and a provider-neutral
`PositioningContextProvider` through `CanonicalApplication`.

Campaign Plans and Marketing Briefs may carry an optional positioning identity
and version during drafting. Governed generation requires both approved
artifacts to reference the same immutable positioning version. The referenced
decision must belong to the authenticated tenant and requested brand, be the
latest version, and remain approved. Validation occurs before the AI provider
is called.

The context provider renders approved positioning as a separate prompt section.
It preserves verified evidence, proof, limitations, assumptions, and unknowns;
it performs no strategy reasoning and creates no new claims.

The authorized pilot API and thin workspace expose safe readiness and review
details but do not mutate Positioning Intelligence. Generation audit metadata
records the positioning identity and version.

## Consequences

- Draft, retired, stale, missing, cross-brand, and cross-tenant positioning
  cannot reach governed generation.
- Planning remains backward-compatible while drafts are being prepared.
- Provider adapters receive only formatted approved intelligence.
- Marketing Strategy remains a separate downstream domain.
- Existing synthetic pilot operations gain review visibility without customer
  pilot activation.

## Alternatives considered

### Infer positioning from a brand at generation time

Rejected because inference hides which immutable decision governed an asset and
can silently change when a newer version appears.

### Copy positioning text into plans and briefs

Rejected because copied text loses lifecycle authority and evidence provenance.

### Add positioning approval controls to the execution workspace

Rejected because it would collapse strategic decision approval into campaign
execution and enlarge the frozen pilot surface.

## Validation

Automated tests cover canonical composition, serialization, approved context
rendering, provider metadata, missing and mismatched references, stale and draft
decisions, tenant and brand boundaries, API readiness, workspace rendering,
continuity, and complete regression.
