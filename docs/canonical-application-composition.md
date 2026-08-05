# Canonical Application Composition

MLAI-027.1 establishes app.application.CanonicalApplication as the single
composition root for the secure pilot. Future authorization, API, and workspace
layers must enter the product through this boundary.

## Canonical persistence

The root initialises one SQLiteDatabase and constructs the tenant, brand,
Business Intelligence, Customer Intelligence, memory, Campaign Plan, Marketing
Brief, Prompt Pack, and compliance-rule repositories over the same database
instance.

SQLite is the authoritative persistence path for the secure pilot. Legacy JSON
services are compatibility or migration inputs only. The composition root does
not silently instantiate them.

## Governed generation

Provider configuration remains outside the domain. A caller supplies an
IntelligenceProviderRegistry, and the root composes it with the canonical
Company Brain, Customer Intelligence, and memory context.

The caller builds a campaign engine through build_campaign_engine and supplies
it to build_campaign_workflow with an explicit artifact service. The workflow
requires approved planning inputs and preserves the distinct Campaign Plan,
Marketing Brief, Prompt Pack, generation, compliance, and artifact boundaries.

## Explicit limits

- MLAI-027.1 has no customer-facing interface.
- Authentication and tenant authorization arrive in MLAI-027.3.
- No real customer data is permitted before the private-pilot gates pass.
- Generated content and compliance-report persistence remain an injected
  artifact boundary until their canonical relational repository is designed.
- Product and Offer Intelligence begins in MLAI-027.2.

See governance/adrs/ADR-0009-canonical-application-composition.md for the
binding architecture decision.
