[CmdletBinding()]
param(
    [string]$OutputRoot = ""
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$Repository = Split-Path -Parent $PSScriptRoot
$Python = Join-Path $Repository ".venv\Scripts\python.exe"
if (-not $OutputRoot) {
    $Stamp = Get-Date -Format "yyyyMMdd_HHmmss"
    $OutputRoot = "C:\Ai Projects\ToolkitTemp\MarketingLabAI\release-executor-identity-inspection-$Stamp"
}

if (-not (Test-Path -LiteralPath $Python -PathType Leaf)) {
    throw "Repository Python executable is missing: $Python"
}
if (-not $OutputRoot.StartsWith(
    "C:\Ai Projects\ToolkitTemp\",
    [System.StringComparison]::OrdinalIgnoreCase
)) {
    throw "OutputRoot must remain under C:\Ai Projects\ToolkitTemp."
}

Write-Host "=== MLAI-031.16 RELEASE EXECUTOR IDENTITY INSPECTION BOUNDARY ==="
Write-Host "Operator account metadata inspection: true"
Write-Host "Project metadata inspection: true"
Write-Host "IAM/service-account inspection: true"
Write-Host "Cloud CLI execution: true"
Write-Host "Credential refresh: false"
Write-Host "IAM mutation: false"
Write-Host "Service-account creation: false"
Write-Host "Service-account key creation: false"
Write-Host "Cloud Run mutation: false"
Write-Host "Deployment: false"
Write-Host "Release-state modification: false"
Write-Host "Automatic retry: false"

Push-Location $Repository
try {
    & $Python -m tools.release_control inspect-executor-identity `
        --output-root $OutputRoot
    if ($LASTEXITCODE -ne 0) {
        throw "Read-only release executor identity inspection failed."
    }
}
finally {
    Pop-Location
}

Write-Host "MLAI_031_16_RELEASE_EXECUTOR_IDENTITY_INSPECTION_COMPLETED"
Write-Host "Evidence root: $OutputRoot"
Write-Host "IAM mutation performed: false"
Write-Host "Service account created: false"
Write-Host "STOP: paste the full output before bootstrap plan preparation."
