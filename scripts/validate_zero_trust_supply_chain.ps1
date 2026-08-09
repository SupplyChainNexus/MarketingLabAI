$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$ProjectRoot = Split-Path -Parent $PSScriptRoot
$Python = (Get-Command "python" -ErrorAction Stop).Source

Set-Location $ProjectRoot

Write-Host ""
Write-Host "## MarketingLabAI Zero-Trust Supply-Chain Foundation"
Write-Host "Cryptographic signing performed: false"
Write-Host "Release authorization issued: false"
Write-Host "Cloud mutation: false"
Write-Host "Deployment execution: false"

& $Python -m py_compile `
    ".\deployment\zero_trust_supply_chain.py" `
    ".\tests\test_zero_trust_supply_chain.py"
if ($LASTEXITCODE -ne 0) { throw "Zero-trust compilation failed." }

& $Python -m unittest `
    tests.test_zero_trust_supply_chain `
    tests.test_quality_governance
if ($LASTEXITCODE -ne 0) { throw "Zero-trust regression failed." }

$Workflow = Get-Content ".\.github\workflows\quality.yml" -Raw
if ($Workflow -notmatch "validate_zero_trust_supply_chain\.ps1") {
    throw "CI does not execute the zero-trust gate."
}

Write-Host ""
Write-Host "ZERO-TRUST SUPPLY-CHAIN FOUNDATION PASSED"
Write-Host "MODE: shadow"
Write-Host "DEPLOYMENT AUTHORIZED: false"
Write-Host "CLOUD MUTATION PERFORMED: false"
