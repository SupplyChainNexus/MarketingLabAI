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

## MLAI-031.7: Canonical private ingress correction

- Correct the canonical template from public ingress to
  `internal-and-cloud-load-balancing`.
- Enforce one shared manifest/bootstrap contract and CI regression suite.
- Preserve the 9630fad run and image as incomplete, non-deployable history.
- After commit and CI, create a fresh image and observational release run.

## MLAI-031.8 — Unified Release Control Plane

Status: implemented, committed, CI verified and adopted

### Purpose

Replace fragmented release scripts with one repository-owned operator path
while preserving the gate catalogue, observational ledger and independent
zero-trust admission authority.

### Acceptance

- One thin PowerShell 5.1 launcher invokes one pinned Python control plane.
- State uses a stable product-named root with no MLAI story number.
- Status, plan, approval, apply, resume and verify share one release identity.
- Plans are deterministic and approvals bind the exact plan digest.
- External evidence is unified, indexed, atomically written and SHA-256 checked.
- Repeated or interrupted application safely resumes without duplicate gates.
- The legacy controller remains observational and has no supported direct UI.
- The verified `2239244` state is adopted without rebuilding or granting
  deployment authority.
- Cloud mutation and Binary Authorization enforcement remain separately gated.

## MLAI-031.9 — Permanent Read-Only Cloud Preflight

Status: implementation in validation

### Purpose

Extend the paved release path through `CLOUD_PREFLIGHT_PASSED` without reviving
temporary scripts or granting deployment authority.

### Acceptance

- The Python control plane owns all cloud-preflight orchestration.
- Exact read-only `gcloud` verbs are allowlisted and invoked without a shell.
- Project, API, identity, artifact, database, secret-access and target-service
  observations are pinned, minimized, hashed and indexed.
- Secret values are never accessed or emitted.
- Public, ambiguous, missing or drifted prerequisites fail closed.
- One deterministic plan, one approval and idempotent apply/resume remain the
  only supported operator journey.
- Installation, validation and CI perform no cloud operation.
- Revision creation, deployment, IAM mutation, traffic and admission authority
  remain unsupported and separately gated.

## MLAI-031.10 — Provenance-Bound Windows Cloud CLI Recovery

Status: founder-authorized durable repair

### Purpose

Repair the actual Windows Python-to-Cloud-SDK boundary, prevent changed
executor code from reusing an old approval, and provide one safe recovery path
for the interrupted cloud-preflight operation.

### Acceptance

- The Windows `.cmd` adapter is explicit and tested with a space-containing path.
- Account, configuration, project, quiet mode and JSON format are adapter-owned.
- A same-adapter doctor passes before any operation journal is created.
- Plans bind the clean repository commit, control-plane version, executor hash
  and platform adapter.
- Missing or changed executor provenance fails closed.
- Formal supersession preserves the old operation without changing a gate or cloud.
- Resume returns one safe next action and never silently reuses stale approval.
- Installation and validation perform no cloud operation or release-state change.

## MLAI-031.11 — Deterministic Private Revision Preparation

Status: founder-authorized durable preparation

### Purpose

Prepare the first `REVISION_CREATED` mutation boundary without executing it.
The operator receives one manifest, one command intent and one hash-indexed
revision-preparation record before any cloud mutation can be separately
approved.

### Acceptance

- Preparation is available only after `CLOUD_PREFLIGHT_PASSED`.
- The rendered manifest is written outside the repository under ToolkitTemp.
- The manifest is bound to the verified release digest, source commit, private
  origin, runtime service account, Cloud SQL attachment, private ingress,
  resource bounds and Secret Manager bindings.
- Secret Manager payloads are not read and public IAM principals remain
  prohibited.
- The command intent is recorded as `gcloud run services replace` with pinned
  region and managed platform, but is not executed by preparation.
- The revision-preparation record has an integrity sidecar and binds the
  release index, observational event head and executor provenance.
- Installation, validation and CI perform no Cloud CLI execution, cloud
  mutation, deployment, traffic routing, rebuild or admission-authority action.

## MLAI-031.12 — First-Service Origin Bootstrap Correction

Status: founder-authorized durable repair

### Purpose

Correct the private revision-preparation contract for the first Cloud Run
service creation. A real Cloud Run `status.url` cannot exist before the service
exists, so first-service preparation must not require a guessed origin.

### Acceptance

- A named first-bootstrap origin is allowed only when cloud preflight proved the
  canonical service is absent and the revision plan is `FIRST_PRIVATE_REVISION`.
- Existing-service revision preparation still requires the actual Cloud Run URL.
- Prepared revision evidence records whether origin reconciliation is required.
- Startup and smoke gates must not pass until the real service URL is observed
  and reconciled.
- The correction performs no Cloud CLI execution, cloud mutation, release-state
  modification, deployment or rebuild.
