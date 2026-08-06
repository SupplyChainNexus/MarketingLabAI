# MarketingLabAI Current Handover

## Checkpoint

- Branch: `feature/tenant-architecture`
- Installation baseline: `54cb7c9`
- Remote state before this story: synchronized
- Last completed epic: MLAI-029 Marketing Strategy Intelligence
- Active epic: MLAI-030 Founder Design Partner Onboarding
- Last completed story: MLAI-030.4 Production Identity and Security Readiness
- Active story: MLAI-030.5 Recovery, Monitoring and Support Readiness

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

## Next engineer action

Complete MLAI-030.5 validation and install it only on verified baseline
`54cb7c9`. Execute and record each controlled rehearsal, including failures,
then begin MLAI-030.6 Design-Partner Acceptance Rehearsal. Use approved test
identities and invented records only. Do not publish the OAuth app, send
external invitations, enable customer data, or fill unset privacy choices
without a new founder decision.
