# MLAI-024 — Marketing Brief and Prompt Integration

## Status

Complete

## Objective

Introduce the provider-neutral Marketing Brief domain that records structured
marketing decisions before prompt rendering and integrate it with existing
Prompt Pack, campaign, and compliance infrastructure.

## Architecture Decision

The existing Prompt Pack system is extended, not replaced. Marketing reasoning
belongs in the Marketing Brief domain. Prompt builders remain presentation
adapters.

See:

- `governance/adrs/ADR-0005-marketing-brief-boundary.md`
- `docs/marketing-brief.md`

## Delivery Plan

### MLAI-024.1 — Marketing Brief Domain Foundation

- [x] Lifecycle, evidence model, validation, serialisation, tests, and ADR.

### MLAI-024.2 — Brief Prompt Adapter

- [x] Deterministic `PromptSection` adaptation and ordering tests.

### MLAI-024.3 — Prompt Pack Integration

- [x] Declared-variable mapping, selection, versioning, and audit metadata.

### MLAI-024.4 — Workflow Integration

- [x] Approved-brief campaign generation with pre- and post-compliance support.

### MLAI-024.5 — Persistence and Completion

- [x] Versioned Marketing Brief persistence.
- [x] Tenant and brand ownership checks.
- [x] Documentation and engineering review.
- [x] Complete validation suite.
- [x] MLAI-024 completion.

## Acceptance Criteria

- [x] Business reasoning is not hidden inside prompt formatting.
- [x] Marketing Briefs remain provider-neutral.
- [x] Evidence and assumptions remain distinguishable.
- [x] Existing Prompt Pack infrastructure is reused.
- [x] Existing campaign callers remain compatible.
- [x] Pre- and post-generation compliance remain active.
- [x] Brief history is immutable and tenant-owned.
- [x] Existing regression tests remain green.
