# ADR-0040: Permanent Read-Only Cloud Preflight Executor

Status: Accepted
Date: 2026-08-12

## Context

The unified release control plane stopped safely after configuration validation,
but `CLOUD_PREFLIGHT_PASSED` still required operator-authored commands. That gap
would reintroduce temporary scripts, shell parsing failures, manual evidence
transfer and multiple operational truths at the first cloud-aware gate.

## Decision

`tools.release_control` owns one permanent cloud-preflight executor. It invokes
`gcloud` through Python argument arrays with `shell=False`, permits only exact
read-only command prefixes, requires JSON output and records hashes of the raw
observations. Resource identities are pinned in
`tools/release_control_plane.json` and validated before execution.

The executor verifies the active project, required APIs, runtime and builder
identities, immutable Docker repository, exact image digest, Cloud SQL contract,
Secret Manager metadata and enabled-version counts, least-privilege access, and
the canonical Cloud Run target state. It never reads secret values. A public or
ambiguous target fails closed.

The existing one-plan, one-approval, idempotent-apply interface remains the only
operator path. The preflight may append only the observational
`CLOUD_PREFLIGHT_PASSED` result. It cannot deploy, create a revision, modify IAM,
route traffic, rebuild an image or grant admission authority.

## Consequences

- Cloud-aware validation is reproducible and machine-verifiable.
- PowerShell remains a thin launcher and does not implement cloud orchestration.
- Repeated apply or resume returns the same completed operation.
- Any failed observation remains a failed gate; repair changes the canonical
  source and requires a fresh plan.
- REVISION_CREATED remains unsupported and separately authorized.
- ADR-0035 still blocks deployment of historical or observational artifacts
  until the independent cryptographic admission path is complete.
