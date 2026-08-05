$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$ProjectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$RequiredFiles = @(
    "AGENTS.md",
    "governance\authority-hierarchy.md",
    "governance\product-constitution.md",
    "governance\locked-decision-register.md",
    "governance\decision-change-control.md",
    "governance\pdrs\README.md",
    "governance\pdrs\PDR-TEMPLATE.md",
    "governance\pdrs\PDR-0001-product-direction-ratification.md",
    "governance\pdrs\PDR-0002-secure-pilot-vertical-slice.md",
    "docs\launch-readiness-review.md",
    "backlog\MLAI-027.md",
    "docs\engineering\continuity.md",
    "docs\handover\CURRENT_HANDOVER.md",
    "scripts\build_handover.ps1"
)

foreach ($RelativePath in $RequiredFiles) {
    $Path = Join-Path $ProjectRoot $RelativePath
    if (-not (Test-Path $Path -PathType Leaf)) {
        throw "Missing continuity file: $RelativePath"
    }
}

$Scripts = @(
    "scripts\build_handover.ps1",
    "tests\test_handover_system.ps1"
)

foreach ($RelativePath in $Scripts) {
    $Path = Join-Path $ProjectRoot $RelativePath
    $Text = Get-Content -LiteralPath $Path -Raw
    [void][scriptblock]::Create($Text)

    $UnsupportedEncodingPattern = '(?i)-Encoding\s+utf8NoBOM'
    if ($Text -match $UnsupportedEncodingPattern) {
        throw "PowerShell 5.1-incompatible encoding name in $RelativePath"
    }
}

$TrackedGovernanceText = @(
    Get-Content -LiteralPath (Join-Path $ProjectRoot "AGENTS.md") -Raw
    Get-Content -LiteralPath (Join-Path $ProjectRoot "governance\authority-hierarchy.md") -Raw
    Get-Content -LiteralPath (Join-Path $ProjectRoot "governance\locked-decision-register.md") -Raw
)

if (($TrackedGovernanceText -join "`n") -notmatch "Marketing Intelligence Operating System") {
    throw "Canonical product identity is missing from continuity governance."
}

$RatificationText = Get-Content -LiteralPath (
    Join-Path $ProjectRoot "governance\pdrs\PDR-0001-product-direction-ratification.md"
) -Raw

if ($RatificationText -notmatch '(?m)^Accepted\r?$') {
    throw "PDR-0001 is not recorded as accepted."
}

if ($RatificationText -notmatch "Launch Readiness and Vertical-Slice Review") {
    throw "PDR-0001 does not preserve the required next-epic review."
}

$PilotDecisionText = Get-Content -LiteralPath (
    Join-Path $ProjectRoot "governance\pdrs\PDR-0002-secure-pilot-vertical-slice.md"
) -Raw

if ($PilotDecisionText -notmatch '(?m)^Accepted\r?$') {
    throw "PDR-0002 is not recorded as accepted."
}

if (
    ($PilotDecisionText -notmatch "MLAI-027") -or
    ($PilotDecisionText -notmatch "Secure Pilot Vertical Slice")
) {
    throw "PDR-0002 does not approve MLAI-027."
}

$CurrentHandoverText = Get-Content -LiteralPath (
    Join-Path $ProjectRoot "docs\handover\CURRENT_HANDOVER.md"
) -Raw

if ($CurrentHandoverText -notmatch "MLAI-027.1 through MLAI-027.5") {
    throw "Current handover does not record MLAI-027.5 completion."
}

if ($CurrentHandoverText -notmatch "Start with \*\*MLAI-027.6") {
    throw "Current handover does not identify MLAI-027.6 as the next story."
}

$CompositionDecisionText = Get-Content -LiteralPath (
    Join-Path $ProjectRoot "governance\adrs\ADR-0009-canonical-application-composition.md"
) -Raw

if ($CompositionDecisionText -notmatch '(?m)^Accepted\r?$') {
    throw "ADR-0009 is not recorded as accepted."
}

if ($CompositionDecisionText -notmatch "CanonicalApplication") {
    throw "ADR-0009 does not preserve the canonical application boundary."
}

$ApiDecisionText = Get-Content -LiteralPath (
    Join-Path $ProjectRoot "governance\adrs\ADR-0012-pilot-api-workflow-contract.md"
) -Raw

if ($ApiDecisionText -notmatch '(?m)^Accepted\r?$') {
    throw "ADR-0012 is not recorded as accepted."
}

if (
    ($ApiDecisionText -notmatch "AuthorizedTenantApplication") -or
    ($ApiDecisionText -notmatch "idempotency")
) {
    throw "ADR-0012 does not preserve the authorized retry-safe API boundary."
}

$WorkspaceDecisionText = Get-Content -LiteralPath (
    Join-Path $ProjectRoot "governance\adrs\ADR-0013-thin-pilot-workspace.md"
) -Raw

if ($WorkspaceDecisionText -notmatch '(?m)^Accepted\r?$') {
    throw "ADR-0013 is not recorded as accepted."
}

if (
    ($WorkspaceDecisionText -notmatch "PilotApiService") -or
    ($WorkspaceDecisionText -notmatch "Real customer data")
) {
    throw "ADR-0013 does not preserve the thin synthetic workspace boundary."
}

Write-Host "MARKETINGLABAI HANDOVER REGRESSION TESTS PASSED" -ForegroundColor Green
