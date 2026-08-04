# ADR-0008 — Campaign Planner Boundary

## Status

Accepted

## Date

2026-08-04

## Context

MarketingLabAI can already capture approved Marketing Briefs, select versioned
Prompt Packs, generate campaign content, review compliance, and persist
generation outputs.

The platform does not yet have a first-class structure that represents the
campaign being planned before individual briefs or content assets are created.

Without a dedicated Campaign Planner boundary:

- content requests can remain isolated rather than coordinated;
- campaign objectives, audiences, channels, timelines, ownership, and success
  measures can be scattered across briefs and workflow arguments;
- campaign lifecycle state can become confused with Marketing Brief lifecycle;
- future Marketing Calendar work may be forced to depend directly on content
  generation models;
- planning logic may leak into prompt rendering or AI-provider workflows.

## Decision

Introduce a provider-neutral `app.campaign_planner` domain.

The Campaign Planner owns campaign identity, tenant and brand identifiers,
name, owner, objective, audience, timeline, selected channels, success
metrics, notes, lifecycle state, validation, and serialisation.

It does not own Marketing Brief lifecycle, Prompt Pack selection, prompt
construction, content generation, compliance evaluation, publishing,
performance ingestion, or calendar synchronisation. Campaign Plan persistence
is implemented behind a repository boundary and does not enter the domain model.

MLAI-025.1 establishes only the domain foundation.

## Campaign Lifecycle

```text
Draft -> Planned -> Approved -> Active -> Completed -> Archived
```

A planned campaign may return to Draft. An approved campaign may return to
Planned. Campaign lifecycle remains independent from Marketing Brief
lifecycle.

## Dependency Direction

```text
Application workflows
        |
        v
Campaign Planner domain
```

The Campaign Planner domain must not import AI-provider, Prompt Pack,
compliance, publishing, external calendar, or persistence models.

## Relationship to Marketing Calendar

ADR-0007 reserves the future Marketing Calendar domain. A future calendar may
create or contain campaign windows. MLAI-025.1 does not implement calendar
functionality.

## Relationship to Marketing Brief

A Campaign Plan describes the coordinated campaign. A Marketing Brief records
approved execution decisions for a campaign or deliverable. Future integration
may associate one or more briefs with a plan, but MLAI-025.1 does not embed
Marketing Brief objects.

### MLAI-025.4 Integration Contract

Campaign Plans associate Marketing Briefs through immutable, version-aware
references containing campaign, brief, tenant, and brand identifiers. Neither
domain embeds or controls the lifecycle of the other.

The existing Marketing Brief campaign workflow accepts an optional Campaign
Plan. Calls without a plan retain their established behaviour. When a plan is
supplied, governed generation requires an approved or active plan, matching
tenant and brand ownership, and a channel included in both the brief and plan.
The workflow returns immutable campaign-plan and brief-version audit metadata.

### MLAI-025.5 Persistence Contract

Campaign Plans are stored as immutable `(campaign_id, version)` rows. Repository
reads are tenant-scoped, saves verify tenant existence and brand ownership, and
history is preserved when a detached successor version is created. The domain
remains independent from SQLite; persistence depends on the domain, not the
reverse.

## Alternatives Considered

### Continue using the legacy CampaignBrief as the plan

Rejected because `CampaignBrief` is an execution input and does not own
campaign lifecycle, coordinated channels, timelines, or success metrics.

### Add planning fields directly to MarketingBrief

Rejected because campaign planning and execution briefing have distinct
lifecycles. One campaign may eventually require multiple briefs.

### Put campaign planning inside the AI prompt layer

Rejected because campaign planning is reviewable business logic that must
remain deterministic and provider-neutral.

### Implement persistence in the foundation story

Rejected because domain semantics should stabilise before database design.

## Consequences

### Positive

- Campaigns become first-class, reviewable business objects.
- Planning remains deterministic and provider-neutral.
- Marketing Brief and campaign lifecycle responsibilities remain separate.
- Future calendar, workflow, persistence, and analytics work gains a stable
  boundary.
- Every subscription tier can use the same complete planning quality.

### Negative

- Later stories must integrate plans with briefs and campaign workflows.
- Callers must respect lifecycle transitions.
- Immutable history increases storage use and requires explicit successor versions.

## Success Criteria

- Campaign planning models are available through `app.campaign_planner`.
- Required campaign context is validated.
- Lifecycle transitions are controlled.
- Models serialise and rebuild without provider dependencies.
- Existing workflows remain compatible.
- No persistence or AI integration is introduced in MLAI-025.1.
