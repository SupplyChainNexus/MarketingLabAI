# ADR-0048: PostgreSQL Managed Provider Strategy

Status: Accepted

## Context

ADR-0030 refused Cloud Run deployment over replaceable SQLite storage.
ADR-0031 selected PostgreSQL through the canonical database factory and recorded
controlled local and Cloud SQL PostgreSQL 18 synthetic evidence. ADR-0032 bound
the private synthetic deployment contract to Cloud Run, Secret Manager, the
dedicated runtime identity and the evidenced Cloud SQL PostgreSQL target.

## Decision

Earthonox uses PostgreSQL as the canonical durable datastore for hosted runtime.
Google Cloud SQL for PostgreSQL remains the initial managed production
implementation.

AlloyDB for PostgreSQL is reserved as an evidence-triggered future scale option.
It is not adopted merely because it is more powerful.

The approved implementation remains the current repository/database-factory
architecture using `psycopg` and the PostgreSQL adapter. SQLAlchemy and Alembic
are not approved by this ADR.

The portability objective is reasonable PostgreSQL portability, not absolute
vendor neutrality. Provider-specific infrastructure concerns stay outside core
domain logic where practical.

## Consequences

- ADR-0031 remains authoritative for PostgreSQL compatibility and migration evidence.
- Cloud SQL remains the current managed PostgreSQL provider until a separately approved evidence-based migration story changes it.
- AlloyDB or another PostgreSQL provider may be evaluated only when a concrete Earthonox requirement justifies it.
- Changing provider or Cloud SQL target requires refreshed compatibility, tenant-isolation, backup/restore, Cloud Run connectivity, Secret Manager, cost and release-control evidence.
- SQLite-to-PostgreSQL translation heritage remains tracked technical debt.
- This ADR authorizes no cloud resource creation, database provisioning, IAM mutation, Secret Manager mutation, deployment, migration execution, production-data operation or release-state modification.