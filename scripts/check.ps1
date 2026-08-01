param(
    [switch]$VerboseTests
)

$ErrorActionPreference = "Stop"

Write-Host ""
Write-Host "Running MarketingLabAI checks..."
Write-Host ""

Write-Host "[1/4] Checking formatting..."
black --check app tests

Write-Host ""
Write-Host "[2/4] Running Ruff..."
ruff check app tests

Write-Host ""
Write-Host "[3/4] Compiling Python files..."
python -m compileall -q app tests

Write-Host ""
Write-Host "[4/4] Running tests..."

if ($VerboseTests) {
    python -m unittest discover -s tests -v
}
else {
    python -m unittest discover -s tests
}

Write-Host ""
Write-Host "All checks passed."
