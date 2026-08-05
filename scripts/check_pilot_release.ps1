$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest
Set-Location (Resolve-Path (Join-Path $PSScriptRoot ".."))
python -m app.operations.cli release-gate
if ($LASTEXITCODE -ne 0) { throw "Synthetic pilot release gate failed." }
