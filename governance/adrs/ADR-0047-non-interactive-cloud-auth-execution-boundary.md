# ADR-0047: Non-interactive cloud auth execution boundary

Status: Accepted

## Context

The release path failed after interactive reauthentication because subsequent
non-interactive Cloud SDK calls could not refresh tokens. This is infrastructure
debt, not a one-off release-script bug.

## Decision

MarketingLabAI release mutations must execute through a pinned non-interactive
cloud auth boundary:

1. Local approvals remain human-orchestration decisions only.
2. Cloud execution uses a pinned release executor service account.
3. Phase 1 uses local operator credentials only to impersonate that executor.
4. Phase 2 replaces local operator credentials with CI/CD Workload Identity.
5. Service-account key files are forbidden.
6. The release control plane must expose an auth doctor that proves this
   boundary before a mutation plan is applied.

## Consequences

- Browser-user auth failures can no longer appear halfway through a release
  mutation path.
- Operator identity and executor identity become separate evidence fields.
- Release commands are deterministic because the impersonated executor is part
  of the command contract.
- CI/CD can later adopt the same executor contract without changing the release
  state model.
