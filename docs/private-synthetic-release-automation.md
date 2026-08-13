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
authority.

## Private revision preparation

After `CLOUD_PREFLIGHT_PASSED`, `prepare-revision` renders the exact private
Cloud Run manifest outside the repository and records the intended
`gcloud run services replace` command without executing it:

```powershell
& ".\scripts\mlai_release.ps1" prepare-revision `
    --output-root "C:\Ai Projects\ToolkitTemp\MarketingLabAI\revision-prep\<stamp>" `
    --origin "<private-cloud-run-origin>" `
    --browser-api-key "<restricted-browser-api-key>" `
    --oauth-client-id "<google-oauth-web-client-id>"
```

The record binds the release index, observational event head, executor
provenance, manifest hash, template hash, expected traffic outcome and command
intent. It performs no Cloud CLI execution, cloud mutation, traffic routing,
rebuild, deployment, admission-authority action or Secret Manager payload
access. Applying `REVISION_CREATED` remains a separate approval boundary.

For first-service bootstrap, the canonical service has no Cloud Run `status.url`
until the first revision creates the service. In that one case only,
preparation may render
`https://marketinglabai-velani-pilot-first-bootstrap.invalid` and mark
`requires_origin_reconciliation: true`. Existing services must use the actual
Cloud Run URL. Startup and smoke gates remain blocked until the real URL is
observed and reconciled.

## Windows Cloud SDK and safe recovery

`doctor-cloud` uses the same adapter as cloud preflight and verifies the exact
pinned account, configuration and project before an operation journal exists:

```powershell
& ".\scripts\mlai_release.ps1" doctor-cloud
```

Every plan is bound to the clean repository commit and executor contract. If
executor code changes while an operation is running, `status` and `resume`
return `supersession_required`. The old plan and approval cannot be reused.
After explicit authorization, close it without changing release or cloud state:

```powershell
& ".\scripts\mlai_release.ps1" supersede-operation `
    --plan "<old-plan-digest>" `
    --operator "<operator>" `
    --reason "<durable-repair-reason>" `
    --authorization-reference "<supersession-authorization>"
```

Then `resume` creates the new provenance-bound plan and stops for its new exact
approval. Supersession is never an admission decision and never executes cloud.

## MLAI-031.13: Durable first-service origin reconciliation

First-service bootstrap may use the approved placeholder origin only until the generated Cloud Run service URL is known. ORIGIN_RECONCILED must replace that placeholder with the observed real URL before STARTUP_VERIFIED.

No startup or smoke gate may pass while MLAI_PUBLIC_ORIGIN is https://marketinglabai-velani-pilot-first-bootstrap.invalid.

## MLAI-031.14: Release tooling hardening

Release transitions must be executed through the Python release-control CLI.
PowerShell scripts are thin launchers only and may not embed Python source.
`ORIGIN_RECONCILED` planning must use `python -m tools.release_control
prepare-origin-reconciliation`.
