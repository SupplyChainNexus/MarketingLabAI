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
- Durable Remediation identifies and corrects the underlying failure path and
  adds an automated prevention check where reasonably achievable.
- A temporary containment is recorded as incomplete and cannot close the
  defect, story, risk, technical debt, or gate without its durable follow-up.
- Applicable release phases apply **Strong controls + automated sequencing + simple operator experience** through the versioned gate catalogue for orchestration,
  but controller state is never deployment authority. Deployable artifacts
  require the independent evidence and infrastructure controls in ADR-0035.
- A deployment phase cannot be closed by an out-of-order manual command or by
  evidence bound to a different commit, image, environment or release run.

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
## Zero-trust release evidence

- Controller state is never accepted as deployment authority.
- Deployable artifacts are digest-pinned and have authentic build provenance.
- Gate evidence is independently signed, RFC 3161-timestamped and policy-bound.
- A separate final release authority and infrastructure admission control are
  required before deployment or traffic routing.
- Legacy or incomplete runs remain non-deployable and are not repaired into
  compliance.
