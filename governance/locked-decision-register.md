# MarketingLabAI Locked Decision Register

Status: Recovered draft â€” awaiting founder approval

## Authority notation

- **Current:** Latest compatible locked decision.
- **Implemented:** Confirmed by the current repository or completed epic history.
- **Future:** Locked direction that is intentionally not yet implemented.
- **Governance:** A rule controlling how future work is assessed.

Conversation references use extracted chronological message numbers so the
decision can be traced back to its surrounding discussion.

## A. Product identity and scope

### LDR-001 â€” Core identity

**Status:** Current
**Sources:** 1128â€“1131, 1220â€“1223, 1571â€“1582

MarketingLabAI is a **Marketing Intelligence Operating System** and the **AI
Marketing Department for growing businesses**. It is not an AI copywriter,
prompt generator, social scheduler, CRM, ERP, accounting system, general AI
assistant, or executive operating system.

Its core mission is to help businesses plan, execute, optimize, and improve
marketing. Adjacent executive-intelligence capabilities may later exist as a
premium extension, but they must not displace the marketing core.

### LDR-002 â€” Primary customers

**Status:** Current
**Source:** 1571â€“1574

The primary market is small businesses, SMEs, entrepreneurs, marketing managers,
and agencies. Enterprise capability may grow later, but the core product must
first succeed for growing businesses.

### LDR-003 â€” Product promise

**Status:** Current
**Sources:** 1573â€“1580

Every paying customer should experience the promise:

> Spend less time marketing and achieve better marketing results.

Customers should feel that a capable marketing department is working behind the
scenes. AI is the engine, not the headline.

### LDR-004 â€” Mission and vision

**Status:** Current
**Sources:** 1220â€“1223, 1571â€“1580

Mission: make world-class marketing intelligence accessible to businesses of
every size, beginning with growing businesses.

Vision: become a trusted Marketing Intelligence Operating System that gives
businesses the knowledge, consistency, governance, execution support, and
continuous improvement of a high-performing marketing organization.

### LDR-005 â€” Product positioning

**Status:** Current
**Sources:** 1220â€“1223, 1579â€“1580

The customer-facing position is â€œa whole marketing team behind you,â€ not â€œan AI
writer.â€ Internally the system may use terms such as Marketing Brief, Prompt
Pack, Compliance Engine, and Campaign Planner. Externally it should use clear
outcome language such as Strategy, Brand Playbooks, Brand Review, and Marketing
Strategist.

The recovered candidate tagline is:

> The intelligence layer above the modern marketing stack.

This tagline is locked as Version 1.0 but explicitly remains open to future
improvement.

## B. Product constitution and commercial laws

### LDR-006 â€” Outcomes before features

**Status:** Current / Governance
**Sources:** 728â€“775, 1579â€“1580

Every landing page, pricing page, advertisement, demo, sales presentation, and
product surface must lead with the customer outcome. Technical features support
the promise; they are not the promise.

### LDR-007 â€” Complete experience at every tier

**Status:** Current / Governance
**Sources:** 1573â€“1580

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

### LDR-008 â€” Founding pricing

**Status:** Current principle; exact packaging requires confirmation
**Sources:** 768â€“775

Launch prices are founding offers rather than permanent pricing. Recovered
prices were R399, R999, R2,499, and custom enterprise pricing. Future pricing
may evolve with product value, while early-customer trust must be protected by a
clear commercial policy.

### LDR-009 â€” Marketing maturity progression

**Status:** Current
**Sources:** 691â€“775

MarketingLabAI sells progression in marketing maturity rather than prompt counts
or token consumption. Product packaging must communicate increasing business
capability and organizational scale. Usage limits may manage costs, but must not
be the primary value proposition.

### LDR-010 â€” Marketing Intelligence Score

**Status:** Future
**Sources:** 728â€“733

A proprietary Marketing Intelligence Score should help customers understand
the completeness and maturity of their marketing system, guide improvement, and
communicate value. It may consider Company Brain completeness, voice, memory,
channels, automation, agents, analytics, compliance, optimization, and learning.

### LDR-011 â€” Customer success platform

**Status:** Future
**Sources:** 728â€“733

The future customer-success layer includes the Marketing Intelligence Score,
MarketingLabAI Academy, an in-product AI coach, guided walkthroughs,
context-sensitive help, a success centre, a voice-of-customer hub, and an
opt-in beta programme.

### LDR-012 â€” Product-led growth infrastructure

**Status:** Future
**Sources:** 891â€“895

Plans, subscriptions, billing status, entitlements, trials, usage controls,
promotional access, and feature flags belong to a dedicated subscription domain.
Other domains ask whether a tenant is entitled to act; they do not encode why.
Promotions and previews should be configuration rather than scattered code.

## C. Intelligence and domain architecture

### LDR-013 â€” Intelligence hierarchy

**Status:** Current / Partially implemented
**Sources:** 1089â€“1131

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

### LDR-014 â€” Deterministic first

**Status:** Current / Governance
**Sources:** 1128â€“1131

The reasoning order is:

1. Verified source data
2. Deterministic calculations
3. Explicit rules
4. Structured AI reasoning
5. Generative output

Missing business context remains explicit and is never silently invented.
Generation is an output of structured intelligence, not a replacement for
domain design.

### LDR-015 â€” Company Brain authority

**Status:** Current / Implemented foundation
**Sources:** 178â€“180, 1128â€“1131

Company Brain is the structured source of business knowledge. It evolves by
adding intelligence domains rather than spawning parallel knowledge systems.
The AI must act from Company Brain context, never from an isolated prompt alone.

### LDR-016 â€” Prompt builders are renderers

**Status:** Current / Implemented
**Sources:** 1113â€“1131

Prompt builders format approved intelligence. They do not own strategy,
unsupported reasoning, persistence, or domain decisions. Business reasoning
belongs in domain builders and services.

### LDR-017 â€” Modular intelligence builders

**Status:** Current / Implemented pattern
**Sources:** 1113â€“1131

Major intelligence domains use modular builders with narrow responsibilities,
deterministic outputs, and composable sections. Exceptions require an ADR.

### LDR-018 â€” Learning follows real execution

**Status:** Current / Future implementation
**Sources:** 1128â€“1131

Learning engines depend on real campaign execution, analytics, customer
behaviour, compliance history, experiments, and business outcomes. The platform
must not fabricate synthetic learning before production evidence exists.

### LDR-019 â€” Provider neutrality

**Status:** Current / Implemented
**Sources:** 483â€“486, 923â€“1000, 1648â€“1649

AI providers and external platforms are replaceable adapters. Core domains must
not contain provider-specific classes or SDK concepts. Provider selection,
capability matching, normalized responses, audit metadata, and bootstrap belong
behind explicit contracts.

### LDR-020 â€” Connector isolation

**Status:** Current principle / Future implementation
**Sources:** 557â€“620, 633â€“636

Meta, Google, TikTok, LinkedIn, Shopify, WordPress, email, CRM, analytics, and
future platforms connect through adapters or a Connector SDK. External platform
semantics must not leak into core domain models.

### LDR-021 â€” Event-driven, decision-aware automation

**Status:** Future
**Sources:** 633â€“636

Automation is informed by intelligence and business events. The platform asks
whether an action should occur before determining whether it can occur.
Workflows support three trust modes:

- Advisor: recommend only.
- Copilot: prepare and await approval.
- Autopilot: execute inside user-defined guardrails.

Every execution feeds institutional knowledge. Humans define the guardrails.

### LDR-022 â€” Connected and Autonomous Marketing

**Status:** Future
**Sources:** 691â€“694

The long-term customer capability model has two major stages:

- **Connected Marketing:** integrations, analytics, publishing, scheduling,
  reporting, CRM, and commerce connectivity.
- **Autonomous Marketing:** decision-making, multi-agent orchestration,
  optimization, experimentation, continuous learning, and self-improving
  workflows.

Autonomous means observe, reason, decide, act, and learnâ€”not merely â€œwhen X,
do Y.â€

### LDR-023 â€” AI Cost Optimizer

**Status:** Future
**Source:** 712â€“713

The orchestration layer will eventually support cost-aware model routing,
provider fallback, prompt/semantic caching, tenant token and spend tracking,
budgets and alerts, ROI reporting, and evidence-driven model selection.

## D. Campaign and calendar boundaries

### LDR-024 â€” Campaign Planner boundary

**Status:** Current / Implemented
**Sources:** 1648â€“1649; ADR-0008; MLAI-025

Campaign Planner manages coordinated marketing work. It does not generate or
publish content and does not replace Marketing Brief. A Campaign Asset is a
deliverable, not a physical file. Campaign, asset, brief, generation, and
publishing lifecycles remain separate.

### LDR-025 â€” Marketing Brief relationship

**Status:** Current / Implemented
**Sources:** MLAI-024 and MLAI-025.4 history

A Campaign Plan may associate immutable, version-aware Marketing Brief
references without embedding or controlling Marketing Brief lifecycle. Governed
generation requires approved planning where a plan is supplied.

### LDR-026 â€” Immutable versioned business records

**Status:** Current / Implemented
**Sources:** Marketing Brief and Campaign Plan persistence epics

Approved planning and briefing records preserve immutable history through
explicit successor versions, tenant-scoped retrieval, ownership enforcement,
latest-version lookup, and history retrieval.

### LDR-027 â€” International Marketing Calendar architecture

**Status:** Current architecture / Future implementation
**Sources:** 1522â€“1527; ADR-0007; MLAI-026

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

### LDR-028 â€” Security by design

**Status:** Current / Governance
**Sources:** 859â€“862

Security is a first-class architectural requirement and part of every story,
not a launch-time retrofit. Features must consider authentication,
authorization, tenant isolation, least privilege, input validation, auditability,
secret handling, rate/resource controls, dependencies, backups, and recovery.

### LDR-029 â€” Tenant authorization

**Status:** Current / Partially implemented
**Sources:** 859â€“862

Supplied tenant and object identifiers are filters, never proof of permission.
Authenticated identity, tenant membership, role, ownership, and operation must
be verified at every protected boundary. Sensitive areas require cross-tenant
regression tests.

### LDR-030 â€” Security baseline and gates

**Status:** Future operational requirement
**Sources:** 859â€“862

The intended web/API baseline is OWASP ASVS Level 2 plus relevant AI/LLM
security verification. Security gates cover development foundation, closed beta,
production integrations, public launch, and continuous operations.

Real customer secrets, platform tokens, payment credentials, confidential
customer lists, and production credentials must not enter the system before the
appropriate security gate. Mature identity and secret-management systems are
preferred over custom authentication or plaintext application storage.

## F. Engineering constitution and delivery method

### LDR-031 â€” Production-grade from the beginning

**Status:** Current / Governance
**Sources:** recovered engineering-principle discussion and 1015â€“1042

Nexus products are built as commercial-grade systems designed to scale without
a painful rewrite. This requires explicit boundaries, tests, versioned
contracts, secure defaults, observability plans, safe migrations, rollback
paths, CI/CD discipline, and documentation. It does not justify premature
complexity.

### LDR-032 â€” Discover before designing

**Status:** Current / Governance
**Sources:** 1015â€“1020

Before major implementation, inventory the real subsystem, dependencies,
maturity, extension points, duplication, risks, and existing tests. Prefer
extension to parallel replacement. Replacement requires evidence and explicit
justification.

An ADR is required when a decision materially changes architecture; routine
story implementation does not need a ceremonial ADR for every edit.

### LDR-033 â€” Vertical slice before horizontal expansion

**Status:** Current / Governance
**Sources:** 972â€“975

After a foundation is production-capable, prove an end-to-end business workflow
before building more engines. Expand the Company Brain and other domains when a
real workflow requires new knowledge. Freeze stable components except for
defects or limitations revealed by integration.

### LDR-034 â€” Layered compliance

**Status:** Current / Implemented foundation
**Sources:** 972â€“975

Compliance evaluation proceeds through deterministic rules, AI-assisted review,
and human approval. AI is not the final legal authority.

### LDR-035 â€” Intelligence before interface

**Status:** Current / Governance
**Sources:** 557â€“560

Major capabilities exist as tested headless services before UI delivery. UI,
CLI, API, schedules, and integrations call shared application/domain services
instead of owning business logic.

### LDR-036 â€” Buyer-ready by default

**Status:** Current / Governance
**Sources:** 1041â€“1042

The system must remain understandable to an independent engineering team,
auditor, investor, or buyer. Architecture, decision history, IP provenance,
quality evidence, known risks, technical debt, roadmap, and continuation steps
must remain current.

### LDR-037 â€” Complete PowerShell delivery

**Status:** Current / Governance
**Sources:** 167â€“170, 309â€“310, 1351â€“1352, 1455â€“1456

MarketingLabAIâ€™s operating environment is Windows PowerShell 5.1. User-facing
engineering instructions must be complete, self-contained, copy/paste-ready,
and include error handling, progress, verification, and a final summary. The
user must not be asked to locate individual files and manually assemble edits.

Repeated processes should become permanent tools. Scripts must use PowerShell
5.1-compatible encoding APIs and avoid unsupported encoding names.

### LDR-038 â€” Atomic story packages

**Status:** Current / Implemented through the MarketingLabAI story-package generator
**Sources:** 1351â€“1456 and MarketingLabAI story-package generator commits 710868c, 1e192e2, ada7c01

Engineering increments are small, coherent packages with installer, validator,
rollback capability, release/context information, and explicit payload. Avoid
giant embedded-code installers and per-installer repair patches. Systemic output
or compatibility problems are fixed in the generator so all future packages
inherit the improvement.

### LDR-039 â€” Story definition of done

**Status:** Current / Governance
**Sources:** 1351â€“1456 and completed MLAI-025 workflow

Each story ends with installation, compilation, focused tests, affected
regression tests, full-suite validation where appropriate, import validation,
Git whitespace validation, architecture/product review, documentation updates,
clean commit, push, and a clean synchronized repository.

### LDR-040 â€” Vision check and Rabbit Rule

**Status:** Current / Governance
**Sources:** 1571â€“1582

Every proposal is classified:

- **Core:** strengthens the Marketing Operating System; build in sequence.
- **Future:** aligned but not current; capture in backlog, ADR, or PDR.
- **Rabbit:** distracts from the core; reject or remove.

Any recommendation that expands beyond the agreed core must carry an explicit
vision warning.

### LDR-041 â€” Sprint review rhythm

**Status:** Current / Governance
**Sources:** 891â€“896, 1581â€“1582

Meaningful increments include engineering, architecture, security, product, and
founder reviews. Reviews test customer value, North Star alignment, scope,
monetizability, retention, technical debt, and evidence. Deferred debt and
business assumptions are recorded rather than left in memory.

## G. Long-term roadmap commitments

### LDR-042 â€” Core product pillars

**Status:** Future direction with partial implementation
**Sources:** 178â€“180

The enduring pillars are Company Brain, autonomous market research, decision
intelligence, campaign execution, performance memory and learning, executive
reporting, governance and human approval, and integrations. Executive reporting
must remain downstream of a successful marketing core.

### LDR-043 â€” Specialized marketing organization

**Status:** Future
**Sources:** 1089â€“1092, 1232â€“1235, 1579â€“1580

Intelligence engines and agents should represent clear real-world marketing
disciplines with owned knowledge, responsibilities, and collaboration contracts.
A Marketing Director/Orchestrator coordinates specialists rather than becoming
one giant all-purpose agent.

### LDR-044 â€” Reusable workflow library

**Status:** Future
**Sources:** 633â€“636

Composable workflows may become installable industry playbooks. They must use
the same intelligence, event, approval, learning, and connector architecture
rather than embedding platform-specific shortcuts.

### LDR-045 â€” Roadmap waves

**Status:** Current strategic sequencing
**Sources:** 1128â€“1131, reconciled with current implementation

Wave 1 establishes Customer, Product, Positioning, Strategy, and governed
campaign execution on top of completed Company/AI/governance foundations.

Wave 2 introduces real learning, experimentation, analytics, attribution,
forecasting, budget optimization, and executive support only after execution
data exists.

The exact story numbers must be maintained in the live roadmap rather than
copied from obsolete chat sprint numbering.
