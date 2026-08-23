# MLAI-033: Durable Marketing Workflow Spine

## Status

Founder-locked core architecture epic

## Classification

Core. Not Rabbit.

## Build boundary and deferred capabilities

The governed implementation boundary, pilot and paid-production prerequisites,
evidence-triggered future work and explicit non-core exclusions are maintained
in the [MLAI-033 Build Boundary and Deferred Capability Register](../governance/registers/mlai-033-build-boundary-and-deferred-capability-register.md).
The register grants no implementation authority and does not resolve the
blocked owner decisions in MLAI-033.1.

## Purpose

MarketingLabAI needs one durable workflow spine for campaign planning,
approval, execution, recovery, evidence and later learning. Agents may
recommend or perform work, but workflow state, approval boundaries, retry
rules, budget limits and evidence belong to the product core.

## Scope

- Durable state model:
  `draft`, `planned`, `awaiting_approval`, `approved`, `running`, `blocked`,
  `failed`, `completed`, `superseded`, `cancelled`.
- Idempotency keys for customer-facing and cost-bearing actions.
- One approval model for publish, spend, boost, campaign launch, learning
  adoption and exception handling.
- Append-only workflow evidence ledger with actor, timestamp, input, output,
  source references, decision reason, failure reason, retry count and hashes.
- Failure taxonomy:
  `validation_failed`, `auth_required`, `provider_error`, `rate_limited`,
  `policy_blocked`, `budget_blocked`, `conflict_detected`,
  `needs_human_decision`.
- Operator status contract exposing current state, next action, blocked reason,
  available retry, required approval and evidence.
- Adapter boundary for Cloud Tasks, social channels, email, Shopify, analytics
  and future providers.
- Budget and risk guardrails for any paid or externally visible action.
- Learning hooks so completed workflows can later emit structured campaign
  learning evidence.

## Explicit Exclusions

- No autonomous paid optimization.
- No full attribution engine.
- No visual generation factory.
- No self-running growth agent.
- No real-customer automation until tenant, approval, budget and audit controls
  are proven.

## Acceptance

- The workflow spine is documented as a product architecture boundary.
- The Rabbit Rule classification is recorded.
- Agent, provider and Cloud Tasks execution remain adapters, not core state.
- The completed and tested foundation starts with deterministic workflow state,
  idempotency, evidence and approval primitives before autonomous agents.

## MLAI-033.1 — Deterministic Marketing Workflow State, Approval and Evidence Foundation

### Status

Implemented and tested as the provider-neutral durable workflow foundation;
remaining deferred controls retain their separate authority boundaries.

### Purpose

Define the first implementation boundary for one provider-neutral durable
marketing workflow spine. The implemented aggregate coordinates exact governed
work references while preserving the
independent lifecycles of Campaign Plan, Campaign Asset, Marketing Brief,
Marketing Calendar, generation, compliance, publishing and learning.

### Required implementation contract

- Create one canonical workflow identifier scoped to tenant and brand.
- Reference an exact immutable Campaign Plan version and, when applicable, an
  exact immutable Marketing Brief version; do not embed or mutate either
  lifecycle.
- Represent every ADR-0043 workflow state and failure class exactly.
- Enforce a deterministic, explicit transition matrix with optimistic workflow
  version checks and terminal-state refusal.
- Persist command idempotency so exact retries replay the prior result and key
  reuse with changed input fails as a conflict.
- Bind immutable approval requirements and decisions to the exact workflow
  version and action so later revisions cannot inherit stale authority.
- Append privacy-safe, sequence-ordered, hash-linked evidence containing actor,
  timestamp, transition, safe source references, decision or failure reason,
  attempt count and sanitized input/output hashes.
- Record attempt accounting, deterministic retry eligibility and governed
  failure classification without exposing provider exceptions as core state.
- Derive an operator-status projection containing current state, one safe next
  action, blocked reason, retry availability, required approval and progressively
  disclosed evidence.
- Default-deny every read and mutation by tenant and brand. Client-supplied
  identifiers remain routing context, never authority.
- Use the canonical database boundary with SQLite and PostgreSQL-compatible
  schema, queries and transactions.
- Commit workflow state, the applicable approval or attempt result and its
  evidence atomically; partial authority must roll back.

### Provider-neutral policy requirements

- Hard limits are immutable policy inputs with dimension, unit, ceiling, scope
  or period, policy version and effective interval. Adaptive limits may only
  reduce activity or require approval and may never weaken a hard limit.
- Tier entitlements are versioned capability decisions and remain separate from
  identity permission, privacy authority, activation, budget and provider
  availability.
- Provider budgets express estimated, reserved, consumed, released and
  reconciled quantities in declared provider-neutral units. Adapters may report
  observations but may not own entitlement or spend policy.
- Policy evaluation returns structured outcomes such as `allowed`,
  `approval_required`, `policy_blocked`, `budget_blocked` or `rate_limited`.
- MLAI-033.1 selects no adaptive-rate algorithm, distributed counter, pricing,
  commercial tier, quota value or provider-specific budget mechanism.

### Founder-approved owner decisions

- One workflow per executable governed marketing-work instance.
- Independent Campaign Plan and workflow lifecycles; the workflow stores exact
  immutable Campaign Plan version references and never mutates Campaign Plan
  state.
- Immutable workflow-version-and-action-bound approvals, with separation of
  duties for high-impact actions.
- No automatic retries until retry ceilings and timing are separately approved.
- Command idempotency scoped to tenant, brand, workflow, command kind and
  caller-supplied key, using canonical request hashing.
- Versioned, canonical, privacy-safe, append-only, hash-linked and
  sequence-ordered evidence committed atomically with authority-changing state.
- Terminal cancellation and supersession that preserve evidence and invalidate
  pending approvals.
- Fail-closed execution when canonical artifact persistence is unavailable.
- Safe business-first operator status, with technical detail progressively
  disclosed only when authorized.

### Clarified foundation contracts

- ADR-0043 contains the complete default-deny transition matrix. `failed`,
  `completed`, `superseded` and `cancelled` are terminal; blocked recovery is
  explicit manual intervention to the recorded resume state, never automatic
  retry.
- Command requests, receipts and evidence use the RFC 8785-compatible,
  restricted-number versioned `MLAI-CJ` UTF-8 profiles, exact record-kind domains and
  domain-separated SHA-256 over privacy-safe fields. ADR-0043 fixes the complete
  receipt envelope and evidence sequence-1 genesis value. MLAI-CJ-1 schema 1 is
  frozen with its original `workflow_id`; new request and receipt writers use
  MLAI-CJ-2 schema 2, keeping immutable `request_workflow_id` distinct from an
  optional existing
  `authoritative_workflow_id`; recovery conflicts never rewrite the requested
  successor identity or disclose cross-tenant or cross-brand authority.
- `approved` to `running`, `blocked` to `running` and `running` to `completed`
  are execution-oriented. They require the applicable reserved or persisted
  proof from the read-only `CanonicalArtifactAvailability` interface and fail
  closed on missing, inaccessible, superseded, integrity-invalid or
  cross-tenant artifacts.
- Paid or spend actions, publishing or launch, learning adoption, policy or
  control exceptions, external-state mutations and externally effective
  cancellation or supersession are high-impact and require separation of
  duties. Unclassified actions are `policy_blocked`; ordinary internal planning
  and read-only status viewing are not high-impact.

These governance contracts did not themselves authorize implementation. The
foundation is now implemented and tested; canonical artifact persistence and
the deferred controls below remain outside that completed boundary.

### Decisions still blocked or deferred

- Approval roles, expiry, withdrawal mechanics and exception scope beyond the
  approved high-impact separation-of-duties rule.
- Retryable failure mapping, attempt ceilings, timing and manual-retry authority.
- Command-idempotency retention.
- Evidence retention and archival.
- Cancellation and supersession effects on attempts and reservations beyond
  pending-approval invalidation and evidence preservation.
- Currency, precision, reservation, settlement, release, refund and provider
  reconciliation semantics.
- Commercial tier, entitlement, fair-use, quota and override values, which
  remain founder-reserved decisions.

### Explicit exclusions

- Provider execution, publishing, queue integration and Cloud Tasks.
- Paid actions, autonomous agents, connectors and plugins.
- Adaptive-rate algorithm implementation or a new rate-limiting architecture.
- Pricing, commercial tiers, quota values, billing or customer activation.
- Cloud, IAM, secrets, external databases, deployment or release changes.
- Further MLAI-033.1 expansion or MLAI-033.2 transport/workspace implementation
  without separate authority.

### Definition acceptance

- The foundation is recorded as implemented and tested; the separately scoped
  customer-facing orchestration/workspace remains unimplemented.
- ADR-0043 and LDR-061 remain authoritative and MLAI-033 remains Core, not Rabbit.
- Existing lifecycle owners and provider-neutral boundaries are preserved.
- RISK-040 and TD-043 retain the parallel-owner and deferred-capability risk
  beyond the implemented foundation.
- Further implementation, testing, commit, push, cloud deployment and release
  each require separate explicit authority.

## MLAI-033.2 — Tenant-Authorized Planning-to-Approval Workspace

### Status

Governance-defined; the implementation contracts are resolved, but no
implementation, migration or validation is authorized.

### Customer outcome and boundary

Provide one tenant-authorized, resumable customer path that creates a governed
marketing workflow from exact Campaign Plan and optional Marketing Brief
versions, progresses through `draft` to `planned` to `awaiting_approval`, records
an immutable approval decision, and reaches `approved`. The boundary stops at
`approved`; it grants no authority for `running`, execution, generation,
publishing, spend, providers, external effects or learning.

### Locked orchestration decision

- Keep `workflow_api_orchestrations` as the workflow-level reservation/root and
  add `workflow_api_operation_claims` as the operation-level child boundary.
  Each operation claim owns immutable command-plan material, progress,
  optimistic version, idempotency digest and final safe HTTP response. Neither
  record owns workflow state, approvals, workflow evidence, authorization
  audit, Campaign Plans or Marketing Briefs.
- Operation claims are uniquely scoped by tenant, brand, actor reference,
  operation and client-key digest. Parent workflow reservation uniqueness is
  unchanged. Exact replay returns the stored original response bytes; changed
  material conflicts deterministically.
- Preserve API idempotency as a completed-response cache. Workflow receipts and
  hash-linked evidence remain the authoritative domain records.
- Require deterministic versioned `mwf_` workflow identity derived from
  authenticated tenant, brand, actor, operation and client-key digest inputs.
  Require a client-generated idempotency key containing at least 128 bits of
  entropy and a versioned, domain-separated workflow-ID derivation. Raw keys
  must not be logged or returned. Implementation must explicitly define and
  validate the accepted representation and length and provide golden tests;
  the exact accepted encoding is an implementation validation detail, not a
  new product or commercial decision.
  The `workflow_api_orchestrations` uniqueness claim is the authoritative
  pre-mutation reservation and is acquired before any workflow mutation. Because
  migration 20 requires a non-null workflow foreign key, the
  `workflow_api_operation_claims` child is created immediately after successful
  workflow creation. It persists the original canonical subcommand request IDs,
  timestamps, command kinds, expected versions and safe-command material. A
  crash in that interval is recovered through the parent claim and deterministic
  workflow identity; recovery never creates a second workflow.
- A durable uniqueness claim resolves concurrent first submissions. Exact
  retries reuse the original canonical bytes and reconcile only missing steps;
  changed input fails deterministically as a conflict.
- Interrupted create-and-plan orchestration resumes from authoritative workflow
  receipts. Approval recovery reuses an existing immutable approval and applies
  only a missing transition.
- Additive migration 20 is required for the child claim table. It is
  SQLite-canonical, PostgreSQL-compatible, non-cascading, and must be covered
  by readiness and disposable rehearsal validation. Historical migrations
  remain unchanged, and this definition does not authorize applying it.
- Approval recovery reconciles the immutable approval, authoritative receipt,
  evidence, workflow state and child progress. Contradictory state fails
  closed without mutation.
- Retention and archival remain deferred and require separate governance.
- Keep the HTTP contract version, MLAI-CJ-2 envelope `schema_version: 2`, and
  workflow safe-command `schema_version: 1` distinct. No retry may silently
  convert or rehash persisted canonical bytes.
- Planning-to-approval POST operations retain existing authenticated session
  and CSRF requirements. Technical detail is omitted for callers without
  `APPROVE`; omission must not be replaced by tenant, actor or evidence
  disclosure.

### Resolved implementation contracts

These contracts govern implementation. Their golden vectors and adversarial
tests are required before the relevant implementation commit is accepted:

- `mwf_` uses versioned domain-separated SHA-256 over canonical authenticated
  tenant, brand, pseudonymous actor, operation and client-key-digest inputs;
  output is 32 lowercase hexadecimal characters after the `mwf_` prefix. A
  fixed golden input, preimage and digest is mandatory.
- `act_` uses versioned domain-separated SHA-256 over authenticated provider
  and subject identity, with stable pseudonymous 32-character lowercase hex
  output. Display names, sessions, CSRF values and tenant membership are
  excluded; a fixed golden vector is mandatory.
- Sub-command request IDs and command-key digests are versioned,
  domain-separated and derived from orchestration identity, ordinal and command
  kind. Original requested timestamps and canonical command bytes are persisted
  before the first authority-changing command and reused verbatim. HTTP,
  MLAI-CJ-2/schema 2 and safe-command/schema 1 remain separate.
- Orchestration claims use tenant, brand, actor, operation and client-key digest
  uniqueness; progress is monotonic. Retries reconcile authoritative receipts,
  replay exact bytes, conflict on changed input, and fail closed on discrepancies.
- Approval requester evidence is selected only within tenant, brand, workflow,
  action and version scope; approval identity, requester, decision, receipt,
  canonical digest, predecessor chain and sequence must validate. Missing,
  ambiguous, invalid or cross-tenant evidence blocks the transition.
- Legacy API idempotency rows remain readable with their existing raw-key
  behavior. New orchestration records store only key digests and safe canonical
  material; raw keys are never logged or returned. Accepted key encoding,
  format and length validation require implementation golden tests.

### Independently reviewable implementation commits

- A: canonical identity contracts and golden vectors.
- B: orchestration persistence, migration and compatibility.
- C1: migration 20 and operation-claim persistence.
- C2: create/plan/status/request-approval and exact replay.
- C3: approval/rejection and evidence-bound recovery.
- C4: concurrency, rehearsal, regression and acceptance.
- E: customer workspace and business-first status ending at `approved`.

### Non-authorization

### Supersession clarification

The earlier `workflow_api_orchestrations`-only design is superseded for
operation-level claims. `workflow_api_orchestrations` remains the
workflow-level root, while `workflow_api_operation_claims` is now required for
operation-scoped claims. The revised C1–C4 sequence supersedes the earlier
C/D sequence. Exact replay, approval recovery and concurrent approval
guarantees depend on additive migration 20 and the child-claim table.

The parent reservation is acquired before workflow mutation. The child claim is
created immediately after successful workflow creation because migration 20
requires its workflow foreign key to be non-null. If a crash occurs between
those writes, deterministic workflow identity and the parent claim reconcile the
missing child without creating another workflow. Once created, the child owns
operation progress and exact response replay.

Exact HTTP replay persists and returns the original status, ordered headers,
exact UTF-8 body bytes and body SHA-256 digest. The replay marker is internal
transport metadata and is never added to the response body.

This governance definition authorizes no application code, test, database
schema, migration, cloud, deployment, customer activation, release, staging,
commit or push operation.
