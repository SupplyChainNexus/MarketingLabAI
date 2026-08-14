# ADR-0049: Release Executor Identity Bootstrap

Status: Accepted

## Context

ADR-0047 pins non-interactive release execution to
`mlai-synthetic-release-executor@marketinglabai-identity-dev.iam.gserviceaccount.com`,
with the local operator using service-account impersonation during Phase 1 and
CI/CD Workload Identity during Phase 2. The first auth doctor proved that the
pinned identity was not yet impersonable and reported that the service account
could not be found.

The attempted follow-up inspection used ad hoc PowerShell commands before an
MLAI-031.16 package existed. It also encountered expired operator credentials.
Neither failure established the executor's current IAM state, and neither
authorized an IAM mutation.

## Decision

The release executor identity is bootstrapped through two evidence-separated
operations:

1. A canonical read-only discovery command uses the pinned operator account to
   inspect the project, executor service account, executor IAM policy,
   user-managed keys and existing project roles.
2. A separate deterministic planner consumes the stored inspection evidence and
   may propose only the missing identity bootstrap actions:
   - create the pinned executor service account; and
   - grant the pinned operator `roles/iam.serviceAccountTokenCreator` on that
     service account.

Planning does not execute the Cloud CLI or modify IAM. Applying any proposed
action requires exact plan-bound authorization. Service-account key files remain
forbidden. Operator reauthentication is interactive local credential
maintenance, is never automatic, and is not IAM or release authority.

The identity bootstrap plan does not grant project-level release permissions.
The executor's Cloud Run, read-only preflight and runtime-service-account
permissions require a separate evidence-bound least-privilege authorization.
Identity existence and impersonability must not be mistaken for release
authorization.

## Consequences

- Missing service-account state becomes a valid discovery result instead of an
  unclassified tool failure.
- Expired operator credentials stop with a specific reauthentication-required
  classification and no automatic retry.
- The plan is bound to inspection evidence, Git commit, operator, project and
  executor identity.
- Existing user-managed service-account keys block planning and require a
  separate security response.
- At most two IAM mutations can appear in an MLAI-031.16 bootstrap plan.
- Phase 2 Workload Identity remains outside this story.
- This ADR authorizes no cloud inspection, IAM mutation, service-account
  creation, key creation, deployment or release-state change by itself.
