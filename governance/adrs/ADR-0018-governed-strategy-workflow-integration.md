# ADR-0018: Governed Strategy Workflow Integration

## Status

Accepted for MLAI-029.5.

## Context

Strategy Intelligence existed as an immutable governed domain, but Campaign
Plans, Marketing Briefs, and AI generation did not yet depend on it. That gap
allowed approved downstream work to omit the strategic decision that should
govern it.

## Decision

- Compose `StrategyRepository`, `StrategyService`, and `StrategyContextProvider`
  through the canonical application.
- Store paired immutable Strategy references on Campaign Plans and Marketing
  Briefs while allowing incomplete drafts.
- Require matching, current, approved, tenant- and brand-owned Strategy
  references for governed generation.
- Require that Strategy and downstream artifacts use the same approved
  Positioning version.
- Render provider-neutral Strategy context and record exact references in audit
  metadata.

## Consequences

Governed generation is traceable from output to Strategy and Positioning.
Revised, retired, stale, missing, or cross-tenant Strategy references block
generation. This story does not activate the customer pilot, add live research,
or claim performance and learning.
