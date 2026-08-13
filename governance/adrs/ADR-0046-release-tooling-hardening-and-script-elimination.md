# ADR-0046: Release Tooling Hardening and Script Elimination

Status: Accepted

## Context

MLAI-031.13 correctly introduced a durable `ORIGIN_RECONCILED` transition, but
the attempted execution path exposed a release-tooling weakness:

- Python was embedded inside PowerShell here-strings.
- PowerShell quoting altered Python source before execution.
- JSON writes risked UTF-8 BOM drift under Windows PowerShell 5.1.
- The public CLI did not own the new transition.
- Tests covered internal functions but not the operator-facing command path.

This is not a Google Cloud infrastructure failure. It is a release-control
infrastructure failure.

## Decision

Release transition execution must be owned by the Python release-control CLI.
PowerShell scripts may only:

- print the authorization boundary;
- collect operator input;
- set environment variables;
- call `python -m tools.release_control ...`;
- report the result.

PowerShell release scripts must not embed Python source.

## Consequences

`ORIGIN_RECONCILED` planning moves to:

```powershell
python -m tools.release_control requirements --gate ORIGIN_RECONCILED
python -m tools.release_control prepare-origin-reconciliation `
  --startup-origin-inspection <path> `
  --revision-created-evidence <path> `
  --output-root <ToolkitTemp path>
```

CI must reject release PowerShell scripts that embed Python here-strings or
write JSON with BOM-prone patterns.

