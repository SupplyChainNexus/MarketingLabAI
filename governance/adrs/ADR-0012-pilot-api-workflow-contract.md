# ADR-0012 - Pilot API and Workflow Contract

## Status

Accepted

## Date

2026-08-05

## Context

The secure pilot needs a stable customer-facing application contract without
letting transport code bypass tenant authorization, lifecycle governance, or
provider neutrality. Retried approval and generation requests can otherwise
create extra immutable versions or duplicate paid AI work.

## Decision

Adopt a transport-neutral `PilotApiService` over
`AuthorizedTenantApplication`. Expose only context, governed generation,
Campaign Plan approval, Marketing Brief approval, and export authorization.
Public contracts contain JSON-safe values and never persistence or AI-provider
domain objects.

Use a minimal standards-based WSGI JSON adapter for the first contract. This
avoids selecting a web framework or deployment platform before the operational
story. A requested tenant header is routing input only; a trusted identity
adapter and active membership establish the tenant-bound session.

Generation must reference an approved Campaign Plan version and approved
Marketing Brief version for the same tenant and brand. Approvals require an
expected current version. Lifecycle mismatches return conflict responses.

Require identity-scoped idempotency keys for generation, approvals, and export
authorization. Persist the canonical request hash and successful response in
SQLite migration 12. Exact retries replay the response; key reuse with changed
input is rejected.

## Dependency direction

WSGI transport depends on pilot contracts and the pilot service. The pilot
service depends on the external identity boundary and authorized application
facade. Only internal application services may reach canonical repositories.
No dependency points from domain models toward HTTP, WSGI, or provider SDKs.

## Alternatives considered

### Expose CanonicalApplication repositories to endpoint handlers

Rejected because handlers could bypass tenant and resource authorization.

### Trust `X-Tenant-ID` as authorization proof

Rejected because possession of an identifier does not establish membership.

### Select FastAPI, Flask, or a hosting platform now

Deferred because framework and runtime operations belong to MLAI-027.6. WSGI
keeps the contract executable with the standard library.

### Allow generation without approved governance references

Rejected because it breaks the pilot's human-approval boundary.

## Consequences

The workspace can build on a narrow, authenticated, retry-safe contract. Stale
approvals and unapproved generation fail explicitly. A future deployment must
still choose a hardened server, live identity adapter, rate limits, privacy-safe
logging, and secret configuration before real customer data is allowed.

## Validation

Synthetic end-to-end tests cover authentication, cross-tenant denial, missing
context, approved generation, lifecycle conflicts, identity-scoped replay,
changed-request conflicts, and idempotent schema initialization.
