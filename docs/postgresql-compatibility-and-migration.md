# PostgreSQL Compatibility and Migration Runbook

## Observational schema readiness

Increment B2 authenticates the versioned
`earthonox.marketinglabai.schema-manifest.v1` manifest before comparing live
catalog metadata. Readiness covers tables, ordered columns, provider-normalized
types, nullability, defaults, explicit indexes, primary and unique constraints,
foreign keys, check constraints, triggers, and exact legacy migration
version/description identities. Historical migration timestamps are not treated
as fabricated cryptographic evidence; the canonical manifest itself carries a
deterministic SHA-256 checksum.

SQLite inspection opens an existing file in read-only/query-only mode and
returns a structured `database_file` failure without creating a missing file or
parent directory. PostgreSQL inspection uses `information_schema` and
`pg_indexes` catalog reads. Neither readiness path applies DDL, repairs schema,
acquires the migration lock, or changes migration numbering. Explicit bootstrap
and reconciliation remain separately owned lifecycle operations.

## Implemented boundary

- `MLAI_PERSISTENCE_BACKEND=postgresql` selects the canonical PostgreSQL adapter.
- `MLAI_DATABASE_URL` is required and must be supplied through Secret Manager in
  hosted environments; credentials never belong in Git, evidence, logs or packages.
- Canonical schema generation derives the complete current table and index set from
  the repository schema source, including the tenant foreign-key boundary added to
  the migrated `brands` table. Rehearsal expectations use that same source rather
  than a hard-coded table count.
- Repository SQL uses one adapter boundary for placeholders, UTC timestamps and
  conflict-safe inserts. PostgreSQL integrity errors retain the established
  repository conflict behavior.
- Database instances expose a single-flight `ensure_initialised()` lifecycle used
  by application composition. Repository constructors are lifecycle-neutral and
  never apply DDL. Only successful schema application is cached. Explicit
  `bootstrap_database()` supports standalone tools and tests; `initialise()` remains
  the migrator-owned reconciliation boundary.
- PostgreSQL reconciliation holds transaction-scoped `pg_advisory_xact_lock` for
  the stable SHA-256-derived namespace
  `earthonox.marketinglabai.schema-migration.v1`. Lock acquisition has a five-second
  transaction-local timeout, and the lock is retained through commit or rollback.
  Waiting initializers recheck readiness under the lock and skip duplicate DDL.
- Hosted runtime composition is readiness-only. A dedicated migration principal
  owns DDL; runtime and readiness principals must not silently repair schema.
- SQLite reconciliation uses `BEGIN IMMEDIATE`, the existing WAL configuration and
  bounded busy timeout to serialize writers across processes without lock files.
- Readiness evaluation is observational: it verifies the canonical table set and
  migration versions without applying DDL or repairing an incomplete target.
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

### Local session-lifecycle rehearsal harness

`python -m tools.postgresql_rehearsal` runs the focused live PostgreSQL session
contracts against the loopback-only database named by `MLAI_DATABASE_URL`. The
database name must match `mlai_rehearsal` or an explicitly disposable
`mlai_rehearsal_*` name. The operator must provision that database as empty; the
harness never requires cluster-wide `CREATEDB` authority and refuses a missing or
non-empty target. Empty-target inspection covers non-system schemas, tables, views,
materialized views, sequences, routines and user-defined types. `localhost` is
accepted only when every resolved address is loopback-local. Each test resets only
the disposable target's `public` schema and registers the same reset as cleanup
before application composition. The harness derives table and migration expectations
from the canonical schema builders, applies bounded connection, statement and lock
timeouts, streams redacted tracebacks, and drops and independently verifies absence
of the exact disposable database after success, failure or timeout. It never changes
PostgreSQL server configuration and is not a production or managed-backup rehearsal.

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

## Managed-provider strategy

ADR-0048 locks PostgreSQL as the canonical durable datastore for hosted
Earthonox runtime. Google Cloud SQL for PostgreSQL remains the initial managed
production implementation. AlloyDB for PostgreSQL is reserved as a future
evidence-triggered scale option. The current implementation remains the
repository database factory and `psycopg` PostgreSQL adapter. SQLAlchemy and
Alembic are not approved at this stage.
