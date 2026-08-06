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

## Consequences

No Google API, Cloud SQL instance, build, deployment, external invitation or real
data is authorized by this decision. A live failure must be classified and
remediated before the unchanged gate is rerun. Founder authorization remains
necessary after all external evidence passes.
