# ADR-0034 — Progressive Release Automation and Operator Simplicity

## Status

Accepted — founder authorized on 2026-08-09

## Context

The private synthetic deployment preserved security and data boundaries, but
separate scripts, numbered assertions and manually assembled cloud commands made
the operational sequence difficult to understand. Configuration and command-
harness defects were found only after cloud operations began. Fixed evidence
filenames also made a safe corrected attempt unnecessarily cumbersome.

The product needs stronger delivery control without allowing governance work to
stop customer-value development.

## Decision

MarketingLabAI adopts **Strong controls + automated sequencing + simple operator experience**
through progressive assurance.

The immediate private-synthetic release path has one repository-owned,
machine-readable gate catalogue and one dependency-aware controller. Each release
attempt is bound to an exact commit, image digest, environment and operator in a
unique evidence directory outside the repository. Gate results are append-only
and hash-chained. A gate cannot pass before its declared prerequisites, and a
non-mutating gate cannot claim a cloud mutation.

The controller is deliberately minimal. It validates and records sequence and
evidence but does not execute cloud commands or grant authority. Cloud mutation,
private traffic and every higher-risk boundary still require their existing
separate approvals. PowerShell remains a thin, PowerShell 5.1-compatible operator
interface over the tested Python controller.

Controls required to prevent unsafe, unordered, untraceable or irreversible
change apply immediately. Browser journeys, observability, rollback, support,
privacy, real-data, performance and scale controls remain binding progressive
gates before their corresponding boundaries open; they do not block local or
controlled synthetic product development prematurely.

## Immediate sequence

1. `SOURCE_VERIFIED`
2. `CI_PASSED`
3. `ARTIFACT_VERIFIED`
4. `CONFIGURATION_VALIDATED`
5. `CLOUD_PREFLIGHT_PASSED`
6. `REVISION_CREATED`
7. `STARTUP_VERIFIED`
8. `SMOKE_TESTS_PASSED`
9. `PRIVATE_TRAFFIC_AUTHORIZED`
10. `PRIVATE_TRAFFIC_ROUTED`
11. `RELEASE_CLOSED`

The identifiers distinguish dependent release phases from independent runtime
safety assertions. Gate numbers in reports are never authority by themselves.

## Failure and retry contract

A failed result requires a classification, remediation and safe next action.
The failed run remains terminal evidence. A corrected attempt starts a new run;
evidence is not overwritten or relabelled. Mutation-capable phases require a
separate authorization reference.

## Consequences

Invalid ordering, evidence collisions and unauthorized mutation claims become
deterministically testable. Operators receive one status model rather than a
collection of remembered commands. The initial controller does not yet perform
Cloud Run deployment, browser smoke tests or rollback; those remain explicitly
tracked progressive work and cannot be represented as complete.

Public access, external invitations, billing, publishing, real-customer data and
real-data learning remain frozen.
