# ADR-0001 — Extensible Prompt Composition

## Status

Accepted

## Date

2026-08-02

## Context

MarketingLabAI currently has two complementary prompt capabilities:

- Versioned Prompt Packs under `app/prompts`
- Generic prompt composition through `PromptSection` and `PromptComposer`

`AIOrchestrator` currently controls the final provider prompt and composes fixed sections for company context, institutional memory, task, and instructions.

New subsystems such as compliance guidance, audience personas, examples, policies, retrieved knowledge, and workflow-specific context need a supported way to add prompt content without:

- constructing one large instruction string;
- modifying `AIOrchestrator` for every new subsystem;
- coupling the Prompt Engine to compliance models;
- creating a second generic prompt-composition package.

## Decision

Extend `AIOrchestrator.generate()` with an optional sequence of additional `PromptSection` objects.

The orchestrator remains responsible for final prompt composition.

Application and workflow adapters may construct generic prompt sections from their own domain models.

The orchestrator will not import compliance, campaign, Prompt Pack, or workflow-specific models.

## Composition order

The final order is:

1. Company Context
2. Relevant Institutional Memory
3. Task
4. Additional workflow sections
5. Instructions

This places grounded context and requirements before the final execution instructions.

## Alternatives considered

### Create a new `app/prompting` package

Rejected because `app/ai/prompt.py` already provides the canonical generic composition model.

### Make Prompt Engine import compliance models

Rejected because the Prompt Engine should understand prompt rendering, not compliance-domain objects.

### Add compliance-specific arguments to AIOrchestrator

Rejected because it would couple provider-neutral orchestration to one subsystem.

### Continue concatenating strings inside CampaignEngine

Rejected because it does not scale to multiple independently testable context sources.

## Consequences

### Positive

- Preserves backward compatibility.
- Provides a single reusable composition extension point.
- Keeps AI orchestration provider-neutral.
- Avoids domain coupling.
- Supports future prompt-section builders.

### Negative

- Workflow adapters must explicitly translate domain objects into `PromptSection` objects.
- Prompt-section ordering becomes part of the orchestrator contract.

## Success criteria

- Existing callers work without modification.
- Additional sections appear in deterministic order.
- Empty sections are omitted by `PromptComposer`.
- Invalid section collections and entries are rejected.
- Existing orchestrator and campaign tests remain green.

## Related components

- `app/ai/prompt.py`
- `app/ai/orchestrator.py`
- `tests/test_ai_orchestrator.py`
