# ADR-0041: Provenance-Bound Windows Cloud CLI Adapter

Status: Accepted
Date: 2026-08-12

## Context

MLAI-031.9 passed 970 repository tests but the first live read-only preflight
failed twice at `projects describe`. Direct PowerShell inspection proved that
the pinned account, configuration and project were active. The untested boundary
was Python launching the Windows `gcloud.cmd` batch entry point from a path with
spaces. The earlier tests replaced the Cloud SDK reader and therefore could not
validate this platform contract.

The interrupted plan and approval predate this repair. Reusing them would allow
changed executor code to act under approval for a different executable contract.

## Decision

The release control plane owns a dedicated Cloud CLI adapter. On Windows, a
`.cmd` or `.bat` entry point crosses one deliberate `cmd.exe` boundary using
Python's Windows command-line quoting. Native binaries remain direct
`shell=False` invocations. Only program-owned, allowlisted argument tokens are
accepted; shell metacharacters and caller-supplied account, configuration,
project, quiet or format flags are rejected.

Every invocation pins the exact account, configuration and project. A
`doctor-cloud` command verifies that same context through the same adapter using
local Cloud SDK metadata. Apply runs the doctor before creating an operation
journal, then reuses that adapter for the authorized read-only observations.

Every new plan binds the control-plane version, clean repository commit,
executor-contract SHA-256 and platform adapter. Changed or missing provenance
fails closed. An interrupted operation may be closed only by the explicit,
integrity-checked `supersede-operation` transition. Supersession preserves the
plan, approval and journal, appends no release gate and performs no cloud action.
A new plan and new approval are then required.

## Consequences

- Windows batch behavior is an explicit tested product contract.
- Authentication drift is detected before a running journal is created.
- Full sanitized Cloud SDK diagnostics are preserved on failure.
- Old approvals never authorize changed executor code.
- `resume` reports supersession when safe automatic continuation is impossible.
- Installation, validation and supersession perform no cloud mutation.
- Cloud preflight remains read-only and grants no deployment or admission
  authority.
