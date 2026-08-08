# ADR-0033 — Durable Remediation Directive

## Status

Accepted by founder on 2026-08-08.

## Context

One-off command repairs can restore an immediate operation while leaving the
same defect available to the next engineer, environment, or release. Repeated
manual Cloud Run corrections demonstrated that configuration duplicated outside
its authoritative template can pass review yet fail only after a revision is
created. That pattern increases cost, weakens evidence, and turns operator memory
into an undocumented dependency.

## Decision

MarketingLabAI applies Durable Remediation. When a failure exposes an underlying
architecture, configuration, delivery-workflow, security, or governance
weakness, engineering must correct the authoritative source and add automated
prevention whenever a durable solution is reasonably achievable.

For controlled deployment, the tracked manifest template, repository renderer,
application configuration contract, PowerShell 5.1 preflight, and CI validation
form one versioned deployment contract. Manual reconstruction of that contract
is refused.

## Enforcement

- Classify the failure and identify its authoritative source.
- Correct the source rather than only the observed instance.
- Add a regression test or deterministic gate that detects recurrence.
- Keep evidence free of secret values and bind it to the exact commit.
- Preserve authorization, privacy, tenant, cost, and public-access boundaries.
- Record unresolved durable work in the risk or technical-debt register.

## Temporary containment

Containment is allowed only to reduce immediate harm, cost, or exposure. It must
be explicitly temporary, preserve existing controls, record evidence, identify
an owner and durable follow-up, and obtain any separately required authority. It
cannot close the defect, story, risk, technical debt, or quality gate.

## Consequences

Delivery may pause longer at the first occurrence of a defect, but the fix
becomes repeatable, reviewable, and enforceable. Passing a manual command is no
longer sufficient proof of deployment readiness. Public access, application
deployment, invitations, billing, publishing, real-customer data, and real-data
learning remain governed by their existing separate decisions.
