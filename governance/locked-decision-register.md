# MarketingLabAI Locked Decision Register

Status: Founder-ratified baseline — approved 2026-08-05 via PDR-0001

## Authority notation

- **Current:** Latest compatible locked decision.
- **Implemented:** Confirmed by the current repository or completed epic history.
- **Future:** Locked direction that is intentionally not yet implemented.
- **Governance:** A rule controlling how future work is assessed.

Conversation references use extracted chronological message numbers so the
decision can be traced back to its surrounding discussion.

## A. Product identity and scope

### LDR-001 — Core identity

**Status:** Current
**Sources:** 1128–1131, 1220–1223, 1571–1582

MarketingLabAI is a **Marketing Intelligence Operating System** and the **AI
Marketing Department for growing businesses**. It is not an AI copywriter,
prompt generator, social scheduler, CRM, ERP, accounting system, general AI
assistant, or executive operating system.

Its core mission is to help businesses plan, execute, optimize, and improve
marketing. Adjacent executive-intelligence capabilities may later exist as a
premium extension, but they must not displace the marketing core.

### LDR-002 — Primary customers

**Status:** Current
**Source:** 1571–1574

The primary market is small businesses, SMEs, entrepreneurs, marketing managers,
and agencies. Enterprise capability may grow later, but the core product must
first succeed for growing businesses.

### LDR-003 — Product promise

**Status:** Current
**Sources:** 1573–1580

Every paying customer should experience the promise:

> Spend less time marketing and achieve better marketing results.

Customers should feel that a capable marketing department is working behind the
scenes. AI is the engine, not the headline.

### LDR-004 — Mission and vision

**Status:** Current
**Sources:** 1220–1223, 1571–1580

Mission: make world-class marketing intelligence accessible to businesses of
every size, beginning with growing businesses.

Vision: become a trusted Marketing Intelligence Operating System that gives
businesses the knowledge, consistency, governance, execution support, and
continuous improvement of a high-performing marketing organization.

### LDR-005 — Product positioning

**Status:** Current
**Sources:** 1220–1223, 1579–1580

The customer-facing position is “a whole marketing team behind you,” not “an AI
writer.” Internally the system may use terms such as Marketing Brief, Prompt
Pack, Compliance Engine, and Campaign Planner. Externally it should use clear
outcome language such as Strategy, Brand Playbooks, Brand Review, and Marketing
Strategist.

The recovered candidate tagline is:

> The intelligence layer above the modern marketing stack.

This tagline is locked as Version 1.0 but explicitly remains open to future
improvement.

## B. Product constitution and commercial laws

### LDR-006 — Outcomes before features

**Status:** Current / Governance
**Sources:** 728–775, 1579–1580

Every landing page, pricing page, advertisement, demo, sales presentation, and
product surface must lead with the customer outcome. Technical features support
the promise; they are not the promise.

### LDR-007 — Complete experience at every tier

**Status:** Current / Governance
**Sources:** 1573–1580

Lower tiers must never be intentionally crippled. Every tier must deliver a
complete experience for its intended customer. Quality, correct compliance,
accurate analytics, and professional marketing output may not be withheld to
force an upgrade.

Higher tiers remove ceilings through scale, users, brands, storage,
collaboration, workflow depth, automation, analytics depth, governance,
integrations, and strategic intelligence.

Golden rule:

> Customers should upgrade because their business has grown, not because the
> lower tier was artificially made inadequate.

### LDR-008 — Founding pricing

**Status:** Current principle; exact packaging requires confirmation
**Sources:** 768–775

Launch prices are founding offers rather than permanent pricing. Recovered
prices were R399, R999, R2,499, and custom enterprise pricing. Future pricing
may evolve with product value, while early-customer trust must be protected by a
clear commercial policy.

### LDR-009 — Marketing maturity progression

**Status:** Current
**Sources:** 691–775

MarketingLabAI sells progression in marketing maturity rather than prompt counts
or token consumption. Product packaging must communicate increasing business
capability and organizational scale. Usage limits may manage costs, but must not
be the primary value proposition.

### LDR-010 — Marketing Intelligence Score

**Status:** Future
**Sources:** 728–733

A proprietary Marketing Intelligence Score should help customers understand
the completeness and maturity of their marketing system, guide improvement, and
communicate value. It may consider Company Brain completeness, voice, memory,
channels, automation, agents, analytics, compliance, optimization, and learning.

### LDR-011 — Customer success platform

**Status:** Future
**Sources:** 728–733

The future customer-success layer includes the Marketing Intelligence Score,
MarketingLabAI Academy, an in-product AI coach, guided walkthroughs,
context-sensitive help, a success centre, a voice-of-customer hub, and an
opt-in beta programme.

### LDR-012 — Product-led growth infrastructure

**Status:** Future
**Sources:** 891–895

Plans, subscriptions, billing status, entitlements, trials, usage controls,
promotional access, and feature flags belong to a dedicated subscription domain.
Other domains ask whether a tenant is entitled to act; they do not encode why.
Promotions and previews should be configuration rather than scattered code.

## C. Intelligence and domain architecture

### LDR-013 — Intelligence hierarchy

**Status:** Current / Partially implemented
**Sources:** 1089–1131

The enduring hierarchy is:

1. Company Intelligence
2. Customer Intelligence
3. Product Intelligence
4. Positioning Intelligence
5. Marketing Strategy Intelligence
6. Campaign and Generation
7. Compliance and Governance
8. Learning Intelligence
9. Executive Intelligence

No intelligence layer bypasses required lower layers without an explicit ADR.
Executive Intelligence is later expansion work, not a reason to leave the core
marketing roadmap.

### LDR-014 — Deterministic first

**Status:** Current / Governance
**Sources:** 1128–1131

The reasoning order is:

1. Verified source data
2. Deterministic calculations
3. Explicit rules
4. Structured AI reasoning
5. Generative output

Missing business context remains explicit and is never silently invented.
Generation is an output of structured intelligence, not a replacement for
domain design.

### LDR-015 — Company Brain authority

**Status:** Current / Implemented foundation
**Sources:** 178–180, 1128–1131

Company Brain is the structured source of business knowledge. It evolves by
adding intelligence domains rather than spawning parallel knowledge systems.
The AI must act from Company Brain context, never from an isolated prompt alone.

### LDR-016 — Prompt builders are renderers

**Status:** Current / Implemented
**Sources:** 1113–1131

Prompt builders format approved intelligence. They do not own strategy,
unsupported reasoning, persistence, or domain decisions. Business reasoning
belongs in domain builders and services.

### LDR-017 — Modular intelligence builders

**Status:** Current / Implemented pattern
**Sources:** 1113–1131

Major intelligence domains use modular builders with narrow responsibilities,
deterministic outputs, and composable sections. Exceptions require an ADR.

### LDR-018 — Learning follows real execution

**Status:** Current / Future implementation
**Sources:** 1128–1131

Learning engines depend on real campaign execution, analytics, customer
behaviour, compliance history, experiments, and business outcomes. The platform
must not fabricate synthetic learning before production evidence exists.

### LDR-019 — Provider neutrality

**Status:** Current / Implemented
**Sources:** 483–486, 923–1000, 1648–1649

AI providers and external platforms are replaceable adapters. Core domains must
not contain provider-specific classes or SDK concepts. Provider selection,
capability matching, normalized responses, audit metadata, and bootstrap belong
behind explicit contracts.

### LDR-020 — Connector isolation

**Status:** Current principle / Future implementation
**Sources:** 557–620, 633–636

Meta, Google, TikTok, LinkedIn, Shopify, WordPress, email, CRM, analytics, and
future platforms connect through adapters or a Connector SDK. External platform
semantics must not leak into core domain models.

### LDR-021 — Event-driven, decision-aware automation

**Status:** Future
**Sources:** 633–636

Automation is informed by intelligence and business events. The platform asks
whether an action should occur before determining whether it can occur.
Workflows support three trust modes:

- Advisor: recommend only.
- Copilot: prepare and await approval.
- Autopilot: execute inside user-defined guardrails.

Every execution feeds institutional knowledge. Humans define the guardrails.

### LDR-022 — Connected and Autonomous Marketing

**Status:** Future
**Sources:** 691–694

The long-term customer capability model has two major stages:

- **Connected Marketing:** integrations, analytics, publishing, scheduling,
  reporting, CRM, and commerce connectivity.
- **Autonomous Marketing:** decision-making, multi-agent orchestration,
  optimization, experimentation, continuous learning, and self-improving
  workflows.

Autonomous means observe, reason, decide, act, and learn—not merely “when X,
do Y.”

### LDR-023 — AI Cost Optimizer

**Status:** Future
**Source:** 712–713

The orchestration layer will eventually support cost-aware model routing,
provider fallback, prompt/semantic caching, tenant token and spend tracking,
budgets and alerts, ROI reporting, and evidence-driven model selection.

## D. Campaign and calendar boundaries

### LDR-024 — Campaign Planner boundary

**Status:** Current / Implemented
**Sources:** 1648–1649; ADR-0008; MLAI-025

Campaign Planner manages coordinated marketing work. It does not generate or
publish content and does not replace Marketing Brief. A Campaign Asset is a
deliverable, not a physical file. Campaign, asset, brief, generation, and
publishing lifecycles remain separate.

### LDR-025 — Marketing Brief relationship

**Status:** Current / Implemented
**Sources:** MLAI-024 and MLAI-025.4 history

A Campaign Plan may associate immutable, version-aware Marketing Brief
references without embedding or controlling Marketing Brief lifecycle. Governed
generation requires approved planning where a plan is supplied.

### LDR-026 — Immutable versioned business records

**Status:** Current / Implemented
**Sources:** Marketing Brief and Campaign Plan persistence epics

Approved planning and briefing records preserve immutable history through
explicit successor versions, tenant-scoped retrieval, ownership enforcement,
latest-version lookup, and history retrieval.

### LDR-027 — International Marketing Calendar architecture

**Status:** Current architecture / Future implementation
**Sources:** 1522–1527; ADR-0007; MLAI-026

The Marketing Calendar is the strategic planning layer for annual, quarterly,
monthly, campaign, review, business, seasonal, regional, and industry events.
It does not generate content, execute campaigns, evaluate compliance, or
publish.

Calendar and Campaign Planner precede individual Marketing Briefs. External
calendars are synchronization targets, never the source of truth. International
context is explicit: country, region, timezone, locale, and language. Weather is
advisory unless a customer explicitly configures an automation.

The architecture is locked now; implementation remains deferred to MLAI-026.

## E. Security constitution

### LDR-028 — Security by design

**Status:** Current / Governance
**Sources:** 859–862

Security is a first-class architectural requirement and part of every story,
not a launch-time retrofit. Features must consider authentication,
authorization, tenant isolation, least privilege, input validation, auditability,
secret handling, rate/resource controls, dependencies, backups, and recovery.

### LDR-029 — Tenant authorization

**Status:** Current / Partially implemented
**Sources:** 859–862

Supplied tenant and object identifiers are filters, never proof of permission.
Authenticated identity, tenant membership, role, ownership, and operation must
be verified at every protected boundary. Sensitive areas require cross-tenant
regression tests.

### LDR-030 — Security baseline and gates

**Status:** Future operational requirement
**Sources:** 859–862

The intended web/API baseline is OWASP ASVS Level 2 plus relevant AI/LLM
security verification. Security gates cover development foundation, closed beta,
production integrations, public launch, and continuous operations.

Real customer secrets, platform tokens, payment credentials, confidential
customer lists, and production credentials must not enter the system before the
appropriate security gate. Mature identity and secret-management systems are
preferred over custom authentication or plaintext application storage.

## F. Engineering constitution and delivery method

### LDR-031 — Production-grade from the beginning

**Status:** Current / Governance
**Sources:** recovered engineering-principle discussion and 1015–1042

Nexus products are built as commercial-grade systems designed to scale without
a painful rewrite. This requires explicit boundaries, tests, versioned
contracts, secure defaults, observability plans, safe migrations, rollback
paths, CI/CD discipline, and documentation. It does not justify premature
complexity.

### LDR-032 — Discover before designing

**Status:** Current / Governance
**Sources:** 1015–1020

Before major implementation, inventory the real subsystem, dependencies,
maturity, extension points, duplication, risks, and existing tests. Prefer
extension to parallel replacement. Replacement requires evidence and explicit
justification.

An ADR is required when a decision materially changes architecture; routine
story implementation does not need a ceremonial ADR for every edit.

### LDR-033 — Vertical slice before horizontal expansion

**Status:** Current / Governance
**Sources:** 972–975

After a foundation is production-capable, prove an end-to-end business workflow
before building more engines. Expand the Company Brain and other domains when a
real workflow requires new knowledge. Freeze stable components except for
defects or limitations revealed by integration.

### LDR-034 — Layered compliance

**Status:** Current / Implemented foundation
**Sources:** 972–975

Compliance evaluation proceeds through deterministic rules, AI-assisted review,
and human approval. AI is not the final legal authority.

### LDR-035 — Intelligence before interface

**Status:** Current / Governance
**Sources:** 557–560

Major capabilities exist as tested headless services before UI delivery. UI,
CLI, API, schedules, and integrations call shared application/domain services
instead of owning business logic.

### LDR-036 — Buyer-ready by default

**Status:** Current / Governance
**Sources:** 1041–1042

The system must remain understandable to an independent engineering team,
auditor, investor, or buyer. Architecture, decision history, IP provenance,
quality evidence, known risks, technical debt, roadmap, and continuation steps
must remain current.

### LDR-037 — Complete PowerShell delivery

**Status:** Current / Governance
**Sources:** 167–170, 309–310, 1351–1352, 1455–1456

MarketingLabAI’s operating environment is Windows PowerShell 5.1. User-facing
engineering instructions must be complete, self-contained, copy/paste-ready,
and include error handling, progress, verification, and a final summary. The
user must not be asked to locate individual files and manually assemble edits.

Repeated processes should become permanent tools. Scripts must use PowerShell
5.1-compatible encoding APIs and avoid unsupported encoding names.

### LDR-038 — Atomic story packages

**Status:** Current / Implemented through the MarketingLabAI story-package generator
**Sources:** 1351–1456 and MarketingLabAI story-package generator commits 710868c, 1e192e2, ada7c01

Engineering increments are small, coherent packages with installer, validator,
rollback capability, release/context information, and explicit payload. Avoid
giant embedded-code installers and per-installer repair patches. Systemic output
or compatibility problems are fixed in the generator so all future packages
inherit the improvement.

### LDR-039 — Story definition of done

**Status:** Current / Governance
**Sources:** 1351–1456 and completed MLAI-025 workflow

Each story ends with installation, compilation, focused tests, affected
regression tests, full-suite validation where appropriate, import validation,
Git whitespace validation, architecture/product review, documentation updates,
clean commit, push, and a clean synchronized repository.

### LDR-040 — Vision check and Rabbit Rule

**Status:** Current / Governance
**Sources:** 1571–1582

Every proposal is classified:

- **Core:** strengthens the Marketing Operating System; build in sequence.
- **Future:** aligned but not current; capture in backlog, ADR, or PDR.
- **Rabbit:** distracts from the core; reject or remove.

Any recommendation that expands beyond the agreed core must carry an explicit
vision warning.

### LDR-041 — Sprint review rhythm

**Status:** Current / Governance
**Sources:** 891–896, 1581–1582

Meaningful increments include engineering, architecture, security, product, and
founder reviews. Reviews test customer value, North Star alignment, scope,
monetizability, retention, technical debt, and evidence. Deferred debt and
business assumptions are recorded rather than left in memory.

## G. Long-term roadmap commitments

### LDR-042 — Core product pillars

**Status:** Future direction with partial implementation
**Sources:** 178–180

The enduring pillars are Company Brain, autonomous market research, decision
intelligence, campaign execution, performance memory and learning, executive
reporting, governance and human approval, and integrations. Executive reporting
must remain downstream of a successful marketing core.

### LDR-043 — Specialized marketing organization

**Status:** Future
**Sources:** 1089–1092, 1232–1235, 1579–1580

Intelligence engines and agents should represent clear real-world marketing
disciplines with owned knowledge, responsibilities, and collaboration contracts.
A Marketing Director/Orchestrator coordinates specialists rather than becoming
one giant all-purpose agent.

### LDR-044 — Reusable workflow library

**Status:** Future
**Sources:** 633–636

Composable workflows may become installable industry playbooks. They must use
the same intelligence, event, approval, learning, and connector architecture
rather than embedding platform-specific shortcuts.

### LDR-045 — Roadmap waves

**Status:** Current strategic sequencing
**Sources:** 1128–1131, reconciled with current implementation

Wave 1 establishes Customer, Product, Positioning, Strategy, and governed
campaign execution on top of completed Company/AI/governance foundations.

Wave 2 introduces real learning, experimentation, analytics, attribution,
forecasting, budget optimization, and executive support only after execution
data exists.

The exact story numbers must be maintained in the live roadmap rather than
copied from obsolete chat sprint numbering.

## H. Marketing decision doctrine

### LDR-046 — Evidence-to-learning marketing decision loop

**Status:** Current / Governance; partially implemented
**Source:** PDR-0003

MarketingLabAI's canonical marketing decision loop is:

1. verified company and market evidence;
2. customer segmentation;
3. target selection;
4. positioning;
5. coherent marketing-mix decisions;
6. objectives and strategy;
7. campaign planning and approved briefs;
8. governed generation;
9. independent compliance;
10. controlled execution;
11. measurement; and
12. evidence-backed learning and adaptation.

Customer value and an explicit business objective lead the loop. Research,
assumptions, uncertainty, and unknowns remain distinguishable. STP precedes
final positioning and strategy. Product, Price, Place, and Promotion form the
minimum marketing-mix lens; service contexts may add People, Process, and
Physical Evidence. Environmental analysis covers at least Political, Economic,
Social, and Technological factors and remains extensible.

Frameworks provide required decision coverage where relevant, not rigid forms.
Material factors may be recorded as irrelevant or unknown but may not be
silently omitted. Metrics identify a target, method, timeframe, and eventual
actual result. AI may assist analysis but may not invent research, positioning,
strategy, performance, or learning. Learning claims require real outcomes, and
humans retain governed approval authority.

### LDR-047 — Story repository integrity

**Status:** Current / Governance
**Source:** MLAI-029.6 repository-integrity audit

Every story must verify its baseline, allowlist intended paths, refuse unexpected
dirty paths, report staged and remaining work, classify every failure, run the
applicable focused and repository-wide gates, and verify clean local/remote
synchronization. A warning or failure may not be dismissed without an explicit
cause, impact, and treatment. The full controls are locked in
`governance/repository-integrity-protocol.md`.

### LDR-048 — Founder Design Partner boundary

**Status:** Current / Governance
**Source:** ADR-0019

Strand Auto Parts and Velani Wholesale are the approved Founder Design Partner
candidates. Their founder accounts may receive full feature access with billing disabled, but entitlement
does not grant customer-data permission. Real-data activation requires a new
founder-approved decision after privacy, identity, recovery, support, and data
boundary gates pass. Readiness never self-authorizes activation.

MLAI-030.1 requires each owner to sign up through trusted external
authentication and a business-specific invitation. Accounts are not manually
pre-created, and identity subjects may not be invented for convenience.
