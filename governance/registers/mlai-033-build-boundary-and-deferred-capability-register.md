# MLAI-033 Build Boundary and Deferred Capability Register

## Status and authority

Governance classification attached to MLAI-033. ADR-0043 and LDR-061 remain
authoritative: MLAI-033 is Core, the durable workflow spine owns workflow state,
approval boundaries, idempotency, evidence, retries, failure classification,
budget guardrails and operator status, and provider or infrastructure adapters
must not become parallel owners.

This register sequences capability work; it changes no architecture decision,
founder-reserved commercial law, lifecycle ownership, release boundary or
implementation status. Every implementation, test, commit, push, cloud,
deployment and release action still requires its own explicit authority.

## Required now

These are requirements for the first separately authorized MLAI-033
implementation increment. Their presence here does not authorize implementation.

| Capability | Required boundary |
|---|---|
| Workflow durability | One provider-neutral, tenant-and-brand-isolated durable aggregate through the canonical SQLite/PostgreSQL-compatible persistence boundary; exact aggregate granularity remains blocked in MLAI-033.1. |
| Approvals | Immutable approval requirements and decisions bound to the exact workflow version and action; roles, expiry, withdrawal, separation of duties and exceptions remain owner decisions. |
| Idempotency | Durable workflow-command receipts with canonical request hashes, exact replay and changed-input conflict; scope and retention remain owner decisions. |
| Evidence | Append-only, privacy-safe, sequence-ordered and hash-linked workflow evidence committed atomically with authority-changing state; canonicalization and retention remain owner decisions. |
| Retries | Explicit attempt accounting and deterministic eligibility derived from failure class and policy; ceilings, timing and manual authority remain owner decisions. |
| Failure handling | ADR-0043 failure classes are the core vocabulary; raw provider or infrastructure exceptions remain adapter observations. |
| Operator status | Current state, one safe next action, blocked reason, retry availability, required approval and progressively disclosed evidence. |
| Tenant isolation | Default-deny tenant and brand ownership on workflows, approvals, attempts, idempotency and evidence; client identifiers remain routing context only. |
| Testing | Focused transition, idempotency, approval, evidence, retry, transaction and cross-tenant tests plus affected regression, PostgreSQL-compatibility and full quality gates are required under separate TEST authority. |
| Hard limits | A provider-neutral policy-input contract with dimension, unit, ceiling, scope, version and effective interval; values and paid-action enforcement remain separately governed. |

## Required before private pilot

Each capability below remains deferred until its trigger. This register
authorizes no implementation.

| Capability | Reason deferred | Measurable trigger that reopens it | Authority required before implementation | No implementation authority |
|---|---|---|---|---|
| Rate limiting | The current process-local sliding-window control is intentionally bounded to a single-instance private topology; MLAI-033 must not redesign it speculatively. | Before private-pilot activation, confirm one-instance topology, positive configured limits, bounded request bodies and a passed rate-limit alert/recovery rehearsal; if more than one serving instance is approved, reopen distributed enforcement. | Architecture and security review; founder authority for pilot activation; separate IMPLEMENT and TEST authority. | Classification only; the current rate limiter is unchanged. |
| Canonical artifact persistence | Generated content and compliance outputs still use an injected or legacy file boundary, so execution completion cannot yet claim durable authoritative artifacts. | Before any workflow adapter may enter `completed`, publish, or emit learning evidence, a tenant-scoped canonical artifact repository and recovery contract must pass SQLite/PostgreSQL compatibility and cross-tenant tests. | Architecture authority plus separate IMPLEMENT, TEST and persistence-migration authority. | No artifact or workflow implementation is authorized. |
| MFA and recovery integrations | MLAI-031.18C intentionally left MFA, factor-change, password and recovery event integration open. | Before private customers or real data are activated, applicable MFA, recovery and factor-change flows have environment-bound rehearsal evidence and invalidate affected sessions. | Founder activation approval, security architecture approval, identity-provider change authority, IMPLEMENT and TEST authority. | No identity-provider or session change is authorized. |
| Provider-global invalidation | Current session invalidation is bounded to identity-and-tenant membership events and cannot respond to provider-global disablement or compromise. | Before private customers or real data are activated, provider-global disablement/revocation events and governed administrator transport pass cross-tenant and recovery rehearsal. | Security architecture, identity-provider, privacy and founder activation authority plus separate IMPLEMENT and TEST authority. | RISK-039 and TD-042 remain open; no invalidation implementation is authorized. |
| Baseline operational evidence | Local operator status and privacy-safe signals do not prove deployed detection, recovery or support readiness. | Before pilot activation, current environment-, commit- and control-version-bound evidence passes applicable monitoring, recovery, incident, support and tenant-isolation gates. | Operations/security owners and founder activation authority; external execution separately authorized. | No rehearsal, monitoring configuration or activation is authorized. |

## Required before paid production

Each capability below remains deferred until its trigger. This register
authorizes no implementation and chooses no commercial value.

| Capability | Reason deferred | Measurable trigger that reopens it | Authority required before implementation | No implementation authority |
|---|---|---|---|---|
| Hard-limit enforcement | MLAI-033.1 defines only provider-neutral inputs; there is no approved paid action, currency policy or ceiling value. | Before the first paid or externally visible action, approved immutable ceilings exist for every applicable spend/action dimension and adversarial tests prove they cannot be weakened by adapters or adaptive policy. | Founder approval for ceilings and override law; architecture, security, IMPLEMENT and TEST authority. | No values, counters or enforcement are authorized. |
| Tier entitlements | Capability access is separate from identity, privacy, activation, budget and provider availability; commercial tiers are unapproved. | Before selling or enforcing a plan, founder-approved versioned capability bundles, effective dates, upgrade/downgrade treatment and customer terms exist and pass default-deny tests. | Founder commercial approval plus product, architecture, legal/privacy, IMPLEMENT and TEST authority. | No tier, price, quota or entitlement implementation is authorized. |
| Provider budgets | Estimated, reserved, consumed, released and reconciled quantities lack approved currency, precision, settlement and refund semantics. | Before a paid provider call, approved unit/currency rules and reservation-to-reconciliation invariants exist and concurrency, failure and refund tests pass. | Founder/finance approval plus architecture, provider, IMPLEMENT and TEST authority. | No provider budget, reservation or paid call is authorized. |
| Billing | Billing would create external financial and customer obligations before validated packaging and operational controls. | Before collecting payment, approved pricing, tax, invoicing, refund, cancellation, entitlement and support terms exist and end-to-end billing reconciliation is rehearsed. | Founder commercial approval, finance/legal/privacy review and separate external-service, IMPLEMENT, TEST and deployment authority. | No billing account, integration, price or charge is authorized. |
| Paid-production assurance | Repository validation and a private pilot do not prove production-scale security, recovery, support, cost or release admission. | Before paid production, all applicable ADR-0051 security layers and zero-trust release controls have current production-bound evidence and founder residual-risk acceptance. | Founder release/activation approval plus security, operations, privacy, infrastructure and release authorities. | No deployment, production activation or release is authorized. |

## Trigger-based future work

Every capability below is aligned but premature. It reopens only on its stated
evidence trigger and requires separate authority; this register authorizes no
implementation.

| Capability | Reason deferred | Measurable trigger that reopens it | Authority required before implementation | No implementation authority |
|---|---|---|---|---|
| Adaptive limits | No representative execution history exists from which to derive safe adaptive policy, and adaptive behavior must never weaken hard limits. | At least one approved pilot dataset covers 90 days or 1,000 governed attempts, contains measured rejection/cost/capacity outcomes, and an owner-approved evaluation shows a static limit materially harms safety or service. | Founder approval for customer-impacting policy, architecture/data/privacy review, IMPLEMENT and TEST authority. | No scoring, learning or adaptive-rate algorithm is authorized. |
| Durable asynchronous event bus | The current synchronous in-process bus is sufficient for local domain notification and is not workflow authority. | Two or more independently deployed consumers require replay, or measured synchronous handler latency/failure breaches an approved SLO in three reviewed incidents. | Architecture and operations authority plus IMPLEMENT, TEST and infrastructure authority where external transport is selected. | No event-bus replacement or broker is authorized. |
| Queues and Cloud Tasks | No approved workflow performs external long-running or independently retryable execution. | A separately authorized adapter has work exceeding the synchronous request SLO or requires durable delayed delivery/retry across process restarts, demonstrated by a load or failure rehearsal. | Architecture, security, cloud-cost and explicit CLOUD/IMPLEMENT/TEST authority. | No queue, Cloud Tasks API or cloud mutation is authorized. |
| Caching | No measured latency or database-load problem requires another consistency boundary. | Representative load shows the approved p95 latency or database-utilization SLO is breached in three repeatable runs and profiling attributes the breach to repeatable reads suitable for bounded caching. | Architecture, privacy/security, IMPLEMENT and TEST authority. | No cache, cache service or invalidation design is authorized. |
| API gateway | Earthonox has one bounded application entry path and no approved public partner API or multi-service routing need. | A public/partner API or at least two independently deployed services require centralized routing, authentication policy or version management under an approved exposure plan. | Founder public-access approval plus architecture, security, infrastructure, IMPLEMENT and TEST authority. | No gateway, public route or exposure is authorized. |
| Plugins and connector framework | Individual integrations are adapters and no repeated extension contract has been validated. | Three separately approved connectors demonstrate the same stable lifecycle, permission, evidence and failure contract without provider-specific core fields. | Product/architecture approval and connector-specific security, privacy, IMPLEMENT and TEST authority. | No plugin, connector or external account access is authorized. |
| Microservices | The canonical application boundary has no measured independent deployment or scaling bottleneck. | One bounded capability requires independent deployment or scaling and profiling shows the modular monolith cannot meet an approved SLO after simpler remediation. | Architecture review, founder cost approval where material, and separate infrastructure, IMPLEMENT, TEST and deployment authority. | No service extraction or network boundary is authorized. |
| Kubernetes | Current hosting strategy does not require cluster scheduling or operations complexity. | Two independently reviewed Cloud Run/platform constraints block approved workloads and a cost/operations comparison shows Kubernetes is the least-complex compliant option. | Founder cost/operations approval plus architecture, security, infrastructure, deployment and release authority. | No cluster, namespace or Kubernetes manifest is authorized. |
| Autoscaling beyond the bounded pilot | The controlled pilot is deliberately single-instance and process-local controls assume that topology. | Representative load exceeds approved one-instance capacity or availability SLO in three repeatable runs after application optimization, and distributed session/rate/budget controls are designed and validated. | Founder cost approval plus architecture, security, infrastructure, IMPLEMENT, TEST and deployment authority. | No scaling or instance-bound change is authorized. |
| Multi-region | No approved availability, residency or recovery requirement justifies cross-region consistency and cost. | A signed customer/regulatory requirement or approved RTO/RPO cannot be met in one region, confirmed by a recovery rehearsal and costed architecture review. | Founder commercial/cost approval plus legal/privacy, architecture, security, infrastructure, deployment and release authority. | No replication, traffic routing or regional resource is authorized. |
| Advanced observability | Baseline privacy-safe signals and readiness evidence exist; high-cardinality tracing or analytics could increase cost and privacy exposure without an operational need. | Three material incidents cannot be diagnosed within the approved response target using current evidence, or an approved SLO requires cross-service traces after services actually exist. | Operations, security/privacy, architecture, cost, IMPLEMENT and TEST authority. | No telemetry vendor, agent, export or customer-content capture is authorized. |

## Explicitly outside Earthonox’s core

These capabilities are rejected as core ownership. There is no automatic
reopening trigger; changing this classification requires the stated authority
and formal change control. This register authorizes no implementation.

| Capability | Reason outside core | Measurable trigger that could justify review | Authority required before implementation | No implementation authority |
|---|---|---|---|---|
| Generic CRM features | Earthonox is a Marketing Intelligence Operating System, not a general customer-record, pipeline or sales-operations system. CRM data may enter only through governed adapters when it supports marketing intelligence. | A validated marketing workflow requires a narrowly defined CRM adapter and no existing provider can satisfy it without core-domain leakage. | Founder product-scope approval if core scope would change; otherwise product/architecture and connector security/privacy authority. | No generic CRM module is authorized. |
| Generic ERP/accounting features | Inventory, payroll, procurement, general ledger and enterprise resource planning are outside the product identity; only verified marketing-relevant inputs may be adapted. | A validated marketing decision requires a specific evidence field unavailable through a bounded adapter, supported by pilot evidence and architecture review. | Founder product-scope approval for any core expansion; otherwise adapter-specific product, architecture, finance/privacy authority. | No ERP or accounting platform capability is authorized. |
| Duplicate Campaign Plan ownership | ADR-0008 assigns planning identity and lifecycle to Campaign Planner. The workflow spine coordinates exact references and cannot replace it. | No operational metric reopens duplication; only a formal ADR supersession with migration evidence could change ownership. | Founder/architecture change control and an explicit superseding ADR. | No duplicate plan model or lifecycle is authorized. |
| Duplicate Campaign Asset ownership | Campaign Asset owns deliverable definition, dependency and asset lifecycle; workflow attempts may reference but not absorb it. | No operational metric reopens duplication; only formal architecture supersession with compatibility and migration evidence. | Architecture change control and founder approval if product behavior changes. | No duplicate asset model or lifecycle is authorized. |
| Duplicate Marketing Brief ownership | Marketing Brief owns execution decisions and approval history independently of workflow execution state. | No operational metric reopens duplication; only formal ADR supersession with migration evidence. | Founder/architecture change control and an explicit superseding decision. | No duplicate brief model or lifecycle is authorized. |
| Duplicate publishing ownership | Publishing remains a distinct lifecycle and future adapter boundary; a workflow approval or `completed` state is not publication authority. | Only an approved publishing story may define the single publishing owner and its reconciliation contract. | Founder approval for external publishing plus architecture, provider, security, IMPLEMENT and TEST authority. | No publishing operation or parallel publisher is authorized. |
| Duplicate learning ownership | Learning must be grounded in real outcomes and retain its own governed lifecycle; workflow evidence is input, not organizational learning by itself. | Representative real execution data and a separately approved Learning Intelligence story satisfy the Product Constitution evidence boundary. | Founder product approval plus data/privacy, architecture, IMPLEMENT and TEST authority. | No learning adoption or synthetic-learning claim is authorized. |
