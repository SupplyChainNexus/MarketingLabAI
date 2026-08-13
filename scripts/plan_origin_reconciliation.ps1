param(
    [Parameter(Mandatory=$true)][string]$StartupOriginInspection,
    [Parameter(Mandatory=$true)][string]$RevisionCreatedEvidence,
    [string]$OutputRoot = ""
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$RepoRoot = "C:\Ai Projects\MarketingLabAI"
$ToolkitRoot = "C:\Ai Projects\ToolkitTemp"
$StateRoot = "C:\Ai Projects\ToolkitTemp\MarketingLabAI\release-control"
$Stamp = Get-Date -Format "yyyyMMdd_HHmmss"
if (-not $OutputRoot) {
    $OutputRoot = Join-Path $ToolkitRoot "MarketingLabAI\origin-reconciliation-prep-$Stamp"
}

Write-Host "=== ORIGIN RECONCILIATION PLAN BOUNDARY ==="
Write-Host "Plan preparation: true"
Write-Host "Cloud CLI execution: false"
Write-Host "Cloud mutation: false"
Write-Host "Release-state modification: false"
Write-Host "Deployment: false"
Write-Host "Secret-value access: false"

if (-not (Test-Path -LiteralPath $StartupOriginInspection -PathType Leaf)) {
    throw "Startup origin inspection evidence not found: $StartupOriginInspection"
}
if (-not (Test-Path -LiteralPath $RevisionCreatedEvidence -PathType Leaf)) {
    throw "Revision-created evidence not found: $RevisionCreatedEvidence"
}

$SecureBrowserApiKey = Read-Host "Enter restricted browser API key" -AsSecureString
$SecureOauthClientId = Read-Host "Enter Google OAuth web client ID" -AsSecureString

$BrowserApiKeyBstr = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($SecureBrowserApiKey)
$OauthClientIdBstr = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($SecureOauthClientId)
try {
    $BrowserApiKey = [Runtime.InteropServices.Marshal]::PtrToStringAuto($BrowserApiKeyBstr)
    $OauthClientId = [Runtime.InteropServices.Marshal]::PtrToStringAuto($OauthClientIdBstr)

    Push-Location $RepoRoot
    try {
        $Python = ".\.venv\Scripts\python.exe"
        $Script = @'
import json
import os
from pathlib import Path

from tools.release_control.config import load_config
from tools.release_control.origin_reconciliation import (
    OriginReconciliationInputs,
    prepare_origin_reconciliation,
    write_origin_reconciliation_plan,
)
from tools.release_control.store import sha256_file

config = load_config()
index_path = Path(os.environ["MLAI_STATE_ROOT"]) / "release-index.json"
index = json.loads(index_path.read_text(encoding="utf-8-sig"))
release = index["release"]
startup = json.loads(Path(os.environ["MLAI_STARTUP_ORIGIN_INSPECTION"]).read_text(encoding="utf-8-sig"))
revision = json.loads(Path(os.environ["MLAI_REVISION_CREATED_EVIDENCE"]).read_text(encoding="utf-8-sig"))
output_root = Path(os.environ["MLAI_OUTPUT_ROOT"])

plan = prepare_origin_reconciliation(
    configuration=config.payload["revision_creation"],
    release=release,
    revision_created_evidence=revision,
    startup_origin_inspection=startup,
    repository_root=config.repository_root,
    output_root=output_root,
    inputs=OriginReconciliationInputs(
        restricted_browser_api_key=os.environ["MLAI_BROWSER_API_KEY"],
        google_oauth_client_id=os.environ["MLAI_GOOGLE_OAUTH_CLIENT_ID"],
    ),
)
plan["startup_origin_inspection_sha256"] = sha256_file(Path(os.environ["MLAI_STARTUP_ORIGIN_INSPECTION"]))
plan["revision_created_evidence_sha256"] = sha256_file(Path(os.environ["MLAI_REVISION_CREATED_EVIDENCE"]))
plan_path = Path(os.environ["MLAI_STATE_ROOT"]) / "origin-reconciliation-plans" / (plan["manifest_sha256"] + ".json")
plan["origin_reconciliation_plan_path"] = str(plan_path.resolve())
plan_sha = write_origin_reconciliation_plan(plan_path, plan)
plan["origin_reconciliation_plan_sha256"] = plan_sha
print(json.dumps(plan, indent=2, sort_keys=True))
'@
        $Env:MLAI_STATE_ROOT = $StateRoot
        $Env:MLAI_STARTUP_ORIGIN_INSPECTION = $StartupOriginInspection
        $Env:MLAI_REVISION_CREATED_EVIDENCE = $RevisionCreatedEvidence
        $Env:MLAI_OUTPUT_ROOT = $OutputRoot
        $Env:MLAI_BROWSER_API_KEY = $BrowserApiKey
        $Env:MLAI_GOOGLE_OAUTH_CLIENT_ID = $OauthClientId
        & $Python -c $Script
        if ($LASTEXITCODE -ne 0) { throw "Origin reconciliation plan preparation failed." }
    }
    finally {
        Pop-Location
        Remove-Item Env:\MLAI_BROWSER_API_KEY -ErrorAction SilentlyContinue
        Remove-Item Env:\MLAI_GOOGLE_OAUTH_CLIENT_ID -ErrorAction SilentlyContinue
    }
}
finally {
    if ($BrowserApiKeyBstr -ne [IntPtr]::Zero) { [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($BrowserApiKeyBstr) }
    if ($OauthClientIdBstr -ne [IntPtr]::Zero) { [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($OauthClientIdBstr) }
}

Write-Host "MLAI_031_13_ORIGIN_RECONCILIATION_PLAN_PREPARED"
Write-Host "Output root: $OutputRoot"
Write-Host "Cloud CLI executed: false"
Write-Host "Cloud mutation performed: false"
Write-Host "Release state modified: false"
Write-Host "STOP: paste this output for exact plan-bound approval."
