# MLAI-027 - Secure Pilot Vertical Slice

## Status

In progress - MLAI-027.2 implemented

## Product authority

- governance/pdrs/PDR-0001-product-direction-ratification.md
- governance/pdrs/PDR-0002-secure-pilot-vertical-slice.md
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

- [ ] Define an external identity-provider adapter boundary.
- [ ] Derive tenant access from the authenticated principal.
- [ ] Enforce authorization in application services.
- [ ] Add cross-tenant denial tests for every exposed operation.
- [ ] Audit identity, approval, generation, and export actions.

### MLAI-027.4 - Pilot API and Workflow Contract

- [ ] Expose only vertical-slice operations.
- [ ] Keep persistence and AI-provider models outside public contracts.
- [ ] Add lifecycle conflict and idempotency handling.
- [ ] Add synthetic end-to-end API tests.

### MLAI-027.5 - Thin Pilot Workspace

- [ ] Add guided onboarding and missing-context indicators.
- [ ] Add Campaign Plan and Marketing Brief review.
- [ ] Require explicit approval before generation.
- [ ] Display content, compliance findings, limitations, and audit metadata.
- [ ] Support revision and safe export without direct publishing.

### MLAI-027.6 - Pilot Operations and Release Gate

- [ ] Add deployment and runtime configuration.
- [ ] Add environment-managed secrets.
- [ ] Add tested database backup and restore.
- [ ] Add readiness checks and privacy-safe structured logs.
- [ ] Add CI gates, operational runbook, data handling, and incident process.
- [ ] Pass synthetic-pilot and private-pilot security gates.

## Epic acceptance criteria

- [ ] The pilot uses one canonical application and persistence path.
- [ ] Tenant authorization is derived from trusted identity.
- [ ] Cross-tenant access is denied and tested.
- [ ] Missing context remains explicit.
- [ ] Only approved plans and briefs govern generation.
- [ ] Compliance evaluation remains independent from prompt guidance.
- [ ] Provider, model, approval, and export audit metadata are preserved.
- [ ] Real customer data is prohibited until all private-pilot gates pass.
- [ ] Focused and complete regressions pass.
- [ ] Risks, debt, capability maturity, ADRs, and handover are current.

## Explicitly deferred

- MLAI-026 Marketing Calendar
- Direct publishing and connector execution
- Billing and public self-service
- Learning, attribution, and Marketing Intelligence Score
- Full Positioning, Strategy, and Executive Intelligence
