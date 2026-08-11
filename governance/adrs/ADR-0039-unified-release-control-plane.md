# ADR-0039 — Unified Release Control Plane

## Status

Accepted by the founder on 2026-08-12 as durable remediation of the
private-synthetic release operator path.

## Context

The `2239244` release exposed structural operational defects before and after a
successful Cloud Build: PowerShell 5.1 native-command behaviour, duplicated
temporary scripts, stale story-numbered paths, unpinned Python discovery,
manual authorization transfer, fragmented evidence directories and direct use
of an observational controller. The application image built successfully when
the request reached Cloud Build; most elapsed troubleshooting time belonged to
the release harness.

ADR-0034 requires strong controls with automated sequencing and a simple
operator experience. ADR-0035 separately requires cryptographic release
authority and infrastructure admission. Treating those responsibilities as one
component would weaken both.

## Decision

MarketingLabAI has one supported release operator entry point:
`scripts/mlai_release.ps1`, a thin PowerShell 5.1 launcher for the pinned Python
module `tools.release_control`.

The Python control plane implements a one-plan, one-approval and one-status
operator contract. It owns deterministic planning, a plan-bound local
approval, idempotent application, safe resume, atomic external records and one
integrity-checked evidence index. It reuses the canonical gate catalogue and
the existing append-only observational ledger; it does not create a parallel
gate state machine.

Responsibilities remain separated:

- `tools.release_control` is the orchestration authority.
- `deployment.release_controller` is observational history only.
- signed attestations, final release authority and Binary Authorization form
  the independent admission authority.

Local approval authorizes only the exact orchestration plan. It is never a
release signature, deployment authority or Binary Authorization attestation.
Cloud-mutating transitions remain unavailable until their hardened executors,
cryptographic evidence and separately authorized infrastructure admission are
implemented.

The external state root is stable and product-named, never story-numbered.
Records use same-directory atomic replacement, SHA-256 sidecars and an
automatically released process lock. Repeat application returns the completed
operation or resumes the same plan; it never creates a duplicate build, release
run or gate result.

Dependency-lock verification hashes UTF-8 text after BOM removal and LF
normalization. This preserves exact dependency semantics while preventing a
clean Windows checkout from failing solely because Git or PowerShell materialized
CRLF line endings. Installer recovery similarly recognizes only a clean baseline
or the exact managed file scope of an interrupted prior attempt.

## Preserved release

The `2239244` image and `run-20260811T220803Z-0ac5eb23` may be adopted as
verified observations so configuration validation can continue without another
build. Adoption does not make that image deployable. ADR-0035 still requires
the first Binary-Authorization-enforced artifact to be rebuilt through the
hardened provenance path.

## Consequences

- Normal operation becomes one status, one deterministic plan and one approval.
- PowerShell does not interpret JSON, control state transitions or execute cloud
  orchestration.
- Direct use of `scripts/release_private_synthetic.ps1` is retired.
- Interrupted local work can resume without rewriting evidence.
- Existing evidence remains immutable and externally referenced by digest.
- No repository action under this ADR performs cloud mutation, deployment,
  traffic routing, secret retrieval, public access or real-data activation.
