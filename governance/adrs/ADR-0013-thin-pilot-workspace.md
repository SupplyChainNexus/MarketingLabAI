# ADR-0013 - Thin Pilot Workspace

## Status

Accepted

## Date

2026-08-05

## Context

MarketingLabAI's secure pilot API was executable but still required engineering
support. The first workspace must make the governed journey understandable
without creating a second application path, exposing persistence, weakening
approval, or implying production readiness.

## Decision

Adopt a thin, framework-neutral WSGI workspace that serves same-origin HTML,
CSS, and JavaScript and delegates every operation to `PilotApiService` through
the pilot JSON contract. Presentation code may not import canonical
repositories, `CanonicalApplication`, or AI provider models.

The workspace guides synthetic onboarding, missing-context review, Campaign
Plan and Marketing Brief review, revision, explicit approval, governed
generation, independent compliance review, limitation disclosure, audit
metadata, and safe JSON export. Generation remains disabled unless the API says
both current governance versions are approved.

Extend the API with transport-safe onboarding, workflow-review, and revision
operations because those capabilities are required by the customer journey.
Authorized application services own domain construction, tenant checks, and
immutable successor creation. Export authorization remains separate from local
file download and never means publication.

Use strict same-origin browser security headers and avoid third-party assets.
The temporary credential field is permitted only for synthetic pilot testing.
Live identity sessions, hardened hosting, secrets, rate limits, observability,
backup, recovery, and data-handling approval remain MLAI-027.6 release gates.

## Alternatives considered

### Let the browser call repositories or SQLite directly

Rejected because it would create an unaudited tenant-boundary bypass.

### Introduce a JavaScript framework and build pipeline

Deferred because the small pilot journey does not justify a new dependency or
deployment toolchain before operational requirements are selected.

### Allow generation and warn about missing approvals afterward

Rejected because approval is a security and governance precondition, not a UI
hint.

### Add direct social or advertising publishing

Rejected because connector execution is explicitly deferred and safe export is
the approved pilot boundary.

## Consequences

The secure vertical slice is now usable as a guided synthetic workflow while
retaining one canonical application path. The UI remains intentionally thin and
replaceable. It cannot be deployed with real customer data until MLAI-027.6
closes the operational and privacy gates.

## Validation

Synthetic tests cover workspace assets and security headers, dependency
direction, verified onboarding, missing context, safe review contracts,
revision and stale-version conflict, reapproval, approval-gated generation,
independent compliance results, limitations, audit metadata, cross-tenant
denial, and export without publishing.
