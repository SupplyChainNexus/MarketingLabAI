# MLAI-031.18C Session Lifecycle Threat Model

## Scope and assets

This threat model covers the private-pilot exchange of a validated provider ID
token for an Earthonox-owned opaque server session. It protects identity
binding, tenant authorization, session and CSRF authority, PostgreSQL session
state, and privacy-safe lifecycle evidence. The fixed private-pilot limits are
15 minutes idle and 60 minutes absolute lifetime.

## Trust boundaries

### Identity and provider-token boundary

Google Cloud Identity Platform authenticates the identity. Earthonox validates
the provider credential through the provider-neutral adapter only when creating
a session. The browser clears the ID token after exchange. Provider credentials
and refresh credentials are never written to Earthonox persistence or audit
evidence. Provider authentication is not tenant authorization.

### Opaque server-session boundary

The browser receives a random opaque session identifier in an HttpOnly,
SameSite=Strict cookie and separate CSRF material. `pilot_sessions` stores only
keyed HMAC digests. `created_at` is the original trusted creation anchor,
`expires_at` is the current idle deadline, and `revoked_at` permanently removes
authority. A successor preserves the original `created_at`; normal renewal
cannot move the absolute deadline.

### Tenant authorization boundary

The session binds provider, subject and tenant. A client-supplied tenant ID is
routing and context only. Every use still revalidates an active server-side
membership, and downstream authorization remains default deny with current
role, operation and resource ownership checks. Knowledge of a tenant or object
identifier is never proof of authority.

## Lifecycle threats and controls

| Threat | Required control |
|---|---|
| Stolen or replayed cookie | Opaque random values, keyed hashes at rest, secure cookie attributes, idle and absolute expiry, rotation and revocation. |
| CSRF on renewal or logout | Require the session-bound CSRF value, session cookie and tenant context. |
| Unlimited sliding lifetime | Preserve original `created_at`; cap every successor at `created_at + 60 minutes`. |
| Competing renewal | Conditional compare-and-swap revokes exactly one active predecessor; only that transaction inserts a successor. |
| Predecessor reuse | Authentication and CSRF queries require `revoked_at IS NULL`; successful rotation never clears predecessor revocation. |
| Renewal during membership change | Renewal locks/revalidates the membership row before compare-and-swap; membership role or active-state changes invalidate matching sessions in the change transaction. |
| Caller-selected tenant escalation | Require session tenant match, current membership and downstream ownership and permission checks. |
| Audit leakage | Record only event, identity and tenant audit dimensions, outcome, safe scope or reason, count and time. |
| Audit failure during creation or rotation | Write sanitized audit evidence in the session transaction; failure rolls back creation or restores the still-active predecessor and discloses no replacement cookie. |

## State transitions

- `created -> active`: provider authentication and tenant authorization succeed;
  idle deadline is creation plus 15 minutes.
- `active -> rotated`: CSRF-protected `PUT /v1/pilot/session` wins the atomic
  compare-and-swap; the predecessor is revoked and a fresh identifier and CSRF
  value plus sanitized audit evidence are inserted with the original creation
  anchor. All parts commit or roll back together.
- `active -> revoked`: logout, identity-and-tenant revocation, or a supported
  membership role or active-state change sets `revoked_at`.
- `active -> expired`: either `expires_at` is reached or 60 minutes have elapsed
  since original `created_at`.
- `revoked/expired/predecessor -> active` is forbidden. Fresh provider
  authentication creates a new lifecycle instead.

## Supported invalidation hooks

`IdentityRepository.save_membership()` is the current role and active-state
mutation boundary used by the authorized membership application facade. A
change invalidates active sessions matching provider, subject and tenant in the
same transaction. Per-use membership revalidation remains mandatory.

`PilotSessionProvider.revoke()` supports current-session logout.
`PilotSessionProvider.revoke_all()` supports identity-and-tenant revocation at
the service boundary. There is no dedicated administrator HTTP endpoint for
the latter in this story.

## Explicitly deferred gaps

The repository has no current event boundary for provider-global account
disablement, password recovery, MFA or factor changes, provider refresh-token
revocation, cross-tenant or global identity invalidation, or security-engine
and suspicious-activity events. MLAI-031.18C does not claim these controls.
They remain separately threat-modelled work, as do provider revocation
orchestration and a governed administrator revocation API.

## Privacy-safe evidence contract

Lifecycle audit records may contain event name, tenant ID, provider and subject
audit dimensions, result, non-secret reason or scope, affected count and
timestamp. They must never contain plaintext session IDs or token hashes. CSRF values or hashes are never recorded.
Cookies, provider ID tokens, and provider credentials are also excluded. Refresh
credentials, secrets, and submitted customer content are likewise excluded.

Lifecycle audit insertion uses the same database transaction as session
creation or renewal. Failure creates no session during login; during renewal it
rolls back predecessor revocation and successor insertion. No replacement
identifier or CSRF material is returned in either case.

## Assurance boundary

The focused tests written for this story are test specifications, not execution
evidence, and are intentionally not run under the story authority. This
document claims no validation, rehearsal, cloud configuration, provider
revocation, deployment, release, customer activation, MFA, edge enforcement or
operational evidence.
