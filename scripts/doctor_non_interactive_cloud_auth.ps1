$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$RepoRoot = "C:\Ai Projects\MarketingLabAI"
$Python = Join-Path $RepoRoot ".venv\Scripts\python.exe"

Write-Host "=== MLAI-031.15 NON-INTERACTIVE AUTH DOCTOR BOUNDARY ==="
Write-Host "Cloud CLI execution: true"
Write-Host "Cloud resource inspection: false"
Write-Host "Cloud mutation: false"
Write-Host "Release-state modification: false"
Write-Host "Deployment: false"
Write-Host "Service-account key files: forbidden"

Push-Location $RepoRoot
try {
    & $Python -m tools.release_control doctor-auth
    if ($LASTEXITCODE -ne 0) {
        throw "Non-interactive cloud auth doctor failed."
    }
}
finally {
    Pop-Location
}

Write-Host "MLAI_031_15_NON_INTERACTIVE_AUTH_DOCTOR_COMPLETED"
Write-Host "Cloud mutation performed: false"
Write-Host "Release state modified: false"
Write-Host "STOP: paste this output before any release mutation retry."
