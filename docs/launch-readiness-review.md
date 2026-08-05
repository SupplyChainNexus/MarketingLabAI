# MarketingLabAI Launch Readiness and Vertical-Slice Review

## Review authority

- Repository checkpoint: `db7a6c8`
- Branch: `feature/tenant-architecture`
- Review date: 2026-08-05
- Product authority: PDR-0001, Product Constitution, ADR-0004, accepted domain ADRs
- Last supplied validation: 683 Python tests passed; continuity regressions passed

## Executive decision

MarketingLabAI has a strong, unusually disciplined domain and governance
foundation, but it is **not ready for a real-customer pilot or public launch**.
The decisive blocker is not Marketing Calendar. It is the absence of one
secure, composed, customer-usable workflow through the capabilities already
built.

Do not activate MLAI-026 next.

The recommended next epic is:

> **MLAI-027 — Secure Pilot Vertical Slice**

Its outcome is one governed journey from authenticated tenant onboarding to a
compliance-reviewed, auditable campaign asset that a pilot customer can review
and export. It must compose existing domains rather than introduce a parallel
application architecture.

## Readiness summary

| Area | Status | Evidence-based conclusion |
|---|---|---|
| Product direction | Ready | Founder-ratified constitution, PDR-0001, authority hierarchy, and takeover contract exist. |
| Domain correctness | Strong foundation | 683 tests cover provider orchestration, Company Brain, Customer Intelligence, briefs, planning, compliance, persistence, and tenant ownership. |
| Governed generation | Functional internally | Prompt Packs, approved Marketing Brief workflow, generation, compliance review, and audit metadata exist as services. |
| Campaign planning | Functional internally | Plans, assets, dependencies, lifecycle control, Marketing Brief association, and immutable persistence are implemented. |
| Customer entry point | Blocked | Only a developer CLI exists; `app/ui` contains no user experience and no HTTP application exists. |
| End-to-end composition | Blocked | The CLI uses legacy JSON services and `CampaignBrief`, bypassing the newer tenant-owned planning and brief workflow. |
| Authentication | Blocked | No login, identity, session, token validation, or external identity-provider adapter is implemented. |
| Authorization | Blocked | Tenant IDs are data filters; no authenticated principal establishes permission to act for a tenant. |
| Canonical persistence | Partial | SQLite repositories exist, but live CLI onboarding and generation still use older JSON storage paths. |
| Intelligence sequence | Partial | Company and Customer Intelligence exist; dedicated Product, Positioning, and Marketing Strategy domains do not. |
| Deployment and operations | Blocked | No deployable service, container/runtime definition, CI workflow, production health endpoint, structured monitoring, backup process, or incident evidence exists. |
| Commercial operations | Deferred correctly | Billing, subscription enforcement, entitlements, trials, and usage controls are not implemented. These are required before paid self-service launch, not before a controlled internal demo. |
| Publishing and integrations | Deferred correctly | No channel publishing exists. Export is sufficient for the first controlled pilot; direct publishing should follow trust and connector boundaries. |

## What is genuinely strong

### 1. The platform has real domain substance

The repository is not a thin AI wrapper. It contains provider-neutral AI
orchestration, context assembly, Company Brain, Customer Intelligence,
versioned Prompt Packs, Marketing Briefs, compliance guidance and evaluation,
Campaign Planning, asset dependency control, immutable persistence,
institutional memory, and tenant-aware repositories.

### 2. Deterministic and audit boundaries are credible

The code consistently validates ownership, lifecycle state, required context,
immutable versions, provider metadata, and compliance results. Campaign Plans
and Marketing Briefs remain separate, as required by ADR-0008.

### 3. Engineering quality is ahead of launch maturity

The test suite and governance system are substantial. This reduces the risk of
building the pilot slice, provided the new entry point composes these tested
services instead of bypassing them.

### 4. SQLite is suitable for the first controlled slice

SQLite is reasonable for a single-instance internal demonstration and a tightly
controlled low-concurrency pilot. It is not, by itself, evidence of readiness
for a horizontally scaled multi-user SaaS deployment.

## Critical launch findings

### LR-001 — No customer-usable application surface

`app/main.py` exposes an `argparse` CLI. `app/ui` is empty. No HTTP routing,
API contract, browser experience, or session boundary exists. A normal customer
cannot discover or operate the implemented domains.

**Classification:** Core blocker.

### LR-002 — The current CLI follows the legacy workflow

CLI onboarding uses file-backed `BrandService` and Business Intelligence
services. CLI campaign generation loads a legacy `CampaignBrief` and invokes
`CampaignEngine` directly. It does not require a Campaign Plan, an approved
versioned Marketing Brief, selected Prompt Pack, or independent compliance
review.

The newer governed workflow exists in
`app/marketing_brief/campaign_workflow.py`, but no user entry point composes it.

**Classification:** Core blocker and architecture-integration risk.

### LR-003 — Tenant ownership is not user authorization

The database models tenants and several repositories scope reads by tenant.
That is necessary but insufficient. No authenticated user or service principal
proves authority to act for the supplied tenant. PDR-0001 and LDR-029 correctly
state that tenant identifiers are filters, not permission evidence.

**Classification:** Core blocker before real customer data.

### LR-004 — Persistence has split authority

The repository contains relational SQLite repositories and older JSON-backed
services. The CLI continues using the older paths for key operations. Without a
canonical application composition root, customer records could be written to
one persistence system while newer workflows read another.

**Classification:** Core blocker.

### LR-005 — Intelligence hierarchy is incomplete

Company and Customer Intelligence foundations exist. Dedicated Product
Intelligence, Positioning Intelligence, and Marketing Strategy Intelligence are
not implemented. Current generation accepts product and offer facts through
brand and brief inputs, but this is not equivalent to governed intelligence at
those layers.

The private pilot must clearly describe its output as governed campaign support,
not claim that the full AI Marketing Department intelligence stack is complete.

**Classification:** Important product gap; minimum verified Product/Offer
context belongs inside the vertical slice, while the full domains remain on the
ordered roadmap.

### LR-006 — Production operations are absent

There is no deployable service definition, CI workflow, runtime environment
contract, monitoring, structured application health endpoint, backup/restore
procedure, rate limiting, or operational incident process. The existing health
command validates local folders, legacy storage, and optional Gemini access; it
does not validate the complete governed workflow.

**Classification:** Private-pilot blocker in minimum form; public-launch blocker
in full form.

### LR-007 — Governance registers are structurally present but empty

The risk and technical-debt registers have no entries despite identifiable
launch risks and split-persistence debt. Buyer-readiness governance exists, but
it has not yet captured current operational reality.

**Classification:** Documentation and governance gap.

### LR-008 — Packaging metadata is stale or incomplete

`pyproject.toml` declares version `0.4.1` and references `README.md`, but no root
README is present in the tracked archive. The product description also uses the
older “AI marketing operating system” wording rather than the ratified category.

**Classification:** Release hygiene gap, not the main blocker.

### LR-009 — Capability maturity documentation is stale

The capability map still records Customer Intelligence capabilities at level
0 even though their domain, SQLite persistence, context rendering, and tests
exist. It also does not represent the completed Campaign Planner accurately.

**Classification:** Governance accuracy gap.

## Customer-journey assessment

| Journey step | Current evidence | Pilot readiness |
|---|---|---|
| Discover and understand value | Product vision exists; no product surface | Not ready |
| Create account and sign in | No identity layer | Blocked |
| Establish tenant and brand | Commands and repositories exist; not securely exposed | Internal only |
| Supply Company Brain context | Interactive CLI exists; persistence paths are split | Internal only |
| Supply Customer Intelligence | Domain and repositories exist; no user workflow | Internal only |
| Supply verified product/offer facts | Basic brand/brief fields only | Partial |
| Create Campaign Plan | Strong domain/service/repository support | No user surface |
| Create and approve Marketing Brief | Strong domain/service/repository support | No user surface |
| Generate governed content | Strong internal workflow exists | Not composed for users |
| Review compliance | Strong internal pipeline exists | Not composed for users |
| Review, revise, approve, export | Persistence exists; no workspace workflow | Blocked |
| Publish to channels | Not implemented | Correctly deferred |
| Measure and learn | Not implemented; real evidence absent | Correctly deferred |

## Recommended launch target

The next target should be a **private, controlled pilot**, not public self-service
SaaS.

The pilot promise should be narrow and honest:

> A business can securely provide verified context, plan one campaign, approve
> its brief, generate one governed marketing asset, review compliance findings,
> and export the approved result with a complete audit trail.

This proves MarketingLabAI's core loop without prematurely adding publishing,
billing, analytics, autonomous learning, or a full Marketing Calendar.

## Recommended epic — MLAI-027 Secure Pilot Vertical Slice

### MLAI-027.1 — Canonical Application Composition

- Define one application composition root for tenant, brand, Company Brain,
  Customer Intelligence, Campaign Plan, Marketing Brief, Prompt Pack,
  generation, compliance, and audit persistence.
- Select SQLite repositories as canonical pilot persistence.
- Treat legacy JSON services as migration inputs or compatibility adapters, not
  competing runtime authority.
- Add an ADR for the application boundary and dependency direction.
- Prove the complete slice using synthetic data before adding an interface.

### MLAI-027.2 — Verified Product and Offer Context

- Establish the minimum Product Intelligence foundation required for truthful
  pilot generation: product/service identity, features, benefits, price facts,
  limitations, proof, warranties, availability, and prohibited claims.
- Preserve unknown values explicitly.
- Feed this context through the established context assembly and prompt
  boundaries.
- Do not attempt the entire future Product Intelligence roadmap in this story.

### MLAI-027.3 — Identity and Tenant Authorization

- Define an external-identity adapter boundary rather than custom password
  storage.
- Derive tenant access from the authenticated principal.
- Enforce authorization in application services, not only at the interface.
- Add cross-tenant denial tests for every exposed operation.
- Add audit events for identity, tenant, brand, approval, generation, and export.

### MLAI-027.4 — Pilot API and Workflow Contract

- Expose only the operations required by the vertical slice.
- Use request/response contracts that do not leak persistence or provider
  models.
- Implement lifecycle and optimistic-conflict handling.
- Add idempotency for creation and generation operations where retry is likely.
- Add an end-to-end API test using synthetic tenant data.

### MLAI-027.5 — Thin Pilot Workspace

- Provide guided onboarding and explicit missing-context indicators.
- Provide Campaign Plan, asset, and Marketing Brief review screens.
- Require visible approval before generation.
- Display generated content, compliance findings, evidence limitations, and
  audit metadata in customer language.
- Support revision and safe export; do not add direct publishing yet.

### MLAI-027.6 — Pilot Operations and Release Gate

- Add deployment/runtime configuration and secret management.
- Add database backup and tested restore for the pilot environment.
- Add health/readiness checks for database, migrations, provider configuration,
  and the composed workflow.
- Add structured logs without leaking prompts, secrets, or customer data.
- Add CI gates, dependency review, operational runbook, privacy/data-handling
  notes, and incident procedure.
- Run a synthetic pilot, then an explicitly authorized controlled customer
  pilot only after the security gate passes.

## Explicitly not in MLAI-027

- Marketing Calendar implementation
- Direct social, advertising, email, or CMS publishing
- Autonomous execution
- Performance learning or attribution
- Billing and public self-service subscription purchase
- Marketing Intelligence Score
- Full Positioning or Marketing Strategy engines
- Executive Intelligence

These remain aligned future work. Adding them now would weaken the vertical
slice and delay customer evidence.

## Required ADRs and governance updates

Before implementation:

1. Record the canonical application and interface boundary.
2. Record the identity-provider and tenant-authorization boundary.
3. Record the pilot deployment and data-protection model.
4. Populate risk and technical-debt registers with LR-001 through LR-009.
5. Refresh the capability map from implementation evidence.
6. Update `CURRENT_HANDOVER.md` from `6da6157` to the ratified checkpoint and
   selected epic.

## Pilot release gates

The private pilot may accept real customer data only when all of the following
are true:

- Identity and authorization are enforced and cross-tenant tests pass.
- The canonical workflow no longer depends on the legacy CLI persistence path.
- Secrets are outside source and managed by the deployment environment.
- Backup and restore are tested.
- Data handling, deletion, retention, and audit behaviour are documented.
- The complete vertical-slice test passes with synthetic data.
- Provider and model audit data are preserved.
- Compliance findings and missing-context limitations are visible.
- Logs do not expose secrets or sensitive customer content.
- Risk and technical-debt registers reflect accepted pilot limitations.

## Recommendation to the founder

Approve MLAI-027 as the next epic and keep MLAI-026 deferred. Build the smallest
secure customer journey over the architecture already created. This is the
point where MarketingLabAI should stop proving isolated components and start
proving that those components deliver one coherent customer outcome.
