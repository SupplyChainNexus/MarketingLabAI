# MLAI-025 — Campaign Planning Platform

## Status

In Progress

## Architectural Authority

- `governance/adrs/ADR-0007-international-marketing-calendar-architecture.md`
- `governance/adrs/ADR-0008-campaign-planner-boundary.md`

## Objective

Create a provider-neutral Campaign Planning capability that coordinates
objectives, audiences, timelines, channels, success measures, Marketing
Briefs, execution workflows, and versioned persistence.

The Campaign Planner is part of the core product and benefits every tier.

## MLAI-025.1 — Campaign Planner Foundation

- [x] Define Campaign Plan identity and lifecycle.
- [x] Define objective, audience, channel, timeline, and metric value objects.
- [x] Enforce deterministic validation.
- [x] Add serialisation and reconstruction.
- [x] Establish the boundary in ADR-0008.
- [x] Add focused unit tests.
- [ ] Commit and release the completed increment.

## MLAI-025.2 — Campaign Planning Service

- [ ] Add deterministic plan creation and revision services.
- [ ] Add planning-readiness evaluation.
- [ ] Add controlled lifecycle operations.
- [ ] Add structured validation results.
- [ ] Add focused service tests.

## MLAI-025.3 — Campaign Structure and Asset Planning

- [ ] Define planned assets and dependencies.
- [ ] Define channel-specific deliverables.
- [ ] Add prioritisation and sequencing.
- [ ] Add deterministic scheduling.
- [ ] Detect duplicates and circular dependencies.

## MLAI-025.4 — Marketing Brief and Workflow Integration

- [ ] Associate one or more briefs with a Campaign Plan.
- [ ] Preserve separate lifecycles.
- [ ] Require approved planning where applicable.
- [ ] Preserve existing callers.
- [ ] Return plan audit metadata.

## MLAI-025.5 — Persistence and Completion

- [ ] Add immutable, versioned persistence.
- [ ] Add tenant and brand ownership validation.
- [ ] Add latest-version and history retrieval.
- [ ] Complete documentation.
- [ ] Run complete engineering review.
- [ ] Commit and release the completed epic.

## Acceptance Criteria

- [ ] Campaign Plans are provider-neutral.
- [ ] Campaign and Marketing Brief lifecycles remain separate.
- [ ] Planning quality is complete on every subscription tier.
- [ ] Tiers differ by capacity, collaboration, automation, and strategic depth.
- [ ] Plans are reviewable before content generation.
- [ ] Persistence preserves version history.
- [ ] Existing campaign, brief, compliance, and intelligence workflows remain
      compatible.
- [ ] MLAI-026 Marketing Calendar work remains deferred.
