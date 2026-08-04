# MLAI-025 â€” Campaign Planning Platform

## Status

In Progress

## Architectural Authority

- `governance/adrs/ADR-0007-international-marketing-calendar-architecture.md`
- `governance/adrs/ADR-0008-campaign-planner-boundary.md`

## Objective

Create a provider-neutral Campaign Planning capability that coordinates
campaign objectives, audiences, timelines, channels, success measures,
Marketing Briefs, execution workflows, and versioned persistence.

The Campaign Planner is part of the core MarketingLabAI product and must
benefit every subscription tier.

## Delivery Plan

### MLAI-025.1 â€” Campaign Planner Foundation

- [x] Define Campaign Plan identity and lifecycle.
- [x] Define objective, audience, channel, timeline, and metric value objects.
- [x] Enforce deterministic validation.
- [x] Add serialisation and reconstruction.
- [x] Establish the Campaign Planner boundary in ADR-0008.
- [x] Add focused unit tests.
- [x] Commit and release the completed increment.

### MLAI-025.2 â€” Campaign Planning Service

- [x] Add deterministic plan creation and revision services.
- [x] Add planning-readiness evaluation.
- [x] Add controlled status operations.
- [x] Add structured validation results.
- [x] Add focused service tests.
- [x] Commit and release the completed increment.

### MLAI-025.3 â€” Campaign Structure and Asset Planning

- [x] Define provider-neutral campaign deliverables.
- [x] Define asset priority and lifecycle.
- [x] Add definition-of-done tracking.
- [x] Add deterministic dependency validation and execution ordering.
- [x] Detect duplicate assets and dependency cycles.
- [x] Add blocked-work reporting.
- [x] Add focused asset, dependency, and service tests.
- [x] Commit and release the completed increment.

### MLAI-025.4 â€” Marketing Brief and Workflow Integration

- [x] Associate one or more Marketing Briefs with a Campaign Plan.
- [x] Preserve separate campaign, asset, and brief lifecycles.
- [x] Require approved planning before governed generation where applicable.
- [x] Preserve existing Marketing Brief campaign callers.
- [x] Return campaign-plan audit metadata.

### MLAI-025.5 â€” Persistence and Completion

- [ ] Add immutable, versioned Campaign Plan persistence.
- [ ] Add tenant and brand ownership validation.
- [ ] Add latest-version and history retrieval.
- [ ] Complete Campaign Planner documentation.
- [ ] Run complete regression and engineering review.
- [ ] Commit and release the completed epic.
