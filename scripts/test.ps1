param(
    [switch]$VerboseTests
)

$ErrorActionPreference = "Stop"

Write-Host ""
Write-Host "Running MarketingLabAI tests..."
Write-Host ""

if ($VerboseTests) {
    python -m unittest discover -s tests -v
}
else {
    python -m unittest discover -s tests
}

Write-Host ""
Write-Host "Tests passed."
