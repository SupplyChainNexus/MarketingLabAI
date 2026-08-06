# MLAI-031 — Controlled Pilot Hosting

## MLAI-031.1 — Controlled Hosting and Durable Pilot Persistence

Status: active

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
