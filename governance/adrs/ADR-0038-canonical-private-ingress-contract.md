# ADR-0038: Canonical private ingress contract

## Status

Accepted.

## Decision

The canonical private-synthetic Cloud Run manifest must contain exactly one
`run.googleapis.com/ingress` annotation whose value is
`internal-and-cloud-load-balancing`.

The manifest validator and the first-service bootstrap planner share this value
as one enforced contract. Public (`all`), internal-only, missing, duplicated or
malformed ingress values fail before rendering or deployment.

The incomplete run `run-20260810T210334Z-6f68e3ad` and image built from commit
`9630fad977e0e21b56a2c701ca45bdfa404fb088` remain historical and non-deployable.
They are not repaired, backfilled, migrated or used as authority. After this
correction is committed and CI passes, deployment resumes only through a fresh
commit-bound image and a fresh observational release run.

## Consequences

- Direct `*.run.app` access cannot bypass the intended load-balancer boundary.
- Cloud Armor and external load-balancer work remain later, separately
  authorized controls; this change does not create them.
- No historical ledger or cloud resource is changed by installation or validation.
