# ADR-0020 — Founder Design Partner Signup and Tenant Claiming

## Status

Accepted

## Decision

Strand Auto Parts and Velani Wholesale are approved Founder Design Partner
candidates. Their accounts will not be manually pre-created. Each owner must
complete trusted authentication, present a business-specific invitation, and
accept the privacy and synthetic-data boundaries.

Tenant and initial admin membership creation is atomic. Claims are retry-safe
for the same identity and closed to another identity after ownership exists.
Invitation plaintext remains outside source control. Free full-feature founder
entitlement remains independent from real-data activation.

## Consequences

The signup journey becomes evaluable without fabricated identity subjects.
Customer-facing signup is not ready until an external identity provider is
selected, deployed, and rehearsed. The customer pilot remains founder-frozen.
