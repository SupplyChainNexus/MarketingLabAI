# ADR-0044: First-Service Origin Bootstrap Correction

## Status

Accepted

## Context

The canonical Cloud Run service `marketinglabai-velani-pilot` does not exist
yet. Cloud Run assigns `status.url` only after service creation, but the
rendered private manifest requires `MLAI_PUBLIC_ORIGIN`. Requiring a real
Cloud Run URL before the first revision would force a guessed value.

## Decision

Revision preparation may use the named bootstrap origin
`https://marketinglabai-velani-pilot-first-bootstrap.invalid` only when
read-only preflight proves the service is absent and the bootstrap mode is
`FIRST_PRIVATE_REVISION`.

Existing-service revision preparation must use the real Cloud Run URL and reject
the bootstrap origin. Prepared evidence records whether origin reconciliation is
required.

## Consequences

- First-service preparation no longer requires guessing a Cloud Run URL.
- The bootstrap origin cannot pass startup or smoke verification.
- The real Cloud Run URL must be observed and reconciled after revision
  creation and before startup or smoke gates pass.
