# ADR-0032 — Controlled Private Synthetic Application Deployment

## Decision

Deploy the canonical application only as an IAM-authenticated, scale-to-zero Cloud
Run service using a digest-pinned container, dedicated least-privilege runtime
identity, Secret Manager bindings and the evidenced synthetic PostgreSQL instance.
The non-root container starts the existing application factory; no parallel
application path is introduced.

SQLite, mutable image tags, embedded credentials, broad service-account reuse, a
different Cloud SQL target and unauthenticated invocation are refused.

## Consequences

Engineering readiness never self-authorizes cloud mutation. External evidence is
required for APIs, IAM, secrets, immutable build, authenticated access, health,
rollback, recovery and cost. External invitations, public signup, real-customer
data, billing, publishing and real-data learning remain frozen.
