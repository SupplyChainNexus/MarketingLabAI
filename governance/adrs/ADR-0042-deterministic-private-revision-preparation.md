# ADR-0042: Deterministic Private Revision Preparation

## Status

Accepted

## Context

The private synthetic release has passed source, CI, artifact, configuration
and read-only cloud preflight gates. The next eligible gate,
`REVISION_CREATED`, is the first cloud mutation boundary. Recent failures show
that mutation steps must be prepared as durable product machinery, not
operator-specific PowerShell.

## Decision

MarketingLabAI adds a repository-owned `prepare-revision` control-plane command.
It renders the exact private Cloud Run manifest outside the repository and
records the intended `gcloud run services replace` command, but does not execute
Cloud CLI or mutate Google Cloud.

The preparation record binds the release index, observational event head,
executor provenance, manifest hash, template hash, immutable image digest,
source commit, private service origin and expected Cloud Run bootstrap mode.
It reads no Secret Manager payloads and grants no admission authority.

## Consequences

- `REVISION_CREATED` cannot be reached from an ad hoc command.
- Review can inspect the exact manifest and command before mutation approval.
- Preparation is machine-verifiable and idempotent.
- Actual revision creation remains a later explicit mutation boundary.
