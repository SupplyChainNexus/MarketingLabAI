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

## MLAI-031.3 — Controlled Private Synthetic Application Deployment

Status: engineering package ready; external deployment evidence pending

### Purpose

Deploy one IAM-authenticated, scale-to-zero synthetic Cloud Run service through
the canonical runtime without public access or real-customer data.

### Acceptance

- Container startup uses the canonical environment-composed WSGI application.
- The image is non-root, digest-pinned and excludes local data and secrets.
- A dedicated least-privilege runtime identity replaces broad account reuse.
- Cloud SQL connector and four external Secret Manager bindings are exact.
- Minimum instances are zero and maximum instances are one.
- IAM denial, health, rollback, recovery, tenant isolation and cost are evidenced.
- Invitations, public signup, billing, publishing, real data and learning stay frozen.

### Durable deployment correction

- The tracked Cloud Run template is the only deployment configuration authority.
- A repository renderer validates every environment name, secret reference,
  private-IAM fragment, immutable image package, and bounded resource setting.
- PowerShell 5.1 and CI execute the same no-mutation preflight.
- Failed manual revisions are retained as evidence and do not authorize another
  one-off patch; ADR-0033 Durable Remediation governs recurrence prevention.

## MLAI-031.4 — Progressive Release Automation

Status: engineering implementation complete; external execution not authorized

- Lock the deployment lifecycle into one dependency-ordered gate catalog.
- Provide one PowerShell 5.1 operator entry point with status and safe-next-step output.
- Record append-only, hash-chained, commit- and image-bound release evidence.
- Refuse skipped gates, in-repository run data, unclassified failures, and
  unauthorized mutation claims.
- Execute the same no-mutation validation in CI.

## MLAI-031.5 — Zero-Trust Software-Supply-Chain Foundation

Status: founder-authorized repository foundation; cloud enforcement pending

- Supersede controller state as release authority.
- Lock the exact run, commit, image digest, gate, policy and timestamp binding.
- Add a versioned shadow policy and independent no-mutation verifier.
- Keep legacy runs and the 7e45958 artifact historical and non-deployable.
- Target SLSA Build Level 3, independent in-toto/DSSE gate signatures, RFC 3161
  timestamps, isolated final authorization and Cloud Run Binary Authorization.
- Keep API enablement, KMS, attestors, organization policy, deployment and
  traffic as separately authorized infrastructure stages.
