# MarketingLabAI Current Handover

## Checkpoint

- Branch: `feature/tenant-architecture`
- Commit: `6da6157`
- Remote state: synchronized with `origin/feature/tenant-architecture`
- Repository state at handover: clean
- Last completed epic: MLAI-025 Campaign Planning Platform
- Last recorded validation: 69 focused tests and 683 complete-suite tests passed

## Product direction

MarketingLabAI is a Marketing Intelligence Operating System and the AI
Marketing Department for growing businesses. It must help customers spend less
time marketing and achieve better marketing results. AI is the engine, not the
headline.

## Implemented checkpoint

MLAI-025 provides a provider-neutral Campaign Planner with deterministic plan
and asset validation, lifecycle control, dependency ordering, Marketing Brief
workflow integration, audit references, and immutable tenant-scoped versioned
persistence.

## Immediate continuation decision

MLAI-026 International Marketing Calendar Intelligence is architecturally
defined and deferred pending an explicit launch-priority review. Campaign
Planner completion satisfies its technical dependency, but completion does not
automatically authorize implementation. Review ADR-0007 and current commercial
launch requirements before activating MLAI-026.

## Known governance work

- Reconcile the stale opening and priority language in `docs/product_vision.md`.
- Refresh capability maturity from the implemented repository; do not trust old
  sprint numbering.
- Confirm canonical subscription tier names before encoding them.
- Treat recovered founding prices as historical candidates until commercial
  costs and policy are reviewed.
- Preserve Marketing Intelligence Score as a future hypothesis requiring an
  evidence model, explainability, validation, and anti-gaming rules.
- Inventory security governance before assigning a new ADR number.

## Non-negotiable boundaries

- Intelligence hierarchy and deterministic-first reasoning
- Explicit missing context and evidence-grounded learning
- Provider neutrality and connector isolation
- Tenant isolation, auditability, least privilege, and human accountability
- Separate campaign, asset, brief, generation, calendar, publishing, and
  learning lifecycles
- Generator-level fixes instead of recurring package repair patches
- Complete PowerShell 5.1-compatible owner instructions

## Next engineer's first action

Run the handover regression test, review the founder-decision queue in the
locked-decision register, and perform a launch-priority review before opening
the next implementation story.
