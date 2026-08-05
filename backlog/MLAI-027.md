# MLAI-027 - Secure Pilot Vertical Slice

## Status

MLAI-027.6 implemented - customer pilot remains founder-frozen

## Product authority

- governance/pdrs/PDR-0001-product-direction-ratification.md
- governance/pdrs/PDR-0002-secure-pilot-vertical-slice.md
- governance/pdrs/PDR-0003-marketing-decision-doctrine.md
- docs/launch-readiness-review.md

## Objective

Compose MarketingLabAI's tested intelligence, planning, generation, compliance,
and persistence capabilities into one secure private-pilot customer journey.

## Pilot outcome

An authorized tenant can provide verified context, plan one campaign, approve a
Marketing Brief, generate one governed marketing asset, review compliance and
limitations, and export the result with a complete audit trail.

## Delivery plan

### MLAI-027.1 - Canonical Application Composition

- [x] Define one application composition root.
- [x] Select SQLite as canonical pilot persistence.
- [x] Compose tenant, brand, Company Brain, Customer Intelligence, Campaign
      Plan, Marketing Brief, Prompt Pack, generation, compliance, and audit.
- [x] Isolate legacy JSON runtime paths behind migration or compatibility
      boundaries.
- [x] Add an ADR for application-boundary and dependency direction.
- [x] Prove the complete slice with synthetic data and no customer interface.

### MLAI-027.2 - Verified Product and Offer Context

- [x] Define minimum Product Intelligence models and validation.
- [x] Capture identity, features, benefits, prices, limitations, proof,
      warranties, availability, and prohibited claims.
- [x] Preserve unknown values explicitly.
- [x] Integrate verified context through established AI context boundaries.
- [x] Add persistence and focused regression coverage.

### MLAI-027.3 - Identity and Tenant Authorization

- [x] Define an external identity-provider adapter boundary.
- [x] Derive tenant access from the authenticated principal.
- [x] Enforce authorization in application services.
- [x] Add cross-tenant denial tests for every exposed operation.
- [x] Audit identity, approval, generation, and export actions.

### MLAI-027.4 - Pilot API and Workflow Contract

- [x] Expose only vertical-slice operations.
- [x] Keep persistence and AI-provider models outside public contracts.
- [x] Add lifecycle conflict and idempotency handling.
- [x] Add synthetic end-to-end API tests.

### MLAI-027.5 - Thin Pilot Workspace

- [x] Add guided onboarding and missing-context indicators.
- [x] Add Campaign Plan and Marketing Brief review.
- [x] Require explicit approval before generation.
- [x] Display content, compliance findings, limitations, and audit metadata.
- [x] Support revision and safe export without direct publishing.

### MLAI-027.6 - Pilot Operations and Release Gate

- [x] Add deployment and runtime configuration.
- [x] Add environment-managed secrets.
- [x] Add tested database backup and restore.
- [x] Add readiness checks and privacy-safe structured logs.
- [x] Add CI gates, operational runbook, data handling, and incident process.
- [x] Pass the synthetic operational gate while retaining the founder freeze on
      any customer pilot.

## Epic acceptance criteria

- [x] The pilot uses one canonical application and persistence path.
- [x] Tenant authorization is derived from trusted identity.
- [x] Cross-tenant access is denied and tested.
- [x] Missing context remains explicit.
- [x] Only approved plans and briefs govern generation.
- [x] Compliance evaluation remains independent from prompt guidance.
- [x] Provider, model, approval, and export audit metadata are preserved.
- [x] Real customer data is prohibited until all private-pilot gates pass.
- [x] Focused and complete regressions pass.
- [x] Risks, debt, capability maturity, ADRs, and handover are current.

## Explicitly deferred

- MLAI-026 Marketing Calendar
- Direct publishing and connector execution
- Billing and public self-service
- Learning, attribution, and Marketing Intelligence Score
- Full Positioning, Strategy, and Executive Intelligence
