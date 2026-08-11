$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$Launcher = Join-Path $PSScriptRoot "mlai_release.ps1"
& $Launcher validate-repository
if ($LASTEXITCODE -ne 0) {
    throw "Unified release-control validation failed with exit code $LASTEXITCODE."
}
