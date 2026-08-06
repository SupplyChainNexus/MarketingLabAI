# ADR-0023 — Constitution-Preserving Quality Mandate

## Status

Accepted by the founder on 2026-08-06. Supersedes the narrow-scope
interpretation of LDR-047 and the Repository Integrity Protocol; it does not
weaken their integrity controls.

## Context

Explicit story path allowlists, clean-baseline checks and founder approval for
material boundary changes prevented mixed commits and omitted work. Applied too
narrowly, however, the path allowlist could discourage necessary adjacent bug
fixes, accessibility improvements, consistency repairs, missing tests and
maintainability work merely because those paths were not predicted before
implementation evidence existed.

Passing unit tests can also be mistaken for product readiness when browser
journeys, failure recovery, accessibility, usability and operational evidence
remain incomplete.

## Decision

The Engineering Steward may make reversible, evidence-backed improvements that
strengthen correctness, security, usability, accessibility, maintainability,
testing, recovery or operational clarity, including necessary adjacent paths.

The initial path allowlist is an expected scope, not a prohibition on justified
quality work. Every added path must:

1. trace to an observed defect, risk, usability problem, architectural weakness
   or measurable quality improvement;
2. preserve the Product Constitution, locked decisions, tenant isolation,
   evidence boundaries and human approval;
3. include appropriate tests and documentation;
4. preserve unrelated user work;
5. be identified separately in scope and staged reports; and
6. remain reversible or receive explicit approval before an irreversible step.

Tests may be corrected when their expectation is demonstrably defective. They
must never be weakened merely to obtain a passing result. Every failure remains
classified before repair.

## Reserved founder decisions

Explicit founder approval remains mandatory for:

- real customer data or live invitation delivery;
- public or production activation;
- production publishing;
- paid services, recurring costs or vendor commitments;
- destructive migrations or irreversible data operations;
- privacy-boundary or security-model changes;
- changes to product identity, scope, customer promise, commercial laws,
  Constitution or locked product direction.

No implementation may reduce tenant isolation, evidence traceability,
compliance correctness or core product quality as an optimization.

## Quality evidence

Applicable readiness evidence now covers functional correctness, security,
tenant isolation, usability, accessibility, failure and recovery behaviour,
maintainability, traceability, automated regression, browser-level rehearsal,
cost boundaries and honest limitations. A story documents inapplicable gates
rather than silently omitting them.

## Consequences

Repository integrity remains strict about baselines, unrelated dirty paths,
failure classification, regression, staging and synchronization. Scope can
expand only through evidence and transparent reporting. Material product,
commercial, privacy and activation decisions remain founder-reserved.
