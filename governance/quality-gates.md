# Quality Gates

Every production increment must pass:

1. Formatting
2. Static analysis
3. Python compilation
4. Focused unit tests
5. Affected regression tests
6. Public import verification
7. Git scope review

Passing automated tests alone is not product readiness. Each increment must
also classify the applicability and result of usability, accessibility,
browser-journey, failure-recovery, maintainability, cost and operational gates.
An inapplicable gate requires a recorded reason; an incomplete applicable gate
remains a limitation or blocker.

Git scope review begins from an expected-path allowlist. Necessary adjacent
quality repairs are permitted under ADR-0023 when their evidence, tests,
documentation and separate scope reporting are complete.

A failed gate must be investigated before committing.

## Durable Remediation Gate

A failed gate is not closed by a one-off command correction alone. The change
must identify the underlying failure class, correct its authoritative source,
and add automated prevention where reasonably achievable. Temporary
containment must be labelled and tracked as incomplete; it may not weaken a
test, security boundary, authorization boundary, or evidence requirement.

## Intelligence Quality Gates

### Domain Integrity

- Business rules must live in the responsible domain.
- Prompt builders must remain presentation adapters.
- Verified values must not be replaced with AI-generated assumptions.
- Derived metrics must identify and test their source calculations.
- Intelligence builders must omit unsupported conclusions.

### Context and Generation

- Available verified Company Brain context must be used by applicable
  generation workflows.
- Missing context must not be silently fabricated.
- Generation workflows must record material missing context where it affects
  output quality.
- AI-provider output must remain independently validated where deterministic
  validation exists.
- Compliance prompt guidance must not replace post-generation compliance
  evaluation.

### Architecture

- New domains must use existing generic extension points where suitable.
- Core orchestration must not import avoidable domain-specific models.
- Parallel Company Brain, prompt-composition, or workflow systems require an
  ADR.
- New abstractions require demonstrated lifecycle, querying, ownership, or
  integration needs.
- Tenant and brand boundaries must be tested.

### Testing

- New intelligence logic requires focused automated tests.
- Deterministic calculations require boundary and missing-input tests.
- Prompt rendering requires ordering and empty-section tests.
- Repository changes require persistence and isolation tests.
- Workflow changes require end-to-end integration tests.
- Affected regression suites must pass before commit.

### Documentation and Audit

- Material architecture changes require an ADR.
- Capability maturity must be reviewed after a major increment.
- AI-generated assets must preserve provider and model audit data.
- Technical debt and accepted risks must be recorded.
