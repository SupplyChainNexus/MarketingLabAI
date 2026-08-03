param(
    [string[]]$TestModules = @(),

    [switch]$FullSuite,

    [switch]$SkipFormat
)

$ErrorActionPreference = "Stop"

if (-not $SkipFormat) {
    Write-Host "`n--- Formatting ---"
    .\scripts\format.ps1
}

if ($TestModules.Count -gt 0) {
    Write-Host "`n--- Focused tests ---"

    foreach ($Module in $TestModules) {
        Write-Host "`nRunning: $Module"
        python -m unittest $Module -v

        if ($LASTEXITCODE -ne 0) {
            throw "Test module failed: $Module"
        }
    }
}

if ($FullSuite) {
    Write-Host "`n--- Full test suite ---"
    python -m unittest discover -s tests -p "test_*.py" -v

    if ($LASTEXITCODE -ne 0) {
        throw "Full test suite failed."
    }
}

Write-Host "`n--- Diff check ---"
git diff --check

if ($LASTEXITCODE -ne 0) {
    throw "git diff --check failed."
}

Write-Host "`n--- Git status ---"
git status --short

Write-Host "`nVALIDATION COMPLETE"
