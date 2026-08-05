# MarketingLabAI Current Handover

## Checkpoint

- Branch: `feature/tenant-architecture`
- Ratified baseline: `db7a6c8`
- Remote state at selection: synchronized with `origin/feature/tenant-architecture`
- Last completed product epic: MLAI-025 Campaign Planning Platform
- Last completed governance work: continuity system and PDR-0001 ratification
- Last recorded validation: 683 Python tests; continuity regressions passed

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

Start with **MLAI-027.1 — Canonical Application Composition**.

## Mandatory first-story constraints

- Inspect and reuse existing services and repositories.
- Select one canonical runtime persistence path.
- Treat legacy JSON paths as migration or compatibility boundaries.
- Do not add a UI before the synthetic composed workflow passes.
- Do not introduce real customer data.
- Add an ADR for the application boundary and dependency direction.
- Preserve provider neutrality, tenant boundaries, lifecycle separation, and
  deterministic-first reasoning.

## Current risks and debt

See `governance/registers/risk-register.md` and
`governance/registers/technical-debt-register.md`. The primary risks are missing
identity/authorization, split runtime persistence, absent customer surface, and
absent pilot operations.

## Next engineer's first action

Create the MLAI-027.1 story manifest and source package only after reviewing
PDR-0002, the launch-readiness review, existing composition points, and relevant
accepted ADRs.
