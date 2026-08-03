# ADR-0005 — Marketing Brief Domain Boundary

## Status

Accepted

## Date

2026-08-03

## Context

MarketingLabAI already has two mature prompt capabilities:

- generic prompt composition through `PromptSection` and `PromptComposer`;
- versioned Prompt Packs with persistence, selection, rendering, and service
  boundaries.

The platform also has Company Intelligence, Customer Intelligence,
institutional memory, campaign generation, and preventative and evaluative
compliance.

The missing capability is not another Prompt Pack system. The missing
capability is a provider-neutral structure that records the marketing
decisions made before prompt rendering.

Without that structure, objectives, audiences, offers, channels, key messages,
constraints, success measures, assumptions, and supporting evidence may remain
embedded in workflow-specific strings.

## Decision

Introduce `app.marketing_brief` as the canonical structured marketing decision
domain.

A Marketing Brief:

- belongs to a tenant and brand;
- records an objective and intended audience;
- records selected channels and deliverables;
- records the offer, key message, and call to action;
- records constraints and success measures;
- references Customer and Product Intelligence identifiers when available;
- separates traceable evidence from explicit assumptions;
- has an auditable lifecycle and version;
- remains independent of AI providers and Prompt Pack formatting.

## Dependency Direction

```text
Company Intelligence
        +
Customer Intelligence
        +
Product Intelligence when available
        +
Workflow decisions
        |
        v
Marketing Brief
        |
        v
Prompt-section adapter
        |
        v
Existing Prompt Pack and PromptComposer infrastructure
        |
        v
AIOrchestrator
```

## Boundaries

The Marketing Brief domain must not:

- contain provider request objects;
- contain provider-specific model names;
- own Prompt Pack selection;
- own prompt-template rendering;
- hide unsupported assumptions as verified evidence;
- replace compliance evaluation.

Prompt builders remain presentation adapters. They may render a Marketing
Brief into generic prompt sections, but they must not become the source of
marketing strategy.

## Lifecycle

The initial lifecycle is:

1. `draft`
2. `ready`
3. `approved`
4. `retired`

Draft briefs may be incomplete. Ready and approved briefs must contain
channels, deliverables, a key message, and a call to action.

## Consequences

### Positive

- Business reasoning becomes inspectable before prompt generation.
- Existing prompt infrastructure is reused rather than duplicated.
- Provider independence is preserved.
- Evidence and assumptions remain distinguishable.
- Future campaign, SEO, email, social, and research workflows can share one
  brief model.

### Negative

- Workflow adapters must translate their inputs into a Marketing Brief.
- Future persistence and version-selection policies require separate stories.
- Product references may remain empty until Product Intelligence exists.

## Rejected Alternatives

### Add fields directly to PromptPack

Rejected because Prompt Packs define reusable rendering assets, not individual
marketing decisions.

### Create a second prompt-composition package

Rejected because `app.ai.prompt` is already the canonical generic composition
model.

### Keep using CampaignBrief as the universal structure

Rejected because the existing Campaign Brief is workflow-specific and does not
provide a general evidence, assumption, lifecycle, and cross-channel boundary.

## Success Criteria

- Marketing Brief models validate and normalise their data.
- Draft briefs support progressive completion.
- Ready and approved briefs enforce execution requirements.
- Evidence remains traceable.
- Round-trip serialisation preserves nested data.
- Existing prompt, campaign, compliance, and Customer Intelligence tests remain
  green.
