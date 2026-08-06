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

Status: engineering complete; live PostgreSQL evidence blocked

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
- A traceable live migration and isolated restore remain required before the
  durable-adapter hosting gate can pass.

### Gate effect

Local PostgreSQL compatibility engineering and controlled synthetic rehearsal are
authorized. Infrastructure mutation, cloud build, deployment, invitations and real
data remain frozen and are not self-authorized.
