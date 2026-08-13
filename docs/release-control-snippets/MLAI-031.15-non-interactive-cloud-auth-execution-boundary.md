# MLAI-031.15 - Non-interactive cloud auth execution boundary

Release cloud execution must not depend directly on an interactive browser-user
token. Local human approval remains an orchestration input only. The actual
release executor is a pinned service account impersonated by the local operator
in Phase 1 and by CI/CD Workload Identity in Phase 2.

## Locked boundary

- No service-account key files.
- No release mutation without a passing non-interactive auth doctor.
- No release mutation command may omit `--impersonate-service-account`.
- Operator identity and executor identity must both be recorded in evidence.
- A browser login can refresh local operator credentials, but it is not release
  execution authority.
- If impersonation cannot be proven, the release stops before mutation.

## Phase 1

Local operator auth plus service-account impersonation:

- Operator: `info@supplychainnexus.co.za`
- Executor: `mlai-synthetic-release-executor@marketinglabai-identity-dev.iam.gserviceaccount.com`
- Project: `marketinglabai-identity-dev`

## Phase 2

CI/CD Workload Identity becomes the production-grade release execution path.
The same executor identity remains pinned, but the source principal changes
from local operator credentials to the configured CI identity provider.
