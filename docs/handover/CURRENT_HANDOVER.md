# MarketingLabAI Current Handover

## Checkpoint

- Branch: `feature/tenant-architecture`
- Installation baseline: `e1eafaa`
- Remote state before this story: synchronized with `origin/feature/tenant-architecture`
- Last completed product epic: MLAI-025 Campaign Planning Platform
- Last completed story: MLAI-027.5 Thin Pilot Workspace
- Validation target: focused workspace/API/security and complete regressions

## Product direction

MarketingLabAI is a Marketing Intelligence Operating System and the AI
Marketing Department for growing businesses. AI is the engine, not the
headline. PDR-0001 through PDR-0003 remain authoritative. PDR-0003 locks the
evidence-to-learning marketing decision loop while preserving the established
intelligence dependency order. MLAI-026 remains deferred until the
private-pilot release gate is complete and evidence has been reviewed.

## Current implementation

MLAI-027.1 through MLAI-027.5 now form one guided synthetic pilot journey over
the canonical SQLite application, trusted identity, tenant authorization, and
retry-safe pilot API.

The framework-neutral workspace supports minimum verified Company, Customer,
and Product onboarding; explicit missing-context indicators; Campaign Plan and
Marketing Brief review, revision, and approval; approval-gated provider-neutral
generation; independent compliance results; limitations and audit metadata;
and authorized local JSON export without publishing. Presentation code depends
only on the pilot API contract and never on raw repositories.

Start with **MLAI-027.6 - Pilot Operations and Release Gate**.

Do not expand MLAI-027.6 into full Positioning, Strategy, environmental
intelligence, Analytics, or Learning implementation. PDR-0003 governs those
future capabilities, but the current story remains an operational release gate.

## MLAI-027.6 constraints

- Select and configure a hardened service runtime without changing domain or
  workspace dependency direction.
- Replace temporary synthetic credential entry with a live identity flow,
  hardened sessions, controlled membership bootstrap, and secret rotation.
- Add environment-managed secrets, TLS-aware configuration, rate limits, and
  privacy-safe structured logs.
- Add tested SQLite backup, restore, integrity, and migration procedures.
- Add readiness, monitoring, incident, and support runbooks.
- Add CI gates for regression, formatting, static analysis, migrations,
  continuity, and package validation.
- Complete the synthetic-pilot security test before proposing any real data.
- Keep direct publishing, billing, and public self-service deferred.

## Release prohibition

Real customer data remains prohibited. The workspace is not production-ready,
despite being functionally usable with synthetic data. Only the explicit
MLAI-027.6 private-pilot security and operational gates may change that status.

## Current risks and debt

The major remaining gaps are live identity and membership operations, hardened
hosting, privacy-safe logging, monitoring, rate limits, backup/restore, CI,
incident response, data handling, and support procedures. See the risk and
technical-debt registers.

## Next engineer's first action

Review PDR-0003, ADR-0009 through ADR-0013, the risk and debt registers, and
the MLAI-027.6 acceptance criteria. Begin with a release-gate matrix before
choosing hosting or identity vendors. Do not admit real customer data, add
publishing, or collapse deferred strategic intelligence into operations work.
