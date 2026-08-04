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

Write-Host "MARKETINGLABAI HANDOVER REGRESSION TESTS PASSED" -ForegroundColor Green
