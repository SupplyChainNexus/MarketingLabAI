# ADR-0028 — Design-Partner Acceptance Rehearsal

## Status

Accepted for controlled synthetic rehearsal. External partner activity and real
customer data remain frozen.

## Decision

Acceptance is assessed separately for each approved partner tenant. The
authenticated tenant must match the registry entry, the combined production
security and operational gate must pass, and the current synthetic privacy
notice and boundary must be accepted.

Seven end-to-end scenarios require immutable evidence bound to the deployed
commit and environment: signup/session, privacy boundary, tenant isolation,
strategy workflow, governed generation/compliance, logout/recovery/support, and
browser accessibility/usability. Request-supplied booleans are not acceptance
evidence. Missing, expired, wrong-environment, wrong-commit, or latest failed
evidence blocks the assessment.

## Consequences

Strand Auto Parts and Velani Wholesale pass independently. A passed rehearsal
permits a founder activation assessment only. It does not authorize external
invitations, real data, public signup, production activation, billing,
publishing, learning, or market-validation claims.
