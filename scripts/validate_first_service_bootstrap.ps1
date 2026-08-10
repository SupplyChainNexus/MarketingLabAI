$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$ProjectRoot = (Resolve-Path (Join-Path $PSScriptRoot ".."))
$Python = (Get-Command python -ErrorAction Stop).Source

Write-Host ""
Write-Host "## MarketingLabAI Durable First-Service Bootstrap Gate"
Write-Host "Cloud mutation: false"
Write-Host "Deployment execution: false"

& $Python -m unittest `
    tests.test_private_synthetic_bootstrap `
    tests.test_release_controller
if ($LASTEXITCODE -ne 0) {
    throw "First-service bootstrap regression failed."
}

$Catalog = Get-Content `
    -LiteralPath (Join-Path $ProjectRoot "deployment\private_synthetic_release_gates.json") `
    -Raw
$Required = @(
    "FIRST_PRIVATE_REVISION",
    "ZERO_TRAFFIC_REVISION",
    "without public or pilot invocation authority",
    "zero platform traffic"
)
foreach ($Phrase in $Required) {
    if ($Catalog -notmatch [regex]::Escape($Phrase)) {
        throw "Bootstrap catalogue contract is incomplete: $Phrase"
    }
}

$Authorities = @(
    "governance\adrs\ADR-0037-first-service-private-bootstrap.md",
    "governance\locked-decision-register.md",
    "governance\quality-gates.md",
    "governance\definition-of-done.md"
)
foreach ($RelativePath in $Authorities) {
    $Content = Get-Content -LiteralPath (Join-Path $ProjectRoot $RelativePath) -Raw
    if ($Content -notmatch "FIRST_PRIVATE_REVISION") {
        throw "Binding bootstrap authority is incomplete: $RelativePath"
    }
}

Write-Host ""
Write-Host "DURABLE FIRST-SERVICE BOOTSTRAP GATE PASSED"
Write-Host "CURRENT HISTORICAL RUN MIGRATED: false"
Write-Host "CLOUD MUTATION PERFORMED: false"
Write-Host "DEPLOYMENT EXECUTED: false"
