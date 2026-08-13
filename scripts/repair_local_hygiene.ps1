param(
    [switch]$FullTests
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$RepoRoot = "C:\Ai Projects\MarketingLabAI"
Push-Location $RepoRoot

try {
    Write-Host "=== LOCAL HYGIENE REPAIR ==="
    Write-Host "Repository modification: formatting/encoding only"
    Write-Host "Cloud operation: false"
    Write-Host "Release-state modification: false"

    $Utf8NoBom = New-Object System.Text.UTF8Encoding($false)

    $TextFiles = @(
        ".github\workflows\quality.yml",
        "backlog\MLAI-031.md",
        "deployment\private_synthetic_release_gates.json",
        "docs\handover\CURRENT_HANDOVER.md",
        "docs\private-synthetic-release-automation.md",
        "governance\definition-of-done.md",
        "governance\locked-decision-register.md",
        "governance\quality-gates.md",
        "governance\registers\risk-register.md",
        "governance\registers\technical-debt-register.md",
        "scripts\plan_origin_reconciliation.ps1",
        "tools\release_control_plane.json"
    )

    foreach ($Relative in $TextFiles) {
        if (Test-Path -LiteralPath $Relative -PathType Leaf) {
            $Text = Get-Content -LiteralPath $Relative -Raw
            $Text = $Text.TrimEnd() + "`n"
            [System.IO.File]::WriteAllText((Resolve-Path $Relative).Path, $Text, $Utf8NoBom)
        }
    }

    & ".\.venv\Scripts\python.exe" -m ruff check . --fix
    if ($LASTEXITCODE -ne 0) { throw "Ruff auto-fix failed." }

    & ".\.venv\Scripts\python.exe" -m black .
    if ($LASTEXITCODE -ne 0) { throw "Black format failed." }

    git diff --check
    if ($LASTEXITCODE -ne 0) { throw "Git whitespace check failed." }

    if (-not $env:GEMINI_API_KEY) {
        $env:GEMINI_API_KEY = "synthetic-test-key"
    }

    if ($FullTests.IsPresent) {
        & ".\.venv\Scripts\python.exe" -m unittest discover -s tests
        if ($LASTEXITCODE -ne 0) { throw "Complete Python regression failed." }
    }

    & ".\.venv\Scripts\python.exe" -m tools.release_control validate-repository
    if ($LASTEXITCODE -ne 0) { throw "Release repository validation failed." }

    Write-Host "LOCAL_HYGIENE_REPAIR_PASSED"
    Write-Host "Cloud operation performed: false"
    Write-Host "Release state modified: false"
}
finally {
    Pop-Location
}