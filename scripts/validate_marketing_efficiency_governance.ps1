$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$ProjectRoot = Split-Path -Parent $PSScriptRoot
$Phrase = "5-10 hours saved per week"
$Reduction = "40-60%"
$OperatorRule = "three meaningful"
$Qualification = "designed to"

Write-Host ""
Write-Host "## MarketingLabAI Marketing Efficiency Governance Gate"
Write-Host ""
Write-Host "Customer claim validated: false"
Write-Host "Real-customer measurement authorized: false"

$Authorities = @(
    "AGENTS.md",
    "governance\product-constitution.md",
    "governance\locked-decision-register.md",
    "governance\quality-gates.md",
    "governance\adrs\ADR-0036-simple-operator-and-measured-marketing-efficiency.md",
    "docs\marketing-efficiency-evidence-protocol.md"
)

foreach ($RelativePath in $Authorities) {
    $Path = Join-Path $ProjectRoot $RelativePath
    if (-not (Test-Path -LiteralPath $Path -PathType Leaf)) {
        throw "Missing marketing-efficiency authority: $RelativePath"
    }
    $Content = Get-Content -LiteralPath $Path -Raw
    $Normalized = (($Content -split "\s+") -join " ").Trim()
    if ($Normalized -notmatch [regex]::Escape($Phrase)) {
        throw "Missing weekly target: $RelativePath"
    }
    if ($Normalized -notmatch [regex]::Escape($Reduction)) {
        throw "Missing reduction target: $RelativePath"
    }
}

$CombinedRaw = ($Authorities | ForEach-Object {
    Get-Content -LiteralPath (Join-Path $ProjectRoot $_) -Raw
}) -join "`n"
$Combined = (($CombinedRaw -split "\s+") -join " ").Trim()

foreach ($Required in @($OperatorRule, $Qualification, "Synthetic")) {
    if ($Combined -notmatch [regex]::Escape($Required)) {
        throw "Marketing-efficiency governance is incomplete: $Required"
    }
}

Write-Host ""
Write-Host "MARKETING EFFICIENCY GOVERNANCE GATE PASSED"
Write-Host "CLAIM STATUS: qualified target"
Write-Host "CUSTOMER CLAIM VALIDATED: false"
Write-Host "CLOUD MUTATION PERFORMED: false"
