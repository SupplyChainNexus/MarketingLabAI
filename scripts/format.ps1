$ErrorActionPreference = "Stop"

Write-Host ""
Write-Host "Formatting MarketingLabAI..."
Write-Host ""

black app tests
ruff check app tests --fix

Write-Host ""
Write-Host "Formatting complete."
