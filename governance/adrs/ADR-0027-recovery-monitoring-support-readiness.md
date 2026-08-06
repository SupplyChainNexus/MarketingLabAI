# ADR-0027 — Recovery, Monitoring and Support Readiness

## Status

Accepted for controlled synthetic rehearsal. Real-customer activation remains frozen.

## Decision

Security and operational readiness may not be established by unsupported
configuration booleans. Every rehearsal result is stored as an immutable record
bound to an environment, deployed Git commit, operator, observation time,
expiry time, and sanitized evidence reference. Failed results require a failure
classification and remediation and remain in history.

Operational readiness requires verified backup, restore, rollback, alert,
incident-response, support-owner, and response-target evidence. Evidence for a
different environment or commit, expired evidence, and a latest failed result
remain blockers. Privacy-safe signal counters cover readiness, authentication,
rate-limit, database, backup, and server failures without customer content.

The top-level founder-assessment decision requires the base release gate,
production identity/security readiness, and recovery/monitoring/support
readiness together.

## Consequences

Controlled synthetic rehearsal is required, not merely permitted on paper.
Passing readiness permits MLAI-030.6 acceptance rehearsal only. It never
authorizes real data, external invitations, public signup, production customer
access, billing, publishing, or real-data learning. Founder approval remains a
separate later decision.
