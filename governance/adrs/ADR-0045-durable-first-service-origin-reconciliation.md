# ADR-0045: Durable First-Service Origin Reconciliation

Status: Accepted

## Context

The first private Cloud Run service cannot know its final service URL before the
service exists. MLAI-031.12 allowed a controlled bootstrap placeholder origin
for that first revision only. The startup inspection then correctly stopped
because the running service still advertised the bootstrap placeholder instead
of the real Cloud Run URL.

Treating that as a one-off operator patch would recreate the same failure for
future pilots. The release path needs a durable lifecycle state.

## Decision

Introduce `ORIGIN_RECONCILED` as the explicit transition between
`REVISION_CREATED` and `STARTUP_VERIFIED`.

The transition:

- uses the observed Cloud Run service URL from read-only inspection;
- renders a new digest-pinned manifest with the real private service origin;
- permits at most one Cloud Run service replacement when explicitly approved;
- forbids public IAM, secret-value reads, rebuilds, admission authority, and
  real-customer data;
- records machine-verifiable evidence before `STARTUP_VERIFIED` becomes
  eligible.

## Consequences

First-service bootstrap becomes a normal release lifecycle state, not a manual
recovery script. Future pilots follow the same paved path:

`REVISION_CREATED -> ORIGIN_RECONCILED -> STARTUP_VERIFIED`.

The release controller remains observational. Admission authority remains
external zero-trust Binary Authorization.

