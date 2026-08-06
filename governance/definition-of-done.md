# Definition of Done

A feature is complete only when:

- Existing architecture was reviewed.
- No duplicate subsystem was introduced.
- Public interfaces are documented.
- Tests have been added or updated.
- Regression tests pass.
- Formatting passes.
- Python compilation passes.
- Git scope contains only intended files.
- Documentation reflects the implementation.
- Risks and technical debt have been considered.
- Applicable usability, accessibility, browser-journey, failure-recovery and
  operational gates have passed or are explicitly recorded as incomplete or
  inapplicable.
- Necessary adjacent paths are justified, tested and separately reported under
  ADR-0023.

## Continuity gate

An epic or material product increment is not complete until:

- authority documents affected by the change are updated;
- ADRs or PDRs record material durable decisions;
- `docs/handover/CURRENT_HANDOVER.md` reflects the new checkpoint;
- known risks, debt, and deferred decisions are current;
- focused and complete validation evidence is recorded;
- the handover regression test passes;
- a new handover bundle can be generated outside the repository; and
- the committed branch is clean, pushed, and synchronized.

## Intelligence Capability Checklist

A new intelligence capability is not complete until the applicable items below
are satisfied:

- [ ] Intelligence layer is identified.
- [ ] Traditional marketing function or workflow is identified.
- [ ] Customer value and intended outcome are documented.
- [ ] Dependencies on lower intelligence layers are explicit.
- [ ] Missing context is handled without invented facts.
- [ ] Business reasoning is not hidden inside prompt formatting.
- [ ] Deterministic rules and calculations are tested.
- [ ] Tenant and brand ownership boundaries are preserved.
- [ ] Audit metadata is retained where relevant.
- [ ] Public interfaces are documented.
- [ ] Focused automated tests pass.
- [ ] Affected regression suites pass.
- [ ] Architectural decisions are recorded where material.
- [ ] Product Capability Map maturity is reviewed.
- [ ] Risks and technical debt are recorded when unresolved.
- [ ] Documentation matches the implemented behaviour.
