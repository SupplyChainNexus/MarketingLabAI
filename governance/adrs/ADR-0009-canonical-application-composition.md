# ADR-0009 - Canonical Application Composition

## Status

Accepted

## Date

2026-08-05

## Context

MarketingLabAI has tested tenant, Company Brain, Customer Intelligence,
Campaign Plan, Marketing Brief, Prompt Pack, generation, compliance, and audit
capabilities. They were not previously assembled through one application
boundary. The developer CLI still represents a legacy JSON-backed runtime path,
while the newer domain repositories use tenant-aware SQLite persistence.

A secure pilot cannot be built over competing runtime authorities. It needs one
composition root that makes dependency direction explicit and allows future
identity, API, and workspace layers to depend on application services rather
than persistence or provider implementations.

## Decision

Introduce app.application.CanonicalApplication as the canonical application
composition root for the secure pilot.

The root:

- initialises one SQLite database;
- composes tenant, brand, Company Brain, Customer Intelligence, memory,
  Campaign Plan, Marketing Brief, Prompt Pack, and compliance repositories over
  that database;
- composes AI context using Company and Customer Intelligence plus memory;
- composes provider-neutral AI orchestration and campaign generation;
- composes the approved Campaign Plan and Marketing Brief workflow through
  Prompt Pack selection, generation, independent compliance evaluation, and
  artifact persistence;
- requires the campaign artifact persistence boundary to be injected until a
  canonical relational artifact repository is introduced.

Legacy JSON services may remain for compatibility, migration, or existing
developer workflows. They are not a fallback inside the canonical composition
root and may not become runtime authority for the secure pilot.

## Dependency direction

Future API, workspace, and authorization layers depend on the
CanonicalApplication composition root. The root selects application workflows,
provider-neutral provider adapters, explicit artifact persistence, and SQLite
repositories. Domain models do not import SQLite, AI-provider SDKs, user
interfaces, or external identity models. Provider adapters do not own business
rules.

## Security and data boundaries

MLAI-027.1 does not introduce authentication or authorization. Consequently:

- no real customer data is authorised;
- the synthetic proof uses the existing default test tenant only;
- tenant authorization remains required in MLAI-027.3 before any customer
  interface;
- API and UI work remain deferred to MLAI-027.4 and MLAI-027.5.

## Alternatives considered

### Extend the legacy CLI as the pilot boundary

Rejected because it would preserve JSON persistence and bypass the newer
tenant-aware workflow.

### Let each interface construct its own repositories

Rejected because dependency selection would drift and cross-tenant controls
would be harder to enforce consistently.

### Convert every legacy artifact to SQLite in this story

Rejected because it would broaden the story beyond composition. Generated
content and compliance artifacts remain an explicit injected boundary until
their relational lifecycle is designed.

### Add API, UI, and authentication now

Rejected because the approved delivery sequence establishes the application
boundary first and tests it without customer data.

## Consequences

### Positive

- Future interfaces receive one canonical dependency graph.
- SQLite becomes the authoritative pilot persistence path.
- Customer Intelligence now reaches provider prompts through the canonical
  context assembler.
- Provider selection remains replaceable and testable.
- Legacy JSON cannot be selected silently.
- The complete approved-plan workflow is proven with synthetic data.

### Negative

- Brand voice and generated campaign artifacts still require explicit boundary
  inputs.
- Authorization is not yet present and real customer data remains prohibited.
- Existing legacy CLI code remains until a later migration or retirement story.

## Validation

- canonical repositories share one SQLite database instance;
- Company and Customer Intelligence are both assembled;
- Customer Intelligence is rendered into provider requests and audited;
- an approved persisted Campaign Plan and Marketing Brief select a Prompt Pack,
  generate through a mock provider, run independent compliance, and save
  artifacts through an injected boundary;
- focused and complete regressions pass.
