$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$ProjectRoot = Split-Path -Parent $PSScriptRoot
$PythonCommand = Get-Command python -ErrorAction Stop
$Python = $PythonCommand.Source

Write-Host ""
Write-Host "## MarketingLabAI Canonical Private Ingress Contract"
Write-Host ""
Write-Host "Historical release-run modification: false"
Write-Host "Cloud mutation: false"
Write-Host "Deployment execution: false"
Write-Host "Python: $Python"

if (-not (Test-Path -LiteralPath $Python -PathType Leaf)) {
    throw "Resolved Python interpreter does not exist: $Python"
}

Set-Location $ProjectRoot
& $Python -m unittest tests.test_private_ingress_contract
if ($LASTEXITCODE -ne 0) { throw "Private ingress contract regression failed." }

$TemplatePath = "deployment\cloud-run.private-synthetic.yaml.template"
$Template = [System.IO.File]::ReadAllText((Resolve-Path -LiteralPath $TemplatePath))
$Expected = "run.googleapis.com/ingress: internal-and-cloud-load-balancing"
$Matches = [regex]::Matches($Template, [regex]::Escape($Expected)).Count
if ($Matches -ne 1) { throw "Canonical private ingress must occur exactly once." }
if ($Template -match "run.googleapis.com/ingress:\s+(all|internal)\s") {
    throw "A prohibited ingress value remains in the canonical template."
}

$Workflow = [System.IO.File]::ReadAllText(
    (Resolve-Path -LiteralPath ".github\workflows\quality.yml")
)
$Enforcement = '& ".\scripts\validate_private_ingress_contract.ps1"'
if ([regex]::Matches($Workflow, [regex]::Escape($Enforcement)).Count -ne 1) {
    throw "CI does not enforce the private ingress contract exactly once."
}

Write-Host ""
Write-Host "CANONICAL PRIVATE INGRESS CONTRACT PASSED"
Write-Host "INGRESS: internal-and-cloud-load-balancing"
Write-Host "HISTORICAL RUN MIGRATED OR REPAIRED: false"
Write-Host "CLOUD MUTATION PERFORMED: false"
Write-Host "DEPLOYMENT EXECUTED: false"
