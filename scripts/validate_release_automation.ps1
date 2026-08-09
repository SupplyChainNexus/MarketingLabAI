$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$ProjectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$ProjectVenvPython = "$ProjectRoot.venv\Scripts\python.exe"
$Python = if (Test-Path -LiteralPath $ProjectVenvPython -PathType Leaf) {
    $ProjectVenvPython
}
else {
    (Get-Command "python" -ErrorAction Stop).Source
}

Push-Location $ProjectRoot

try {
    Write-Host ""
    Write-Host "MarketingLabAI Unified Release Automation Gate"
    Write-Host "------------------------------------------------"
    Write-Host "Cloud mutation: false"
    Write-Host "Deployment execution: false"

    Write-Host ""
    Write-Host "[1/4] Validating the dependency-aware gate catalogue..."
    & $Python -m deployment.release_controller validate-catalog
    if ($LASTEXITCODE -ne 0) { throw "Release-gate catalogue validation failed." }

    Write-Host ""
    Write-Host "[2/4] Running focused release-controller regression..."
    & $Python -m unittest tests.test_release_controller
    if ($LASTEXITCODE -ne 0) { throw "Release-controller regression failed." }

    Write-Host ""
    Write-Host "[3/4] Verifying binding governance..."
    $Authorities = @(
        "governance\adrs\ADR-0034-progressive-release-automation.md",
        "governance\locked-decision-register.md",
        "governance\quality-gates.md",
        "governance\definition-of-done.md"
    )
    foreach ($RelativePath in $Authorities) {
        $Path = Join-Path $ProjectRoot $RelativePath
        if (-not (Test-Path -LiteralPath $Path -PathType Leaf)) {
            throw "Missing release-automation authority: $RelativePath"
        }
        if ((Get-Content -LiteralPath $Path -Raw) -notmatch
            "Strong controls \+ automated sequencing \+ simple operator experience") {
            throw "Release-automation directive is incomplete: $RelativePath"
        }
    }

    Write-Host ""
    Write-Host "[4/4] Verifying CI enforcement..."
    $Workflow = Get-Content `
        -LiteralPath (Join-Path $ProjectRoot ".github\workflows\quality.yml") `
        -Raw
    if ($Workflow -notmatch "validate_release_automation\.ps1") {
        throw "Unified release automation is not enforced by CI."
    }
}
finally {
    Pop-Location
}

Write-Host ""
Write-Host "UNIFIED RELEASE AUTOMATION GATE PASSED"
Write-Host "CLOUD MUTATION PERFORMED: false"
Write-Host "DEPLOYMENT EXECUTED: false"
