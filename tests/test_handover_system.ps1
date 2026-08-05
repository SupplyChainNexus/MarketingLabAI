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
    "governance\pdrs\PDR-0003-marketing-decision-doctrine.md",
    "governance\adrs\ADR-0014-pilot-operations-release-gate.md",
    "governance\adrs\ADR-0015-positioning-intelligence-foundation.md",
    "governance\adrs\ADR-0016-governed-positioning-workflow-integration.md",
    "docs\pilot-release-gate.md",
    "docs\pilot-operations-runbook.md",
    "docs\privacy-and-data-handling.md",
    "docs\pilot-incident-response.md",
    "docs\launch-readiness-review.md",
    "backlog\MLAI-027.md",
    "backlog\MLAI-028.md",
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

$MarketingDoctrineText = Get-Content -LiteralPath (
    Join-Path $ProjectRoot "governance\pdrs\PDR-0003-marketing-decision-doctrine.md"
) -Raw

if ($MarketingDoctrineText -notmatch '(?m)^Accepted\r?$') {
    throw "PDR-0003 is not recorded as accepted."
}

$RequiredDoctrineTerms = @(
    "Customer segmentation",
    "Target selection",
    "Positioning",
    "Marketing-mix decisions",
    "Independent compliance",
    "Evidence-backed learning"
)

foreach ($RequiredTerm in $RequiredDoctrineTerms) {
    if ($MarketingDoctrineText -notmatch [regex]::Escape($RequiredTerm)) {
        throw "PDR-0003 is missing doctrine term: $RequiredTerm"
    }
}

if ($MarketingDoctrineText -notmatch "MLAI-027.6 remains an operational release story") {
    throw "PDR-0003 does not preserve MLAI-027.6 scope."
}

$CurrentHandoverText = Get-Content -LiteralPath (
    Join-Path $ProjectRoot "docs\handover\CURRENT_HANDOVER.md"
) -Raw

if ($CurrentHandoverText -notmatch "MLAI-027.1 through MLAI-027.6") {
    throw "Current handover does not record MLAI-027.6 completion."
}

if ($CurrentHandoverText -notmatch "customer pilot remains explicitly") {
    throw "Current handover does not preserve the founder pilot freeze."
}

if ($CurrentHandoverText -notmatch "MLAI-028.5") {
    throw "Current handover does not record governed positioning integration."
}

$PositioningIntegrationText = Get-Content -LiteralPath (
    Join-Path $ProjectRoot "governance\adrs\ADR-0016-governed-positioning-workflow-integration.md"
) -Raw

if ($PositioningIntegrationText -notmatch '(?m)^Accepted\r?$') {
    throw "ADR-0016 is not recorded as accepted."
}

if (
    ($PositioningIntegrationText -notmatch "same immutable\s+positioning version") -or
    ($PositioningIntegrationText -notmatch "customer\s+pilot")
) {
    throw "ADR-0016 does not preserve workflow and frozen-pilot boundaries."
}

$PositioningDecisionText = Get-Content -LiteralPath (
    Join-Path $ProjectRoot "governance\adrs\ADR-0015-positioning-intelligence-foundation.md"
) -Raw

if ($PositioningDecisionText -notmatch '(?m)^Accepted\r?$') {
    throw "ADR-0015 is not recorded as accepted."
}

if (
    ($PositioningDecisionText -notmatch "immutable") -or
    ($PositioningDecisionText -notmatch "customer-pilot freeze")
) {
    throw "ADR-0015 does not preserve lifecycle and pilot-freeze boundaries."
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

$OperationsDecisionText = Get-Content -LiteralPath (
    Join-Path $ProjectRoot "governance\adrs\ADR-0014-pilot-operations-release-gate.md"
) -Raw

if ($OperationsDecisionText -notmatch '(?m)^Accepted\r?$') {
    throw "ADR-0014 is not recorded as accepted."
}

if (
    ($OperationsDecisionText -notmatch "Waitress") -or
    ($OperationsDecisionText -notmatch "customer pilot unauthorized")
) {
    throw "ADR-0014 does not preserve runtime and pilot-freeze boundaries."
}

$StrategyDecisionText = Get-Content -LiteralPath (
    Join-Path $ProjectRoot "governance\adrs\ADR-0017-strategy-intelligence-foundation.md"
) -Raw

if ($StrategyDecisionText -notmatch '(?m)^Accepted\r?$') {
    throw "ADR-0017 is not recorded as accepted."
}

if (
    ($StrategyDecisionText -notmatch "approved positioning") -or
    ($StrategyDecisionText -notmatch "customer pilot remains founder-frozen")
) {
    throw "ADR-0017 does not preserve strategy dependency and pilot boundaries."
}

if (
    ($CurrentHandoverText -notmatch "MLAI-029.1") -or
    ($CurrentHandoverText -notmatch "MLAI-029.6") -or
    ($CurrentHandoverText -notmatch "Strand Auto Parts")
) {
    throw "Current handover does not preserve the locked Strategy sequence."
}

if (
    ($CurrentHandoverText -notmatch "MLAI-029.2") -or
    ($CurrentHandoverText -notmatch "user-supplied PESTLE") -or
    ($CurrentHandoverText -notmatch "without live research")
) {
    throw "Current handover does not preserve Strategy synthesis boundaries."
}

if (
    ($CurrentHandoverText -notmatch "MLAI-029.3") -or
    ($CurrentHandoverText -notmatch "explicit strategic choices") -or
    ($CurrentHandoverText -notmatch "does not invent")
) {
    throw "Current handover does not preserve objective and choice boundaries."
}

if (
    ($CurrentHandoverText -notmatch "MLAI-029.4") -or
    ($CurrentHandoverText -notmatch "minimum four-part marketing mix") -or
    ($CurrentHandoverText -notmatch "does\s+not invent pricing")
) {
    throw "Current handover does not preserve marketing-mix boundaries."
}

Write-Host "MARKETINGLABAI HANDOVER REGRESSION TESTS PASSED" -ForegroundColor Green
