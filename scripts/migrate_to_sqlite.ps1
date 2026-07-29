$ErrorActionPreference = "Stop"

Write-Host ""
Write-Host "MarketingLabAI - JSON to SQLite Migration"
Write-Host "========================================="
Write-Host ""

python -m app.database.migration

if ($LASTEXITCODE -ne 0) {
    throw "The SQLite migration reported one or more failed records."
}

Write-Host ""
Write-Host "SQLite migration completed successfully."
Write-Host ""
