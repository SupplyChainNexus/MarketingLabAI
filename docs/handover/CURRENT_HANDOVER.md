# MarketingLabAI Current Handover

## Checkpoint

- Branch: `feature/tenant-architecture`
- Installation baseline: `5d79691e95d757ff4383a6f24ecb595eacd64e7e`
- Starting state: clean at the MLAI-031.18C implementation baseline
- Last completed epic: MLAI-029 Marketing Strategy Intelligence
- Active epic: MLAI-031 Controlled Pilot Hosting
- Last completed story: MLAI-031.18C Threat Model and Server-Session Lifecycle Foundation
- Active story: MLAI-033.3 C5 Phase C integration is implemented locally against Migration 21; commit and push remain unauthorized

## Product direction

MarketingLabAI remains a Marketing Intelligence Operating System and AI
Marketing Department for growing businesses. PDR-0003 and the locked
six-story MLAI-029 sequence govern the Strategy increment.

## Current implementation

MLAI-027.1 through MLAI-027.6 provide the canonical application, verified
product context, tenant authorization, secure API, thin workspace, and
controlled operational release gate.

MLAI-028.1 through MLAI-028.5 provide approved, immutable Positioning
Intelligence and governed workflow context. MLAI-029.1 adds a provider-neutral
Strategy Intelligence domain with tenant- and brand-owned decisions, explicit
positioning references, separate evidence, assumptions, unknowns, confidence,
choices and non-choices, immutable lifecycle, human approval, and migration 15.

Approval requires verified evidence, at least one business objective, and the
exact referenced Positioning version to be approved for the same brand.

MLAI-029.2 adds deterministic situation synthesis over supplied Company,
Customer, Product, approved Positioning, and time-stamped user-supplied PESTLE
evidence. It returns traceable opportunities, constraints, risks, gaps, and
limitations without live research, opaque scoring, forecasts, or invented facts.

MLAI-029.3 validates measurable objectives and explicit strategic choices
against the same immutable Situation Report. The evaluator does not invent
baselines, targets, budgets, forecasts, or results.

MLAI-029.4 validates the minimum four-part marketing mix, optional service
extensions, objective-linked channel roles, and measurement coverage. It does
not invent pricing, budgets, forecasts, attribution, or results.

MLAI-029.5 composes current approved Strategy through the canonical application,
persists immutable Strategy references on Campaign Plans and Marketing Briefs,
and requires matching Strategy and Positioning references before governed AI
generation. Provider context and audit metadata retain exact version identity.

MLAI-029.6 adds a client-facing Strategy review to the same authorized
workspace and requires aligned current Positioning, Strategy, Campaign Plan,
and Marketing Brief versions for generation readiness. It also adds a
deterministic Founder Design Partner assessment. Strand Auto Parts is the
proposed first partner with full feature access and billing disabled, but the
assessment never authorizes real customer data.

MLAI-030.1 replaces manual account creation with authenticated, invitation-
controlled signup for Strand Auto Parts and Velani Wholesale. Each claim creates
an isolated tenant and admin owner atomically. Signup remains synthetic-only;
the external identity deployment and browser flow remain MLAI-030.2 blockers.

MLAI-030.2 initially selected Microsoft Entra External ID, then superseded that
choice before deployment after a formal free-first comparison. Google Cloud
Identity Platform is now selected and adds strict RS256 signature, project
issuer and audience, expiry, issued-at, authentication-time, and subject
validation behind the existing identity adapter. Google authenticates;
MarketingLabAI retains tenant membership, authorization, founder entitlement,
invitations and audit decisions. SMS, Front Door, premium add-ons, invitation
delivery and real customer data remain disabled. The existing Google Workspace
organization may administer the Cloud project, but its staff directory is not
the customer directory. A live Cloud project is not
required until offline validation succeeds.

The controlled Google project `marketinglabai-identity-dev` is now configured
for synthetic browser rehearsal. Google sign-in is enabled with an external
testing audience, controlled test users, exact loopback origin
`http://127.0.0.1:8080`, restricted Firebase browser-key referrers, and only the
Identity Toolkit and Token Service APIs. The application serves browser-safe
configuration, exchanges the Google credential for a project-audience Firebase
ID token, requires verified Google email claims, keeps the token in memory
only, and clears it after creating the existing hashed tenant-bound session.
Cloud Functions, password authentication, SMS, MFA, public signup, invitation
delivery, real customer data, and paid identity extensions remain disabled.

MLAI-030.3 adds a versioned, default-deny synthetic privacy policy for each
approved design-partner tenant. Signup now records the exact privacy notice and
data-boundary versions atomically with tenant ownership. Authenticated APIs
expose the current policy, identity-bound acceptance evidence, and deterministic
category decisions. Only enumerated invented synthetic categories are allowed.
Real-data retention and deletion periods remain unset, and every privacy
response keeps real-data activation false.

MLAI-030.4 adds bounded Google authentication age, current tenant-membership
revalidation for every session use, audited current-session and identity-wide
revocation, CSRF-protected logout, bounded request bodies, defensive response
headers, and deterministic production-security checks. Deployment and rehearsal
claims are accepted only as explicit boolean evidence. Missing evidence blocks
production-security readiness, and every report keeps real-data activation
false even when all checks pass.

MLAI-030.5 replaces unsupported readiness claims with immutable migration-17
evidence bound to environment, deployed commit, operator, timestamps, expiry,
and sanitized references. Failures require classification and remediation.
Recovery, alert, incident and support checks feed a deterministic operational
report, while privacy-safe signal counters expose alert state without customer
content. The top-level founder-assessment gate requires base, security and
operational readiness together and still keeps activation false.

The Repository Integrity Protocol is now locked for every future story:
baseline and scope verification, tracked/untracked/staged reporting, failure
classification, complete applicable quality gates, no remaining intended paths,
and clean local/remote synchronization are mandatory.

ADR-0023 now supersedes the narrow interpretation of story path allowlists with
the Constitution-Preserving Quality Mandate. Expected scope remains explicit,
but reversible evidence-backed improvements to correctness, security,
usability, accessibility, maintainability, testing, recovery and operational
clarity may include necessary adjacent paths when they are justified, tested,
documented and separately reported. Founder approval remains mandatory for
real data, live invitations, public activation, paid services, destructive or
irreversible changes, privacy boundaries and product-direction changes.

The first Governance Drag Audit found no broad architectural corruption or
omitted executable behaviour. It confirmed brittle prose-regex continuity
checks, stale identity operational guidance and incoherent workspace step
numbering, and identified missing browser/accessibility automation as probable
governance drag. These findings are remediation evidence, not pilot activation.

## Locked MLAI-029 sequence

1. MLAI-029.1 Strategy Intelligence Foundation
2. MLAI-029.2 Situation and Opportunity Synthesis
3. MLAI-029.3 Objectives and Strategic Choices
4. MLAI-029.4 Marketing Mix and Measurement
5. MLAI-029.5 Governed Workflow Integration
6. MLAI-029.6 Client-Facing Strategy Workspace and Design-Partner Readiness

## Release state

MLAI-030.6 adds partner-specific acceptance evidence and MLAI-030.7 adds
append-only, tenant- and founder-bound activation controls with Velani Wholesale
as the first candidate. Neither story sends an invitation or activates data.

The post-MLAI-030.7 hosting audit confirmed the Google project is active and
billing-enabled while Cloud Run, Artifact Registry, Cloud Build and Secret
Manager remain disabled. The audit also found 144 SQLite persistence references.
Because Cloud Run local storage is replaceable, MLAI-031.1 refuses SQLite cloud
deployment and requires complete PostgreSQL migration and recovery evidence.

MLAI-031.2 adds runtime database selection, a PostgreSQL adapter compatible with
the canonical repository contract, deterministic dependency-ordered generation of
all 21 tables, and source-preserving transactional synthetic migration with exact
per-table parity. The index-idempotency correction is recorded at `b09055a`.

Commit-bound live evidence now passes locally and against the controlled synthetic
Cloud SQL PostgreSQL 18 instance in `africa-south1`. Schema versions 1 through 17,
all 21 tables, exact migration parity, 17 canonical application contracts, managed
backup, isolated local restore and post-rehearsal cleanup were verified. The Cloud
and local synthetic primary databases, sanitized evidence and recovery artifacts
were retained; temporary contract and restore databases were deleted. This closes
the durable-adapter external-evidence gate only and does not authorize deployment or
real-customer data.

ADR-0024 authorizes engineering and quality development and controlled
synthetic design-partner rehearsal, including approved Google test identities,
synthetic invitation claiming and browser, accessibility, recovery, revocation,
backup, security and failure testing. The former broad founder-frozen status is
superseded by `real_data_activation_frozen`.

Synthetic evidence is not market validation or learning. Actual business data,
external design-partner invitations, public or production activation, external
publishing, real-data learning, customer billing, unapproved paid services and
destructive production changes still require a separate founder-approved
decision and the applicable privacy, recovery, support and data boundaries.

## Durable deployment correction

ADR-0033 and LDR-053 now bind Durable Remediation: a one-off command repair may
not close a failure when a durable source correction and automated prevention
are reasonably achievable. The Cloud Run template, manifest renderer,
application configuration contract, PowerShell 5.1 validator, and CI job are one
canonical deployment contract. Manual environment reconstruction is refused.

The controlled image remains digest-pinned, private, and synthetic. Previously
failed Cloud Run revisions are evidence of configuration drift, not approval to
patch or rerun. No cloud mutation is part of this repository correction.

## Next engineer action

Install and validate the durable correction against clean baseline `a66c853`.
Render the canonical manifest outside the repository, review its redacted
contract summary, and request separate authority before creating another private
revision. Do not publish the OAuth app, send invitations, enable public signup,
billing, publishing, real-customer data, or real-data learning.

## Progressive release automation

ADR-0035 and LDR-055 supersede controller release authority. The controller is
an observational coordinator only. A permanent release requires hosted-build
provenance, independently signed in-toto evidence, exact RFC 3161 timestamp
coverage, independent policy verification, a separate final release signer and
deployment-layer enforcement. Legacy ledgers remain unchanged and
non-deployable; the 7e45958 run must not be backfilled into compliance.

The repository currently implements the binding trust policy and a shadow-only
independent verifier. It performs no cryptographic signing, cloud mutation,
deployment or authorization. Next work is hosted-builder provenance and signing
design, followed by separately authorized KMS, attestor and Binary Authorization
infrastructure in audit mode before enforcement.

## Queued customer-outcome governance

ADR-0036 and LDR-056 bind simple operator experience and evidence-governed
marketing-efficiency claims. Ordinary Company Brain work targets no more than
three meaningful decisions. The product targets 5-10 hours saved per week and
40-60% less repeatable campaign-preparation time, but those figures remain
qualified targets until representative customer-pilot evidence passes the
measurement protocol. MLAI-032.1 is queued and does not interrupt the active
hosting and zero-trust supply-chain storyline.

## MLAI-031.7: Canonical private ingress correction

- Correct the canonical template from public ingress to
  `internal-and-cloud-load-balancing`.
- Enforce one shared manifest/bootstrap contract and CI regression suite.
- Preserve the 9630fad run and image as incomplete, non-deployable history.
- After commit and CI, create a fresh image and observational release run.

## MLAI-031.8: Unified release-control repair

Founder authorization on 2026-08-12 initiates durable remediation of the
release operator path after more than four hours of PowerShell, path, parsing,
evidence and authorization-handoff failures. The Cloud Build itself succeeded.

The verified `2239244` image, build evidence and observational release run are
preserved. `SOURCE_VERIFIED`, `CI_PASSED` and `ARTIFACT_VERIFIED` remain passed;
`CONFIGURATION_VALIDATED` is the continuation point. No rebuild, duplicate run,
cloud mutation or retrospective admission authority is permitted.

ADR-0039 introduced `tools.release_control`, one stable external evidence index
and `scripts/mlai_release.ps1` as the only supported operator entry point. Its
repository validation, Windows PowerShell 5.1 journey, read-only adoption and
configuration gate have passed. Binary Authorization enforcement still
requires a later hardened build under ADR-0035.

## MLAI-031.9: Permanent read-only cloud preflight

MLAI-031.8 is committed at `9d2093157fd439de9fdedbb4475cd246f8cfc8e2`,
GitHub Actions run 34 passed, the verified `2239244` observations were adopted,
and `CONFIGURATION_VALIDATED` passed through plan
`87bcde478b4691f1464f13b1afcc7fc352f135be600b97b980cf7c89bb4c0046`.
Apply/resume idempotency and the indexed evidence chain both verified.

ADR-0040 extends the same control plane through read-only cloud preflight. It
uses exact non-mutating `gcloud` verbs, pinned resource identities, minimized
hash-indexed evidence and no secret payload access. Installation and CI perform
no cloud operation. After commit and CI, create one preflight plan and stop for
the exact plan approval. Do not proceed to `REVISION_CREATED`; ADR-0035 still
requires the hardened independent admission path before cloud mutation.

## MLAI-031.10: Windows Cloud CLI recovery

The approved MLAI-031.9 plan stopped twice before any cloud observation because
Python did not preserve the authenticated context when launching `gcloud.cmd`.
Direct diagnostics confirmed the expected account, default configuration and
project. The operation remains `running`, the gate remains pending, and no cloud
mutation occurred.

ADR-0041 makes the Windows batch adapter explicit, adds same-adapter local
diagnostics, binds plans to executor provenance and requires formal
supersession of the old operation before a fresh plan and approval. Installation
must not alter the external release state. After commit and CI, run
`doctor-cloud`, formally supersede plan `178f09fa673e1edefeb7034245879e1275fbb517b685a22a244a4f29d1983db6`,
then use `resume` to create—but not approve—the replacement plan.

## MLAI-031.11: Deterministic private revision preparation

MLAI-031.10 commit `ccd0f3d374e0ca8c96fb29fc40040eb48451b4d1` passed CI,
`doctor-cloud` passed, the stale preflight operation was superseded, and the
new provenance-bound `CLOUD_PREFLIGHT_PASSED` plan completed with evidence
SHA-256 `d2b779001a76aebec269b91a0db79c3839874753a2da54aabc93ae11fb998818`.
`REVISION_CREATED` is now the next eligible gate.

ADR-0042 introduces `prepare-revision` to render the exact private Cloud Run
manifest and command intent under ToolkitTemp without executing Cloud CLI,
mutating cloud, routing traffic, rebuilding, deploying or reading Secret
Manager payloads. The actual `REVISION_CREATED` mutation still requires
separate plan-bound approval after CI.

## MLAI-031.12: First-service origin bootstrap correction

The Cloud Run origin readiness check on 2026-08-13 returned `Cannot find
service [marketinglabai-velani-pilot]`. The first revision therefore cannot use
a real Cloud Run `status.url` yet. MLAI-031.12 allows the named first-bootstrap
origin only for `FIRST_PRIVATE_REVISION` after preflight proves the service is
absent, and marks the prepared evidence as requiring origin reconciliation.
Existing services still require the real Cloud Run URL.

## MLAI-033: Durable marketing workflow spine

Founder instruction on 2026-08-13 locks MLAI-033 as the next core
product-architecture epic after the private synthetic deployment reaches a safe
checkpoint. It is not Rabbit work. The durable workflow spine will own campaign
state, approval boundaries, idempotency, evidence, failure classification,
retry semantics, budget guardrails and operator status.

Agents remain downstream capabilities. Intent routing is next-core after the
spine; visual formatting, opportunity boosting and attribution remain future
work until the spine, tenant boundaries, approvals, budget controls and audit
evidence are proven.

### MLAI-033.1 governance definition

MLAI-033.1 — Deterministic Marketing Workflow State, Approval and Evidence
Foundation is implemented and tested. It provides a provider-neutral durable
aggregate with a canonical tenant-and-brand-scoped
identifier, exact Campaign Plan and optional Marketing Brief version
references, ADR-0043 states and failure classes, deterministic transitions,
command idempotency, version-and-action-bound approvals, privacy-safe
hash-linked evidence, attempt and retry accounting, failure classification and
operator status through SQLite and PostgreSQL-compatible transactional
persistence.

Founder approval on 2026-08-21 resolves nine foundation boundaries: one
workflow per executable governed marketing-work instance; independent Campaign
Plan and workflow lifecycles with immutable plan-version references and no plan
mutation; immutable version-and-action-bound approvals with high-impact
separation of duties; no automatic retries before separate ceilings and timing
approval; tenant/brand/workflow/command-kind/caller-key idempotency with
canonical request hashing; versioned canonical privacy-safe append-only
hash-linked sequence-ordered evidence committed atomically with authority
changes; terminal cancellation and supersession preserving evidence and
invalidating pending approvals; fail-closed execution without canonical
artifact persistence; and safe business-first operator status with authorized
progressive technical disclosure. Those decisions did not themselves authorize
implementation; the foundation was subsequently implemented and tested.

ADR-0043 now clarifies the four implementation contracts that previously
blocked safe foundation work: the complete default-deny transition matrix and
manual blocked-recovery rules; the RFC 8785-compatible restricted-number
versioned `MLAI-CJ` canonical UTF-8 JSON profiles with exact request, receipt and evidence
domains and envelopes, privacy-safe exclusions, SHA-256 construction and
evidence genesis. MLAI-CJ-1 schema 1 and its `workflow_id` remain frozen; new
request and receipt writers use MLAI-CJ-2 schema 2, which distinguishes
immutable `request_workflow_id` from an optional existing
`authoritative_workflow_id`, so
recovery conflicts preserve the proposed successor in the request hash while
safely referencing the tenant-and-brand-scoped existing successor; reserved and
persisted artifact proofs from a future read-only
`CanonicalArtifactAvailability` interface for execution-oriented transitions;
and explicit high-impact action classes with unclassified actions
`policy_blocked`. The clarification itself granted no implementation authority;
the workflow foundation is now implemented and tested, while canonical artifact
persistence remains separate and deferred.

Hard limits, adaptive limits, tier entitlements and provider budgets are
provider-neutral policy inputs only. No algorithm, distributed counter,
commercial tier, quota value, pricing or provider-specific budget mechanism is
selected. Approval roles, expiry, withdrawal mechanics and remaining exception
scope; retryable-failure mapping, ceilings, timing and manual authority;
idempotency retention; evidence retention and archival; remaining cancellation
effects; budget settlement; and
commercial values remain blocked or deferred for later authority.

Provider execution, publishing, queues, Cloud Tasks, paid actions, autonomous
agents, connectors, plugins, rate-limiting redesign, billing, customer
activation, cloud, IAM, secrets, external databases, deployment and release are
outside MLAI-033.1. RISK-040 and TD-043 remain open for parallel-owner and
deferred-capability risk beyond the implemented foundation. MLAI-033 remains
Core, and all existing Campaign Plan, Campaign Asset, Marketing Brief,
Marketing Calendar, generation, compliance, publishing and learning lifecycle
owners remain distinct.

## MLAI-031.13 handover note

REVISION_CREATED is passed, but startup cannot pass while the first bootstrap origin remains configured. Install and validate MLAI-031.13, then plan ORIGIN_RECONCILED using the startup-origin inspection evidence and revision-created evidence.

## MLAI-031.14 handover note

The release path is intentionally paused before ORIGIN_RECONCILED execution.
Install MLAI-031.14, wait for CI, then use the Python release-control CLI for
requirements and planning.

## MLAI-031.15 handover note

Do not retry ORIGIN_RECONCILED until MLAI-031.15 is installed, committed,
CI-verified, and `doctor-auth` passes. The failed direct browser-user gcloud path
is superseded by service-account impersonation.

## MLAI-031.17: PostgreSQL managed-provider strategy

The 2026-08-14 architecture review confirmed PostgreSQL as the canonical durable
datastore for hosted Earthonox runtime. ADR-0048 locks Google Cloud SQL for
PostgreSQL as the initial managed production implementation and reserves AlloyDB
for PostgreSQL as an evidence-triggered future scale option. SQLAlchemy and
Alembic are not approved in this increment.

## MLAI-031.16 handover note

MLAI-031.16 uses ADR-0049 because ADR-0048 is occupied by the PostgreSQL managed
provider decision. Commit and obtain CI before running the read-only identity
inspector. Do not re-use the failed ad hoc V1/V2 inspection commands.

## MLAI-031.18A closure

MLAI-031.18A is complete at commit `940c07226b406393b71973192fafe58cd4e65978`; GitHub Actions quality run 49 passed. ADR-0050 and LDR-064 make the repository integrity contract binding: CI must run the canonical read-only coherence checker, mojibake and governance identifier drift fail closed unless acknowledged by exact baseline hash, and any repair must be separately planned and hash-bound.

The five inherited governance files corrected by the closure plan are limited to `backlog/MLAI-031.md`, this handover, the locked-decision register, the risk register and the technical-debt register. RISK-037 and TD-040 preserve the remaining repository-integrity risk and debt. No cloud operation, infrastructure mutation, release-state change or release-ledger mutation is authorized by this closure.

### Canonical export corrective amendment

Evidence intake must use raw committed Git blobs, an explicit versioned path manifest, and completed-ZIP path/hash verification. `git archive` and working-tree bytes are forbidden as evidence authorities. PowerShell is LF; only `.bat` and `.cmd` use CRLF. Git configuration diagnosis is read-only and must never silently mutate system, global or repository-local settings.

The MLAI-031.18C intake exposed that suffix replacement could collapse a dotted
output-root name to `MLAI-031.zip`. The durable 18A correction appends `.zip` to
the complete name, refuses existing or ambiguous destinations and source/output
overlap before writing, and creates the ZIP exclusively. An intake workaround
or successful blob verification does not close this defect without the tracked
correction and adversarial tests.

`docs/handover/CURRENT_HANDOVER.md` remains the committed, reviewable checkpoint for architecture, authority and safe-resume state. It is not a per-command log. A future separately governed continuity capability should maintain a redacted atomic `CURRENT_SESSION.json` and append-only hash-chained event journal under `C:\Ai Projects\ToolkitTemp\MarketingLabAI\continuity`; it must exclude secrets and may not grant execution authority. Until that capability is authorized, update this handover at reviewed story checkpoints and preserve exact ToolkitTemp evidence paths and hashes in the handover entry.

## MLAI-031.18B security architecture lock

ADR-0051 and LDR-065 preserve the current Google Cloud Identity Platform,
tenant authorization, server-session, PostgreSQL, private Cloud Run and
zero-trust release boundaries and place them inside a fourteen-layer
defense-in-depth target. The lock distinguishes documented, implemented,
externally configured, rehearsed and operationally evidenced states so green CI
cannot be mistaken for deployed security.

Current foundations include strict Google token checks, bounded hashed sessions,
CSRF, secure cookies, tenant-membership revalidation, session revocation and
readiness evidence. MLAI-031.18C adds rotating renewal and fixed idle-plus-
absolute expiry. TD-041 retains provider revocation orchestration, MFA and
step-up, edge enforcement, centralized detection delivery and complete
security-CI and incident-recovery rehearsal as unimplemented. RISK-038 keeps
activation closed until applicable controls have current environment-bound
evidence.

Any next security implementation must be separately authorized and must extend
the repository-confirmed threat model and session/token lifecycle without
claiming the deferred controls below. The governance lock itself performed no
authentication, cloud, IAM, Identity Platform, Secret Manager, database,
deployment or release-state mutation.

## MLAI-031.18C session lifecycle foundation

MLAI-031.18C extends the existing PostgreSQL-compatible `pilot_sessions` store
without a migration. `created_at` is the original trusted 60-minute absolute
anchor, `expires_at` is the 15-minute idle deadline, and `revoked_at` makes
rotation predecessors and revoked sessions permanently non-authoritative.
CSRF-protected `PUT /v1/pilot/session` rotates both opaque session and CSRF
material through a conditional transaction, with at most one competing renewal
winner.

Sanitized creation and renewal audit evidence is inserted inside the same
session transaction. Audit failure rolls back creation completely or rolls
renewal back to the still-active predecessor; no replacement cookie or CSRF
material is disclosed.

Every use retains current membership revalidation and default-deny tenant
authorization. The membership repository invalidates matching active sessions
when an existing membership role or active state changes. Provider-global,
cross-tenant, MFA, recovery, refresh-token and security-engine invalidation are
not implemented and remain deferred under RISK-039 and TD-042.

MLAI-031.18C is formally closed on operator-supplied local validation against
the exact implementation bytes before commit: 46 focused tests passed, 1,046
full repository tests passed, Ruff passed, Black check passed, the
infrastructure coherence CI check passed with zero blocking findings, and
`git diff --check` passed. This is not live PostgreSQL rehearsal, production
validation, deployment validation or external CI evidence. No cloud, secret,
external-database, deployment, release-state or release operation occurred.

Provider-global revocation, cross-tenant or global invalidation, password and
recovery events, MFA and factor-change invalidation, provider refresh-token
revocation orchestration, suspicious-activity and security-engine hooks, a
dedicated administrator revocation transport, edge enforcement, centralized
detection, and production and external rehearsal evidence remain open or
deferred under RISK-038, RISK-039, TD-041 and TD-042. The durable MLAI-033.1
workflow foundation is implemented and tested; only the customer-facing
MLAI-033.2 planning-to-approval transport/workspace slice remains unimplemented.

## SOC 2 readiness boundary

LDR-067 records progressive SOC 2 readiness as aligned Future assurance work
that must reuse Earthonox's existing infrastructure, security, workflow,
evidence, migration, observability and operational-control boundaries. It does
not start certification, authorize compliance software or create parallel
evidence storage. Increment B2 comprehensive observational schema readiness
is completed and committed. Database lifecycle Increments B1 and B3 are also
completed and committed. MLAI-033.2 is the active next Core story, but remains
governance-defined and implementation-blocked rather than started.

Formal audit preparation, personnel controls, vendor-risk procedures, evidence
portals, Type I preparation, Type II operating-period evidence and certification
remain deferred until production scale, customer requirements or commercial due
diligence justify them. Any reopening requires separate authority; no
application, audit, vendor, deployment, cloud or release work is authorized by
this governance record.

## MLAI-033.2 planning-to-approval orchestration decision

Option B is locked for the tenant-authorized planning-to-approval workspace: one
provider-neutral durable orchestration record owns the request claim,
server-determined workflow identity, original canonical subcommand material,
progress state and final safe HTTP response. It is coordination state only. API
idempotency stays a completed-response cache, while workflow state, approvals,
workflow evidence, authorization audit, Campaign Plans and Marketing Briefs
retain their existing authorities.

The resolved contract set requires deterministic versioned `mwf_` workflow
identity and pseudonymous versioned `act_` actor reference, plus a
client-generated idempotency key containing
at least 128 bits of entropy, a versioned domain-separated workflow-ID
derivation, durable canonical subcommand identities and material before the
first domain command, a concurrent
uniqueness claim, exact-byte retry and missing-step reconciliation. Approval
recovery reuses an existing immutable approval and performs only a missing
transition. The workspace stops at `approved`; it authorizes no execution or
external effect. Raw idempotency keys must not be logged or returned.
Implementation must define and validate the accepted representation and length
and add golden tests. Fixed golden vectors are mandatory for both identity
derivations; accepted key encoding remains an implementation validation rule.

No implementation or migration is authorized. The six implementation contracts
are resolved: identity derivation and vectors, actor reference, deterministic
sub-command IDs/timestamps, exact monotonic recovery, scoped approval-evidence
validation, and legacy/new transport-idempotency compatibility. Retention and archival also
remain deferred. HTTP, MLAI-CJ-2 schema 2 and safe-command schema 1 versioning
remain separate, existing session and CSRF rules remain binding, and technical
detail is omitted for callers without `APPROVE`.

Implementation remains split into independently reviewable commits: A identity
contracts and vectors; B orchestration persistence and migration; C1 migration
20 and child-claim persistence; C2 create/plan/status/request-approval and
exact replay; C3 approval/rejection and evidence-bound recovery; C4 concurrency,
rehearsal, regression and acceptance; and E customer workspace.

### MLAI-033.2 operation-claim amendment

This amendment supersedes the earlier `workflow_api_orchestrations`-only
design for operation-level claims. `workflow_api_orchestrations` remains the
workflow-level root; `workflow_api_operation_claims` is now required for
operation-scoped claims. The revised C1–C4 sequence supersedes the earlier C/D
sequence. Exact replay, approval recovery and concurrent approval guarantees
depend on migration 20 and the child-claim table.

`workflow_api_orchestrations` remains the workflow-level reservation/root.
`workflow_api_operation_claims` is the operation-level child boundary. Each
child claim stores immutable command-plan material, progress, optimistic
version, idempotency digest and final safe response. Operation uniqueness is
scoped by tenant, brand, actor reference, operation and client-key digest;
parent workflow reservation uniqueness is unchanged. Exact replay returns the
stored original response bytes. Approval recovery reconciles approval, receipt,
evidence, workflow state and child progress; contradictory state fails closed
without mutation.

The parent reservation uniqueness claim is acquired before workflow mutation.
Because migration 20 requires a non-null workflow foreign key, the child claim
is created immediately after successful workflow creation. A crash between
workflow creation and child persistence is recovered through the parent claim
and deterministic workflow identity; recovery never creates a second workflow.
Once created, the child owns operation progress and exact response replay. Exact
HTTP replay preserves the original status, ordered headers, exact UTF-8 body
bytes and body SHA-256 digest; no replay marker is added to the body.

Migration 20 is additive, SQLite-canonical, PostgreSQL-compatible,
non-cascading, and requires readiness and disposable rehearsal validation.
Retention and archival remain deferred. The revised sequence is C1 migration
20 and child-claim persistence; C2 create/plan/status/request-approval and
exact replay; C3 approval/rejection and evidence-bound recovery; and C4
concurrency, rehearsal, regression and acceptance. The customer boundary still
stops at `approved`; no execution, publishing, provider, spend, learning,
workspace, SOC 2, cloud, deployment or release authority is added.

### C4 operational acceptance

Operator-supplied acceptance evidence records C4 commit
`75d7e9307c6ef32e807dd9e9a6d563feba8e51c0` as complete. The guarded disposable
PostgreSQL rehearsal passed all 36 selected tests, including the migration-20
readiness gate. Operation-claim uniqueness, exact replay, concurrency,
approval and rejection recovery, evidence validation, rollback, recovery and
cross-tenant protection all passed. Cleanup confirmed
`mlai_rehearsal` exists=false. At the acceptance checkpoint the branch was
synchronized with `origin/feature/tenant-architecture` and the working tree
was clean. No production or cloud database was contacted, and rehearsal
credentials remained protected.

## C5 evidence-grounded content generation decision boundary

Founder-approved C5 Layer 1 invariants define the next Core architecture
boundary; implementation remains separately unauthorized. Generation must use
an immutable tenant/brand-bound grounding snapshot with deterministic,
versioned canonical serialization and source IDs, versions and digests.
Product, Offer, Audience, Positioning, Strategy and Customer Segment domains
retain evidence ownership and lifecycle authority. Provider output never
authorizes claims or approval. High-risk unsupported, stale, revoked,
conflicting and cross-tenant claims are blocked; unknown or low-confidence
claims are `review_required` and cannot be approved until resolved or
explicitly revalidated.

Exact replay is distinct from regeneration. Generation and asset states remain
bounded to draft/review/approval/rejection/supersession outcomes, Campaign
Asset remains the artifact owner, and operation claims own only coordination,
replay and recovery. C5 does not expand ADR-0043 workflow ownership and does
not authorize execution, publishing, providers, spend, learning, deployment,
release or customer activation.

The approved defaults permit one logical versioned tenant/brand Voice authority
(with legacy `VoiceProfile` only as an adapter), least-privilege evidence
disclosure, existing platform encryption controls, disabled destructive
deletion, and internal provider-neutral error codes. The bounded-hybrid
persistence decision keeps Campaign Asset/Asset Revision as the sole
customer-facing artifact and lifecycle owner. A subordinate Generation Attempt
record may exist only for operational provenance, retries, provider results,
validation and crash recovery; it may not own assets, approvals, workflow
state, evidence, publishing or customer-facing lifecycle. Operation claims
remain coordination/replay records and existing evidence domains retain
evidence ownership. Asset revisions are immutable and tenant/brand-bound;
exact replay returns the original persisted result without provider invocation,
while regeneration creates a new request identity and immutable successor.
New raw grounding persistence remains blocked until retention, deletion, privacy
and ownership policy is approved. Founder-approved Phase B defaults lock a minimum
anti-generic floor of three semantically distinct anchors across at least two
source categories; channel/content-type packs may require additional anchors
and structure. Architecture/Quality owns policy versioning, compatibility,
rollback and golden-corpus governance. Product/marketing owns
channel/content-type rules, while evidence domains retain source meaning and
lifecycle authority. High-risk claims require direct approved evidence;
derived claims require deterministic approved transformations with complete
lineage, unit preservation and no unsupported extrapolation. Unknown and
low-confidence claims are `review_required` and cannot be approved unresolved;
high-risk, stale, revoked, expired, superseded, conflicting, digest-invalid
and cross-tenant claims are `blocked`. Policy packs are append-only and
versioned; rollback affects only new requests, and historical snapshots and
validation results are never silently reinterpreted.

Exact effective dates, compatibility windows, golden-corpus fixture ownership,
timeout/retry values, retention and archival values, public error-code
compatibility, storage fields, migration details and encryption implementation
details remain separately governed. Contradictory, missing, cross-tenant or
digest-invalid state must fail closed without mutation. Any schema, migration,
persistence, retention, archival, deletion, encryption or legal-hold
implementation requires separate authorization. No persistence, schema, migration, API,
workflow, provider, Campaign Asset, publishing, execution, spend, learning,
deployment or release implementation is authorized by this decision.

The founder-approved C5 Phase C metadata-first policy makes Migration 21
additive and metadata-first. Campaign Asset/Asset Revision remains the sole
customer-facing lifecycle owner; Generation Attempt remains subordinate
operational/provenance state. The approved metadata set is tenant/brand-bound
asset and immutable revision identity, generation identity, snapshot digest and
snapshot schema/canonicalization versions, source references, output digest,
validation outcome, policy-pack identity, safe findings, provider/model
provenance, workflow references and revision lineage. Raw grounding snapshot
content is not persisted in this phase. Exact replay must use an immutable
persisted output reference and must not invoke a provider; mutable timestamped
files are not authoritative replay storage. Destructive deletion remains
disabled pending retention, archival, deletion and legal-hold approval.
Encryption/key ownership and raw-content persistence require separate
authorization. No parallel asset, approval, evidence, workflow or
operation-claim owner is created. Migration 21 requires SQLite/PostgreSQL
parity, manifest and readiness updates, and disposable rehearsal coverage.

LDR-069 records these founder-approved Phase B policy defaults. C5 remains
governance-defined; no implementation, persistence, schema, migration or
external operation is authorized by the lock.

### C5 Phase C local implementation checkpoint

The 2026-08-26 task authorization implemented the generation/review boundary
against the existing Migration 21 schema without changing schema, migrations,
the schema manifest or readiness contracts. `GovernedGenerationService` binds
each immutable Asset Revision and subordinate Generation Attempt to the
tenant/brand scope, request and generation identities, grounding and output
digests, policy and validation identities, workflow/operation-claim references,
and revision lineage. Campaign Asset remains the lifecycle owner; workflow
approval records remain approval/evidence authority; operation claims remain
coordination and replay authority.

Exact replay resolves and verifies the immutable output reference and returns
the persisted result without generator invocation. Regeneration requires a new
request and generation identity and creates an immutable successor revision.
Approval rechecks the persisted output digest, exact policy identity, current
approved source-reference set, tenant/brand scope, current revision and the
workflow-owned approval. Missing, contradictory, stale, revoked, expired,
superseded, conflicting, digest-invalid and cross-scope state fails closed.
Only content-free source metadata is persisted; raw grounding content remains
out of persistence. No provider integration, publishing, execution, spend,
learning, deployment, release, UI, retention, archival, deletion or legal-hold
behavior was added.

### C5 recovery checkpoint governance decision

The recovery-hardening inspection identified a durable checkpoint gap in
Migration 21: Generation Attempt currently requires an existing immutable Asset
Revision, so a crash after generation but before output/revision persistence
cannot distinguish an uninvoked provider from a lost generated result. Retrying
could therefore duplicate provider invocation.

LDR-072 and ADR-0043 now govern the correction. Migration 22 will record a
tenant/brand-bound pre-generation Generation Attempt with request, generation
and idempotency identity before provider invocation. The attempt may temporarily
have no revision reference, then binds immutably to exactly one Asset Revision
after output persistence. Uniqueness prevents duplicate attempts for the same
tenant, brand, request and generation identity.

All existing ownership boundaries remain unchanged. Campaign Asset owns
lifecycle; Asset Revision is immutable; Generation Attempt is subordinate;
workflow tables own approval/evidence; operation claims own coordination/replay.
Exact replay invokes no provider, regeneration uses new request and generation
identities, contradictory or cross-scope state fails closed, and raw grounding
content remains unpersisted. SQLite/PostgreSQL parity is mandatory. No deletion,
retention, archival or legal-hold behavior is added.

This checkpoint is governance only. Migration 22 and all schema, manifest,
readiness, rehearsal, application and test work remain separately unauthorized.

The founder subsequently strengthened and locked this direction. Migration 22
must define a forward-only Generation Attempt state machine from `checkpointed`
through lease, provider, output, validation and immutable revision-binding
boundaries. `completed`, `validation_failed` and `failed` are terminal. The
explicit `provider_outcome_unknown` state prohibits repeat provider invocation
for the same identity and permits only proof-based reconciliation to verified
output or terminal failure.

The canonical idempotency identity binds tenant, brand, Campaign Asset, request,
generation, approved input/snapshot digest and versioned generation policy.
Transactional transitions, bounded leases, expiry and monotonic fencing protect
against concurrent and stale workers. Deterministic reconciliation advances
only permitted states and prevents duplicate attempts, revisions, approvals,
receipts and final responses across every crash boundary.

Migration 22 policy must also bound retries, timeouts, rate limits, output size,
circuit breaking and per-tenant cost before provider invocation. Observability
is metadata-only: correlation identity, scope, policy, digests, timestamps,
failure category and recovery decision. Raw grounding, secrets and unrestricted
prompt logs remain prohibited.

Marketing-quality validation must cover objective, audience, offer/positioning,
brand voice, channel constraints, prohibited claims, disclaimers, CTA, factual
grounding and approved Marketing Brief consistency. Human-readable validation
and rejection explanations remain a future operator requirement. Rejected,
failed, synthetic or unexecuted generations are excluded from Marketing
Learning. These strengthened requirements remain governance-only and authorize
none of the deferred implementation or external-operation capabilities.

The founder resolved the remaining Migration 22 planning contracts. Legacy
Migration 21 attempts use the non-authorizing compatibility identity
`legacy-unrecorded-v1`; any duplicate, contradiction, missing reference or
digest inconsistency aborts the migration atomically without repair or
reclassification. Generation operation claims use only the operation-specific
terminal states `completed`, `failed` and `requires_reconciliation`, never the
existing workflow-planning states.

The initial versioned control policy permits one provider attempt after
`provider_in_flight`, a 60-second provider timeout, a 120-second lease with
30-second renewal cadence and clock-skew allowance, a 1 MiB output limit, 10
tenant generation admissions per minute, and a circuit breaker of 5 qualifying
failures in 60 seconds with a 60-second recovery window. Tenant ceilings are
quota controls, not billing or spend accounting. The output store may add
persist-once and canonical-identity lookup for recovery but remains subordinate
to Campaign Asset and outside approval, workflow, publishing and execution
ownership.

Migration 22 has a no-mixed-writer deployment boundary. Migration 21 binaries
cannot write Migration 22 state. Once Migration 22 state has been written,
rollback requires verified backup restoration or a corrective forward
migration. These decisions refine LDR-072 and ADR-0043; no additional ADR is
required. They remain governance-only and do not authorize implementation,
migration execution, deployment or release-state changes.
