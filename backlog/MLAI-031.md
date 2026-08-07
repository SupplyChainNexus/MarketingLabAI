# MLAI-031 — Controlled Pilot Hosting

## MLAI-031.1 — Controlled Hosting and Durable Pilot Persistence

Status: complete

### Purpose

Prevent an unsafe SQLite deployment and define the evidence-backed Cloud Run
and durable PostgreSQL boundary for the Velani pre-activation environment.

### Acceptance

- Cloud Run with SQLite is deterministically refused.
- PostgreSQL compatibility requires explicit complete evidence.
- Secrets are references, never values in source or packages.
- Scale, resource and cost targets are bounded.
- A founder decision remains necessary after engineering readiness.
- Build, deployment, invitations and real data remain unauthorized.

### Follow-on

Complete repository-wide PostgreSQL compatibility, synthetic migration,
backup/restore and cost evidence before enabling APIs or building an image.

## MLAI-031.2 — Repository-Wide PostgreSQL Compatibility and Migration

Status: complete; live local and controlled Cloud PostgreSQL evidence passed

### Purpose

Provide a canonical PostgreSQL runtime, deterministic schema and reversible,
transactional synthetic migration without claiming that local tests prove a live
managed database.

### Acceptance

- Runtime configuration selects SQLite or PostgreSQL through one factory.
- All 21 canonical tables and indexes generate in dependency order.
- Tenant boundaries, timestamps, placeholders, conflict handling and repository
  integrity semantics remain enforced.
- Synthetic migration preserves the source and requires exact per-table parity.
- PostgreSQL backup/restore cannot accidentally use SQLite recovery tooling.
- Traceable local and controlled Cloud PostgreSQL migration, contract, backup,
  isolated-restore and cleanup evidence is recorded against commit `b09055a`.

### Gate effect

The durable PostgreSQL adapter evidence gate is passed for the controlled synthetic
environment. The retained Cloud SQL instance and synthetic primary database do not
authorize application deployment, invitations, public signup, billing, publishing,
real-customer data, production activation or real-data learning. Those boundaries
remain frozen and require separate founder decisions.
