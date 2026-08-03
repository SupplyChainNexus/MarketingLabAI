# MLAI-023 — Customer Intelligence AI Context Integration

## Status

In Progress

## Objective

Make validated Customer Intelligence automatically available to AI workflows
through the shared AI context assembly pipeline.

## Business Value

Marketing outputs should reflect who the business serves, including customer
segments, personas, pain points, motivations, objections, preferred channels,
language, and evidence confidence.

## Architecture

```text
Company Intelligence -----------+
                                 |
CustomerIntelligenceRepository   |
        |                        |
        v                        v
CustomerContextBuilder --> CustomerContextProvider
                                 |
Institutional Memory ------------+
                                 |
                                 v
                         AIContextAssembler
                                 |
                                 v
                              AIContext
```

## Architectural Rules

1. Domain package `__init__.py` files must not re-export infrastructure
   adapters when doing so introduces an upward dependency or circular import.
2. Infrastructure adapters must be imported from their concrete module.
3. New optional AI context fields must preserve existing positional constructor
   compatibility where practical.
4. Missing optional intelligence must result in empty context, not fabricated
   content or workflow failure.

## Sub-stories

### MLAI-023.1 — Customer Context Provider

- [x] Load Customer Intelligence from SQLite.
- [x] Return empty context when no profile exists.
- [x] Convert stored profiles into deterministic context.
- [x] Avoid circular imports between domain and database layers.

### MLAI-023.2 — AIContextAssembler Integration

- [x] Add `customer_context` to `AIContext`.
- [x] Add Customer Intelligence inclusion metadata.
- [x] Integrate `CustomerContextProvider`.
- [x] Preserve Company Brain and memory behaviour.
- [x] Preserve existing positional `AIContext` arguments.
- [x] Validate invalid provider dependencies.

### MLAI-023.3 — Regression and Documentation

- [ ] Run focused and affected regression suites.
- [ ] Review architecture documentation.
- [ ] Record completion evidence.
- [ ] Clean temporary build artifacts.
- [ ] Commit.

## Acceptance Criteria

- Missing Customer Intelligence is handled without failure.
- Existing Customer Intelligence is rendered deterministically.
- Invalid dependencies are rejected.
- Repository errors are not silently swallowed.
- Existing Company Brain and memory behaviour remains unchanged.
- Domain package imports do not create circular dependencies.
- Existing positional construction of `AIContext` remains valid.
- Automated tests pass.

## Related Decisions

- ADR-0004 Marketing Intelligence Hierarchy
- Future ADR-0005 Customer Intelligence Architecture
