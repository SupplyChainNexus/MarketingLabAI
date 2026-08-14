# MLAI-031.16 - Release executor identity bootstrap

MLAI-031.16 closes the gap between the executor identity pinned by ADR-0047 and
the IAM state required to impersonate that identity. It does not grant general
release permissions.

## Paved sequence

1. Install locally with no Cloud CLI execution.
2. Commit, push and obtain CI.
3. Reauthenticate the pinned operator only if the read-only inspector reports
   that it is required.
4. Run `scripts/inspect_release_executor_identity.ps1` once.
5. Review and preserve the inspection evidence under ToolkitTemp.
6. Run `scripts/prepare_release_executor_identity_bootstrap.ps1` against that
   exact evidence.
7. Obtain plan-bound approval before any IAM mutation.
8. Apply no more actions than the approved plan contains.
9. Run `doctor-auth` after bootstrap and preserve its evidence.

## Fail-closed rules

- Missing executor identity is evidence, not an automatic creation trigger.
- Operator reauthentication never retries automatically.
- User-managed service-account keys block planning.
- The planner cannot execute gcloud.
- The plan may contain only service-account creation and the operator's Token
  Creator binding.
- Project-level roles, Workload Identity, Cloud Run, deployment and release
  state remain outside MLAI-031.16.
- Every artifact is written under `C:\Ai Projects\ToolkitTemp`.
