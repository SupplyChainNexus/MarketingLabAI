# PostgreSQL Compatibility and Migration Runbook

## Implemented boundary

- `MLAI_PERSISTENCE_BACKEND=postgresql` selects the canonical PostgreSQL adapter.
- `MLAI_DATABASE_URL` is required and must be supplied through Secret Manager in
  hosted environments; credentials never belong in Git, evidence, logs or packages.
- Canonical schema generation covers all 21 tables and indexes, including the tenant
  foreign-key boundary added to the migrated `brands` table.
- Repository SQL uses one adapter boundary for placeholders, UTC timestamps and
  conflict-safe inserts. PostgreSQL integrity errors retain the established
  repository conflict behavior.
- Synthetic migration copies every table in one target transaction, verifies exact
  counts and proves the SQLite source hash did not change.

## Mandatory live synthetic rehearsal

Do not set `MLAI_DURABLE_ADAPTER_VERIFIED=true` from unit tests. Against an approved
empty PostgreSQL target bound to the exact candidate commit:

1. Initialise the schema and confirm all migration versions and indexes.
2. Load an invented multi-tenant SQLite fixture; record its SHA-256 and row counts.
3. Run the transactional migrator and compare every source/target table count.
4. Run the complete application, API, tenant-isolation, privacy, session, readiness
   and activation regressions against PostgreSQL.
5. Create a managed backup, restore it into a separate isolated target, repeat
   integrity and row-count checks, and record recovery time without customer data.
6. Classify and remediate every failure, then rerun the same gate.
7. Store only a sanitized, immutable evidence reference and the candidate commit in
   `MLAI_DURABLE_ADAPTER_EVIDENCE_REFERENCE`.

## Rollback and cutover

Before activation, rollback means keeping the hosted service on the previous
configuration and retaining the immutable SQLite source. Never overwrite the source
or restore into the active target during rehearsal. A failed copy rolls back its
target transaction. A future real-data cutover requires a separately approved
maintenance window, final delta plan, restore rehearsal and founder decision.

## Still blocked

There is no live PostgreSQL server in the local validation environment. Therefore
live adapter, migration, backup, restore, Cloud SQL cost and region evidence remain
open. Cloud build/deployment, Velani invitation and all real-data activity remain
frozen.
