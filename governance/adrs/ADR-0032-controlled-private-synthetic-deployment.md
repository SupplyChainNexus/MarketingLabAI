# ADR-0032 — Controlled Private Synthetic Application Deployment

## Decision

Deploy the canonical application only as an IAM-authenticated, scale-to-zero Cloud
Run service using a digest-pinned container, dedicated least-privilege runtime
identity, Secret Manager bindings and the evidenced synthetic PostgreSQL instance.
The non-root container starts the existing application factory; no parallel
application path is introduced.

SQLite, mutable image tags, embedded credentials, broad service-account reuse, a
different Cloud SQL target and unauthenticated invocation are refused.

The tracked Cloud Run template is the single deployment configuration authority.
It must be validated and rendered by the repository-owned manifest generator.
Manually reconstructed environment-variable lists, secret aliases, service
names, identity factories, and resource bounds are refused because they can
drift from the tested application contract.

## Consequences

Engineering readiness never self-authorizes cloud mutation. External evidence is
required for APIs, IAM, secrets, immutable build, authenticated access, health,
rollback, recovery and cost. External invitations, public signup, real-customer
data, billing, publishing and real-data learning remain frozen.

The pre-deployment gate validates the complete template contract in CI without
reading secret values or mutating Cloud resources. A failed revision is retained
as evidence and must lead to Durable Remediation of the authoritative source,
not another ad hoc deployment patch.
