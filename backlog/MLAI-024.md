# MLAI-024 — Marketing Brief and Prompt Integration

## Status

In Progress

## Objective

Introduce the provider-neutral Marketing Brief domain that records structured
marketing decisions before prompt rendering, then integrate it with the
existing Prompt Pack, PromptComposer, AIContextAssembler, and AIOrchestrator
architecture.

## Architecture Decision

The existing Prompt Pack system will be extended, not replaced.

Marketing reasoning belongs in the Marketing Brief domain. Prompt builders
remain presentation adapters.

See:

- `governance/adrs/ADR-0005-marketing-brief-boundary.md`

## Delivery Plan

### MLAI-024.1 — Marketing Brief Domain Foundation

- [x] Marketing Brief lifecycle.
- [x] Evidence model.
- [x] Core validation and normalisation.
- [x] Progressive draft support.
- [x] Readiness validation.
- [x] Round-trip serialisation.
- [x] Focused tests.
- [x] Architecture decision record.

### MLAI-024.2 — Brief Prompt Adapter

- [x] Convert a Marketing Brief into deterministic `PromptSection` objects.
- [x] Preserve evidence and assumption boundaries.
- [x] Omit empty optional sections.
- [x] Add ordering tests.

### MLAI-024.3 — Prompt Pack Integration

- [ ] Map Marketing Brief values into Prompt Pack variables.
- [ ] Preserve Prompt Pack selection and versioning.
- [ ] Return Prompt Pack audit metadata.
- [ ] Add integration tests.

### MLAI-024.4 — Workflow Integration

- [ ] Integrate approved Marketing Briefs with campaign generation.
- [ ] Preserve existing campaign callers.
- [ ] Preserve pre- and post-generation compliance.
- [ ] Add affected regression tests.

### MLAI-024.5 — Persistence and Completion

- [ ] Add versioned Marketing Brief persistence.
- [ ] Add tenant and brand ownership checks.
- [ ] Complete documentation and engineering review.
- [ ] Run the complete validation suite.
- [ ] Commit and release.

## Acceptance Criteria

- Business reasoning is not hidden inside prompt formatting.
- Marketing Briefs remain provider-neutral.
- Evidence and assumptions remain distinguishable.
- Existing Prompt Pack infrastructure is reused.
- Existing prompt, campaign, compliance, and intelligence tests remain green.
