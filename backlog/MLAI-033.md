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

Governance-defined and blocked on the implementation contracts below; no
implementation, migration or validation is authorized.

### Customer outcome and boundary

Provide one tenant-authorized, resumable customer path that creates a governed
marketing workflow from exact Campaign Plan and optional Marketing Brief
versions, progresses through `draft` to `planned` to `awaiting_approval`, records
an immutable approval decision, and reaches `approved`. The boundary stops at
`approved`; it grants no authority for `running`, execution, generation,
publishing, spend, providers, external effects or learning.

### Locked orchestration decision

- Add one provider-neutral orchestration record for resumable
  planning-to-approval API operations.
- The record owns only the durable request claim, server-determined workflow
  identity, original canonical subcommand material, progress state and final
  safe HTTP response. It does not own workflow state, approvals, workflow
  evidence, authorization audit, Campaign Plans or Marketing Briefs.
- Preserve API idempotency as a completed-response cache. Workflow receipts and
  hash-linked evidence remain the authoritative domain records.
- Require a client-generated idempotency key containing at least 128 bits of
  entropy and a versioned, domain-separated workflow-ID derivation. Raw keys
  must not be logged or returned. Implementation must explicitly define and
  validate the accepted representation and length and provide golden tests;
  the exact accepted encoding remains an unresolved implementation contract.
  Persist the original canonical
  subcommand request IDs, timestamps, command kinds, expected versions and
  safe-command material before the first authority-changing command.
- A durable uniqueness claim resolves concurrent first submissions. Exact
  retries reuse the original canonical bytes and reconcile only missing steps;
  changed input fails deterministically as a conflict.
- Interrupted create-and-plan orchestration resumes from authoritative workflow
  receipts. Approval recovery reuses an existing immutable approval and applies
  only a missing transition.
- A future migration is required. Historical migrations remain unchanged, and
  this definition neither creates nor authorizes that migration.
- Retention and archival remain deferred and require separate governance.
- Keep the HTTP contract version, MLAI-CJ-2 envelope `schema_version: 2`, and
  workflow safe-command `schema_version: 1` distinct. No retry may silently
  convert or rehash persisted canonical bytes.
- Planning-to-approval POST operations retain existing authenticated session
  and CSRF requirements. Technical detail is omitted for callers without
  `APPROVE`; omission must not be replaced by tenant, actor or evidence
  disclosure.

### Unresolved implementation contracts

These items block implementation and must be locked separately without
inventing privacy, retention or compatibility policy:

- the workflow-ID golden vector and exact versioned derivation format;
- actor-reference derivation and truncation;
- subcommand request-ID and timestamp derivation;
- the exact orchestration recovery and reconciliation algorithm;
- approval-requester evidence lookup and digest validation; and
- transport-idempotency raw-key compatibility treatment, including the exact
  accepted encoding, format and length validation.

### Non-authorization

This governance definition authorizes no application code, test, database
schema, migration, cloud, deployment, customer activation, release, staging,
commit or push operation.
