$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$ProjectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$Template = Join-Path `
    $ProjectRoot `
    "deployment\cloud-run.private-synthetic.yaml.template"

Write-Host ""
Write-Host "MarketingLabAI Durable Private Deployment Gate"
Write-Host "------------------------------------------------"
Write-Host "Cloud mutation: false"
Write-Host "Deployment execution: false"

Push-Location $ProjectRoot

try {
    Write-Host ""
    Write-Host "[1/3] Validating the canonical Cloud Run template..."

    python -m deployment.private_synthetic_manifest `
        validate-template `
        --template $Template

    if ($LASTEXITCODE -ne 0) {
        throw "Canonical Cloud Run template validation failed."
    }

    Write-Host ""
    Write-Host "[2/3] Verifying the binding durable-remediation directive..."

    $DirectiveSources = @(
        "AGENTS.md",
        "governance\product-constitution.md",
        "governance\locked-decision-register.md",
        "governance\definition-of-done.md",
        "governance\adrs\ADR-0033-durable-remediation-directive.md"
    )

    foreach ($RelativePath in $DirectiveSources) {
        $Path = Join-Path $ProjectRoot $RelativePath

        if (-not (Test-Path -LiteralPath $Path -PathType Leaf)) {
            throw "Missing durable-remediation authority: $RelativePath"
        }

        $Text = Get-Content -LiteralPath $Path -Raw

        if ($Text -notmatch "Durable Remediation") {
            throw "Durable-remediation authority is incomplete: $RelativePath"
        }
    }

    Write-Host ""
    Write-Host "[3/3] Verifying CI execution of this gate..."

    $WorkflowPath = Join-Path $ProjectRoot ".github\workflows\quality.yml"
    $Workflow = Get-Content -LiteralPath $WorkflowPath -Raw

    if ($Workflow -notmatch "validate_private_synthetic_deployment\.ps1") {
        throw "The durable private deployment gate is not executed by CI."
    }
}
finally {
    Pop-Location
}

Write-Host ""
Write-Host "DURABLE PRIVATE DEPLOYMENT GATE PASSED"
Write-Host "CLOUD MUTATION PERFORMED: false"
Write-Host "DEPLOYMENT EXECUTED: false"
