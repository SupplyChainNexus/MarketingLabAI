$ErrorActionPreference = "Stop"

Write-Host ""
Write-Host "MarketingLabAI Quality Check"
Write-Host "----------------------------"

if (-not $env:VIRTUAL_ENV) {
    throw "Activate the virtual environment before running quality checks."
}

Write-Host ""
Write-Host "[1/5] Checking formatting..."
python -m black --check app tests

if ($LASTEXITCODE -ne 0) {
    throw "Black formatting check failed."
}

Write-Host ""
Write-Host "[2/5] Running Ruff..."
python -m ruff check app tests

if ($LASTEXITCODE -ne 0) {
    throw "Ruff linting failed."
}

Write-Host ""
Write-Host "[3/5] Running automated tests..."
python -m unittest discover -s tests -v

if ($LASTEXITCODE -ne 0) {
    throw "Automated tests failed."
}

Write-Host ""
Write-Host "[4/5] Running local health check..."
python -m app.main health

if ($LASTEXITCODE -ne 0) {
    throw "Health check failed."
}

Write-Host ""
Write-Host "[5/5] Checking Git for accidental secrets..."
$trackedEnvironmentFiles = git ls-files |
    Where-Object {
        $_ -eq ".env" -or
        $_ -like ".env.*" -and
        $_ -ne ".env.example"
    }

if ($trackedEnvironmentFiles) {
    Write-Host $trackedEnvironmentFiles
    throw "A private environment file is tracked by Git."
}

Write-Host ""
Write-Host "All MarketingLabAI quality checks passed."
