# MarketingLabAI Current Handover

## Checkpoint

- Branch: `feature/tenant-architecture`
- Installation baseline: `3fc25dc`
- Remote state before this story: synchronized
- Last completed epic: MLAI-029 Marketing Strategy Intelligence
- Active epic: MLAI-030 Founder Design Partner Onboarding
- Active story: MLAI-030.2 External Identity Deployment and Signup Experience

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

The Repository Integrity Protocol is now locked for every future story:
baseline and scope verification, tracked/untracked/staged reporting, failure
classification, complete applicable quality gates, no remaining intended paths,
and clean local/remote synchronization are mandatory.

## Locked MLAI-029 sequence

1. MLAI-029.1 Strategy Intelligence Foundation
2. MLAI-029.2 Situation and Opportunity Synthesis
3. MLAI-029.3 Objectives and Strategic Choices
4. MLAI-029.4 Marketing Mix and Measurement
5. MLAI-029.5 Governed Workflow Integration
6. MLAI-029.6 Client-Facing Strategy Workspace and Design-Partner Readiness

## Release state

The customer pilot remains explicitly founder-frozen. Synthetic evidence is
not market validation or learning. A controlled design-partner pilot is now the
next necessary product-validation checkpoint, but readiness is not activation.
Real customer data still requires a new founder-approved pilot decision,
legal/privacy choices, deployed identity, recovery rehearsal, support ownership,
and accepted data boundaries.

## Next engineer action

Install and validate the reconciled MLAI-030.2 package. Then create a controlled
Google Cloud project under the existing Workspace organization, enable Identity
Platform, configure only local environment values, enable audit logs and budget
alerts, and rehearse synthetic signup and recovery. Do not enable SMS, send
founder invitations, or enable real customer data until the remaining onboarding
and activation gates are approved.
