param(
    [Parameter(Mandatory=$true)][string]$StartupOriginInspection,
    [Parameter(Mandatory=$true)][string]$RevisionCreatedEvidence,
    [string]$OutputRoot = ""
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$RepoRoot = "C:\Ai Projects\MarketingLabAI"
$ToolkitRoot = "C:\Ai Projects\ToolkitTemp"
if (-not $OutputRoot) {
    $OutputRoot = Join-Path $ToolkitRoot ("MarketingLabAI\origin-reconciliation-prep-" + (Get-Date -Format "yyyyMMdd_HHmmss"))
}

Write-Host "=== ORIGIN RECONCILIATION PLAN BOUNDARY ==="
Write-Host "Plan preparation: true"
Write-Host "PowerShell embedded Python: false"
Write-Host "Cloud CLI execution: false"
Write-Host "Cloud mutation: false"
Write-Host "Release-state modification: false"
Write-Host "Deployment: false"
Write-Host "Secret-value access: false"

$SecureBrowserApiKey = Read-Host "Enter restricted browser API key" -AsSecureString
$SecureOauthClientId = Read-Host "Enter Google OAuth web client ID" -AsSecureString

$BrowserApiKeyBstr = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($SecureBrowserApiKey)
$OauthClientIdBstr = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($SecureOauthClientId)

try {
    $env:MLAI_BROWSER_API_KEY = [Runtime.InteropServices.Marshal]::PtrToStringAuto($BrowserApiKeyBstr)
    $env:MLAI_GOOGLE_OAUTH_CLIENT_ID = [Runtime.InteropServices.Marshal]::PtrToStringAuto($OauthClientIdBstr)

    Push-Location $RepoRoot
    try {
        & ".\.venv\Scripts\python.exe" -m tools.release_control prepare-origin-reconciliation `
            --startup-origin-inspection $StartupOriginInspection `
            --revision-created-evidence $RevisionCreatedEvidence `
            --output-root $OutputRoot
        if ($LASTEXITCODE -ne 0) {
            throw "Origin reconciliation plan preparation failed."
        }
    }
    finally {
        Pop-Location
    }
}
finally {
    Remove-Item Env:\MLAI_BROWSER_API_KEY -ErrorAction SilentlyContinue
    Remove-Item Env:\MLAI_GOOGLE_OAUTH_CLIENT_ID -ErrorAction SilentlyContinue

    if ($BrowserApiKeyBstr -ne [IntPtr]::Zero) {
        [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($BrowserApiKeyBstr)
    }
    if ($OauthClientIdBstr -ne [IntPtr]::Zero) {
        [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($OauthClientIdBstr)
    }
}

Write-Host "MLAI_031_14_ORIGIN_RECONCILIATION_PLAN_PREPARED"
Write-Host "Output root: $OutputRoot"
Write-Host "Cloud CLI executed: false"
Write-Host "Cloud mutation performed: false"
Write-Host "Release state modified: false"
Write-Host "STOP: paste this output for exact plan-bound approval."
