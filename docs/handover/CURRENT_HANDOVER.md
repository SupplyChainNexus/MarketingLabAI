# MarketingLabAI Current Handover

## Checkpoint

- Branch: `feature/tenant-architecture`
- Installation baseline: `59cf915`
- Remote state before this story: synchronized with `origin/feature/tenant-architecture`
- Last completed epic: MLAI-027 Secure Pilot Vertical Slice
- Last completed story: MLAI-027.6 Pilot Operations and Release Gate
- Validation target: operations/workspace/API/security, continuity, and full regression

## Product direction

MarketingLabAI remains a Marketing Intelligence Operating System and the AI
Marketing Department for growing businesses. PDR-0001 through PDR-0003 remain
authoritative. The public brand decision remains deferred; no product rename
was performed.

## Current implementation

MLAI-027.1 through MLAI-027.6 form one canonical synthetic journey over SQLite,
tenant authorization, external identity boundaries, short-lived hashed
sessions, a retry-safe pilot API, a thin workspace, independent compliance,
privacy-safe logs, rate limits, health/readiness, tested backup and restore,
CI, and operational runbooks.

Waitress is the supported Windows-compatible WSGI runtime behind TLS. Runtime
composition selects external identity and AI registry factories through
environment configuration. The browser no longer accepts a credential; it uses
a Secure/HttpOnly/SameSite server session and CSRF proof.

## Release state

The synthetic operational gate may pass. The customer pilot remains explicitly
frozen by the founder. Configuration rejects real-customer-data enablement, and
readiness reports `private_customer_pilot_authorized=false`. Do not load real
customer data, select a customer, or begin outreach as a consequence of this
story.

Before reconsideration, require a customer-facing checkpoint, a selected live
identity deployment, controlled membership bootstrap, privacy/legal choices,
deployment and restore rehearsal, support ownership, and a new founder-approved
decision. Remind the founder at that point, as requested.

## Remaining constraints

- The actual identity vendor and hosting provider remain intentionally
  unselected while the pilot is frozen.
- Process-local rate limiting is suitable only for the single-instance pilot.
- Legacy CLI/runtime paths remain compatibility boundaries, not pilot authority.
- Generated campaign artifacts still use an injected persistence boundary.
- Direct publishing, billing, public self-service, learning, attribution,
  Calendar, full Positioning, Strategy, and Executive Intelligence remain
  deferred according to existing authority.

## Next engineer's first action

Run the complete MLAI-027.6 validator and review its release-gate evidence. Then
apply the Rabbit Rule and current product roadmap to select the next build
increment without treating synthetic evidence as customer learning or silently
unfreezing the pilot.
