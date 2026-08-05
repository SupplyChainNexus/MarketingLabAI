# MarketingLabAI Current Handover

## Checkpoint

- Branch: `feature/tenant-architecture`
- Current implementation checkpoint: `ee5da24`
- Remote state: synchronized with `origin/feature/tenant-architecture`
- Last completed product epic: MLAI-025 Campaign Planning Platform
- Last completed story: MLAI-027.2 Verified Product and Offer Context
- Last recorded validation: MLAI-027.2 focused and complete regressions passed

## Product direction

MarketingLabAI is a Marketing Intelligence Operating System and the AI
Marketing Department for growing businesses. AI is the engine, not the
headline. PDR-0001 is the founder-ratified product direction.

## Launch-readiness decision

The `db7a6c8` review found strong tested domains but no secure customer-usable
journey. The CLI still exposes legacy JSON-backed onboarding and campaign
generation rather than the newer tenant-owned governed workflow.

PDR-0002 approves MLAI-027 Secure Pilot Vertical Slice as the next epic. MLAI-026
Marketing Calendar remains deferred.

## Active epic

MLAI-027 will compose one private-pilot journey from trusted tenant context and
verified intelligence through Campaign Plan, approved Marketing Brief,
governed generation, independent compliance review, and safe export.

MLAI-027.1 and MLAI-027.2 are complete. The canonical application root composes one SQLite
database, tenant and intelligence repositories, Campaign Plans, Marketing
Briefs, Prompt Packs, provider-neutral generation, independent compliance, and
an explicit campaign-artifact boundary. Company, Customer, verified Product,
and memory context are included through distinct provider prompt boundaries and
request audit metadata.

Start with **MLAI-027.3 - Identity and Tenant Authorization**.

## MLAI-027.3 constraints

- Establish trusted identity and tenant authorization before real customer data.
- Deny cross-tenant access at application-service boundaries.
- Extend the canonical application rather than creating an alternate runtime.
- Keep legacy JSON paths as migration or compatibility boundaries.
- Do not add an API or UI.
- Do not introduce real customer data.
- Add an ADR for identity, authorization, and dependency direction.
- Preserve provider neutrality, tenant boundaries, lifecycle separation, and
  deterministic-first reasoning.

## Current risks and debt

See `governance/registers/risk-register.md` and
`governance/registers/technical-debt-register.md`. The primary risks are missing
identity/authorization, incomplete Positioning and Strategy Intelligence, remaining
legacy compatibility paths, absent customer surface, and absent pilot
operations.

## Next engineer's first action

Review ADR-0009, ADR-0010, and the synthetic canonical workflow, then implement
MLAI-027.3 through the canonical application composition root. Do not admit real
customer data, add an interface, or treat caller-supplied tenant IDs as
authorization evidence.
