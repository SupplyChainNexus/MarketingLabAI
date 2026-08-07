# ADR-0031 — Repository-Wide PostgreSQL Compatibility and Migration

## Decision

The controlled hosted runtime selects PostgreSQL through the canonical database
factory. Existing repository contracts remain stable while the adapter translates
the bounded placeholder, timestamp and conflict syntax used by the application.
The PostgreSQL schema is deterministically derived from the canonical 21-table
schema, with tenant dependencies created first and `brands.tenant_id` enforced by
a database foreign key.

SQLite-to-PostgreSQL migration is synthetic-only, transactional on the target,
preserves and hashes the source, copies dependency-ordered tables, and requires
exact row-count parity. Any mismatch rolls back the target transaction. Cutover is
a reversible configuration decision; this story does not delete or mutate the
SQLite source.

Local compilation, schema, adapter, repository-regression and synthetic-copy
evidence cannot substitute for a live PostgreSQL rehearsal. The durable-adapter
gate remains false until a traceable, commit-bound live migration, tenant-isolation,
backup and isolated-restore result is recorded. PostgreSQL recovery must use the
approved managed-database process; the SQLite backup CLI refuses that backend.

## Evidence closure

The live gate subsequently passed at correction commit `b09055a` against local
PostgreSQL 18 and a controlled synthetic Cloud SQL PostgreSQL 18 instance in
`africa-south1`. Evidence covers schema initialization, exact transactional
migration parity, tenant isolation, 17 canonical application contracts, managed
backup, isolated restore and verified cleanup. Failures were preserved, classified
and remediated before unchanged gates were rerun. Raw evidence and credentials stay
outside Git; only sanitized references and hashes are tracked.

## Consequences

No Google API was authorized by the original engineering decision. The later,
separately approved controlled Cloud SQL rehearsal supplied external synthetic
evidence only and did not authorize application deployment or real data.

The durable-adapter external-evidence gate is passed for controlled synthetic use.
The retained Cloud SQL instance is infrastructure evidence, not application
deployment or production activation. Build, deployment, external invitations,
public signup, billing, publishing, real-customer data and real-data learning remain
unauthorized. Founder authorization remains necessary for each applicable boundary.
