param(
    [switch]$Apply
)

$ErrorActionPreference = "Stop"

$Candidates = @(
    ".\INSTALL.md",
    ".\README.md",
    ".\customer_intelligence_increment_2.zip",
    ".\MLAI-022_customer_context_builder.zip",
    ".\MLAI-022_customer_context_builder",
    ".\MLAI-023.1_customer_context_provider.zip",
    ".\MLAI-023.1_circular_import_patch.zip",
    ".\MLAI-023.2_ai_context_integration.zip",
    ".\docs\CUSTOMER_INTELLIGENCE_BUILD_CONTEXT.txt",
    ".\scripts\create_customer_intelligence_foundation.ps1"
)

$Existing = @(
    $Candidates |
    Where-Object { Test-Path $_ }
)

if ($Existing.Count -eq 0) {
    Write-Host "No known temporary build artifacts were found."
    exit 0
}

Write-Host "Temporary build artifacts:"
$Existing | ForEach-Object { Write-Host " - $_" }

if (-not $Apply) {
    Write-Host ""
    Write-Host "Preview only. Nothing was deleted."
    Write-Host "Run with -Apply to remove these files."
    exit 0
}

foreach ($Path in $Existing) {
    Remove-Item `
        -Path $Path `
        -Force `
        -Recurse
    Write-Host "REMOVED: $Path"
}

Write-Host "`nWorkspace cleanup complete."
git status --short
