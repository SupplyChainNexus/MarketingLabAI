# Unified Private Synthetic Release Control

MarketingLabAI uses **Strong controls + automated sequencing + simple operator
experience** through one supported entry point:

```powershell
& ".\scripts\mlai_release.ps1" status
```

The launcher resolves the active repository virtual environment and forwards
arguments unchanged to `python -m tools.release_control`. It does not
parse JSON, select gates, maintain evidence or execute cloud commands.
Dependency-lock hashes use the documented `utf8-sig-lf-v1` canonical text mode,
so LF and CRLF materializations verify identically without relaxing exact pins.

## Authority separation

| Responsibility | Component |
| --- | --- |
| Planning, approval binding, idempotency and recovery | `tools.release_control` |
| Append-only gate history | `deployment.release_controller` |
| Cryptographic release and deployment admission | External final signer and Binary Authorization |

Controller state and local approval are never deployment authority.

## Normal operator journey

```powershell
& ".\scripts\mlai_release.ps1" status
& ".\scripts\mlai_release.ps1" plan
& ".\scripts\mlai_release.ps1" approve `
    --plan "<plan-digest>" `
    --operator "<operator>" `
    --authorization-reference "<approval-reference>"
& ".\scripts\mlai_release.ps1" apply --plan "<plan-digest>"
& ".\scripts\mlai_release.ps1" status
```

`resume` re-enters the same approved plan. It cannot silently create a second
build, release run or terminal gate result. `status --audit` exposes hashes and
evidence paths through progressive disclosure.

## External state

The default Windows state root is:

```text
C:\Ai Projects\ToolkitTemp\MarketingLabAI\release-control
```

It contains one release index, deterministic plans, plan-bound approvals,
operation journals and evidence. Every JSON record has a SHA-256 sidecar and is
written atomically. A process lock is released automatically if execution is
interrupted.

The root can be overridden with `MLAI_RELEASE_STATE_ROOT` or `--state-root`.
It may never be inside the repository or coupled to an MLAI story number.

## One-time adoption

An existing observational run is adopted only after its chain, build summary,
post-build assessment, commit and image digest verify. Adoption indexes
evidence; it does not rewrite it or make the image deployable.

```powershell
& ".\scripts\mlai_release.ps1" adopt `
    --run "<observational-run-directory>" `
    --build-summary "<controlled-build-summary.json>" `
    --post-build-assessment "<post-build-evidence-assessment.json>" `
    --operator "<operator>"
```

Direct use of `scripts/release_private_synthetic.ps1` is retired.

## Read-only cloud preflight

After `CONFIGURATION_VALIDATED`, `plan` produces the deterministic
`CLOUD_PREFLIGHT_PASSED` transition. Approval and application use the same
normal journey. Apply inspects only pinned cloud resources through exact
read-only `gcloud` verbs and stores minimized, hash-indexed evidence.

The executor verifies project and API state, service accounts, immutable
artifact identity, Cloud SQL, Secret Manager metadata/access and the canonical
Cloud Run service boundary. It never accesses secret payloads. It cannot create
a revision, deploy, modify IAM, route traffic, rebuild or issue admission
authority. `REVISION_CREATED` remains unsupported and requires later explicit
architecture and authorization work under ADR-0035.
