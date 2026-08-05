# MarketingLabAI Current Handover

## Checkpoint

- Branch: `feature/tenant-architecture`
- Installation baseline: `229001a`
- Remote state before this story: synchronized with `origin/feature/tenant-architecture`
- Last completed product epic: MLAI-025 Campaign Planning Platform
- Last completed story: MLAI-027.4 Pilot API and Workflow Contract
- Validation target: focused API/security and complete regressions

## Product direction

MarketingLabAI is a Marketing Intelligence Operating System and the AI
Marketing Department for growing businesses. AI is the engine, not the
headline. PDR-0001 is the founder-ratified product direction. PDR-0002 keeps
MLAI-026 deferred while the secure private-pilot vertical slice is completed.

## Current implementation

MLAI-027.1 through MLAI-027.4 compose one canonical SQLite application,
verified Company, Customer, Product, and memory context, versioned Campaign
Plans and Marketing Briefs, provider-neutral generation, independent
compliance, trusted identity, default-deny tenant authorization, and an
authenticated pilot API contract.

The API exposes only context, approved generation, plan approval, brief
approval, and export authorization. Generation requires approved plan and
brief versions for the same tenant and brand. Identity-scoped idempotency makes
retries safe and stale lifecycle versions return explicit conflicts. Public
contracts do not expose repositories or provider request models.

Start with **MLAI-027.5 - Thin Pilot Workspace**.

## MLAI-027.5 constraints

- Build the workspace only over the pilot API contract; do not import raw
  repositories or `CanonicalApplication` into presentation code.
- Guide onboarding and show missing context explicitly.
- Support Campaign Plan and Marketing Brief review and explicit approval.
- Never offer generation without approved governance references.
- Display output, compliance findings, limitations, and audit metadata.
- Support revision and safe export; do not add direct publishing.
- Use synthetic data only. Real customer data remains prohibited until all
  MLAI-027.6 private-pilot gates pass.
- Preserve tenant isolation, lifecycle separation, provider neutrality, and
  deterministic-first reasoning.

## Current risks and debt

The major remaining gaps are the guided workspace, live identity-provider and
membership operations, hardened API deployment, privacy-safe logging, backup
and restore, monitoring, CI, and incident procedures. See the risk and
technical-debt registers for the controlled list.

## Next engineer's first action

Review ADR-0009 through ADR-0012 and design the thinnest guided workspace that
depends exclusively on `PilotApiService` or its JSON contract. Do not select a
publishing connector, admit real customer data, or bypass approval and
authorization boundaries.
