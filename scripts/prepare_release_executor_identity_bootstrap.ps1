[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [string]$Inspection,
    [string]$OutputRoot = ""
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$Repository = Split-Path -Parent $PSScriptRoot
$Python = Join-Path $Repository ".venv\Scripts\python.exe"
if (-not $OutputRoot) {
    $Stamp = Get-Date -Format "yyyyMMdd_HHmmss"
    $OutputRoot = "C:\Ai Projects\ToolkitTemp\MarketingLabAI\release-executor-identity-plan-$Stamp"
}

if (-not (Test-Path -LiteralPath $Python -PathType Leaf)) {
    throw "Repository Python executable is missing: $Python"
}
if (-not (Test-Path -LiteralPath $Inspection -PathType Leaf)) {
    throw "Inspection evidence is missing: $Inspection"
}
if (-not $OutputRoot.StartsWith(
    "C:\Ai Projects\ToolkitTemp\",
    [System.StringComparison]::OrdinalIgnoreCase
)) {
    throw "OutputRoot must remain under C:\Ai Projects\ToolkitTemp."
}

Write-Host "=== MLAI-031.16 RELEASE EXECUTOR IDENTITY PLAN BOUNDARY ==="
Write-Host "Inspection evidence verification: true"
Write-Host "Deterministic IAM plan preparation: true"
Write-Host "Cloud CLI execution: false"
Write-Host "Credential refresh: false"
Write-Host "IAM inspection: false"
Write-Host "IAM mutation: false"
Write-Host "Service-account creation: false"
Write-Host "Service-account key creation: false"
Write-Host "Cloud Run mutation: false"
Write-Host "Deployment: false"
Write-Host "Release-state modification: false"

Push-Location $Repository
try {
    & $Python -m tools.release_control prepare-executor-identity-bootstrap `
        --inspection $Inspection `
        --output-root $OutputRoot
    if ($LASTEXITCODE -ne 0) {
        throw "Release executor identity bootstrap plan preparation failed."
    }
}
finally {
    Pop-Location
}

Write-Host "MLAI_031_16_RELEASE_EXECUTOR_IDENTITY_PLAN_PREPARED"
Write-Host "Output root: $OutputRoot"
Write-Host "Cloud CLI executed: false"
Write-Host "IAM mutation performed: false"
Write-Host "STOP: paste the full output for exact plan-bound authorization."
