$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest
Set-Location (Resolve-Path (Join-Path $PSScriptRoot ".."))
python -m app.operations.cli backup
if ($LASTEXITCODE -ne 0) { throw "Pilot backup failed." }
