## MLAI-031.14: Release tooling hardening

The release path is paused until the operator-facing tooling is repaired.

Rules:

- No Python embedded in PowerShell release scripts.
- No temporary script becomes critical release machinery.
- Every transition must expose requirements through the Python CLI.
- Every transition plan must be created through the Python CLI.
- PowerShell remains a thin launcher only.
- All evidence and outputs remain under `C:\Ai Projects\ToolkitTemp`.

This repair must pass CI before `ORIGIN_RECONCILED` planning resumes.

