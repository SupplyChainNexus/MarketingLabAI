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

## External evidence closure

The unchanged live gate passed against local PostgreSQL 18 and the controlled
synthetic Cloud SQL PostgreSQL 18 instance in `africa-south1`, bound to correction
commit `b09055a`. Evidence verifies 21 tables, migrations 1 through 17, exact
source/target parity, preserved source SHA-256, 17 application contracts with zero
failures or errors, managed backup, isolated local restore, and cleanup of temporary
contract and restore databases.

Sanitized evidence is indexed by the external manifest
`MLAI-031.2_external_evidence_SHA256_b09055a.txt` (SHA-256
`3f2c1e2788f46cc68d3e0873551f39ec0ed77a620cc9c5f0353edcc3a2a68cab`).
The post-rehearsal cleanup addendum SHA-256 is
`82c7ed004fc975968f26bd9e815178cd592e97829ba2be513cc9d5e11ba2156e`.
Raw transcripts, dumps and credentials remain outside Git.

The durable-adapter external-evidence gate is passed. Cloud application build and
deployment, Velani invitation, public signup, billing, publishing, real-customer
data, production activation and real-data learning remain frozen.
