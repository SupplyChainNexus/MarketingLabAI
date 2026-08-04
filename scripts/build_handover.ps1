[CmdletBinding()]
param(
    [string]$OutputRoot = "C:\Ai Projects\ToolkitTemp\MarketingLabAIHandover"
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$ProjectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$Timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
$BundleRoot = Join-Path $OutputRoot "MarketingLabAI_handover_$Timestamp"
$EvidenceRoot = Join-Path $BundleRoot "repository_evidence"

$RequiredFiles = @(
    "AGENTS.md",
    "governance\authority-hierarchy.md",
    "governance\product-constitution.md",
    "governance\locked-decision-register.md",
    "governance\decision-change-control.md",
    "governance\product-capability-map.md",
    "governance\definition-of-done.md",
    "governance\quality-gates.md",
    "docs\product_vision.md",
    "docs\intelligence_roadmap.md",
    "docs\architecture\ARCHITECTURE_PRINCIPLES.md",
    "docs\engineering\continuity.md",
    "docs\handover\CURRENT_HANDOVER.md"
)

$MissingFiles = @(
    $RequiredFiles | Where-Object {
        -not (Test-Path (Join-Path $ProjectRoot $_) -PathType Leaf)
    }
)

if ($MissingFiles.Count -gt 0) {
    throw "Required handover files are missing: $($MissingFiles -join ', ')"
}

New-Item -ItemType Directory -Path $EvidenceRoot -Force | Out-Null

foreach ($RelativePath in $RequiredFiles) {
    $SourcePath = Join-Path $ProjectRoot $RelativePath
    $DestinationPath = Join-Path $EvidenceRoot $RelativePath
    $DestinationDirectory = Split-Path $DestinationPath -Parent
    New-Item -ItemType Directory -Path $DestinationDirectory -Force | Out-Null
    Copy-Item -LiteralPath $SourcePath -Destination $DestinationPath -Force
}

$CollectionRoots = @("backlog", "governance\adrs", "governance\pdrs")
foreach ($RelativeRoot in $CollectionRoots) {
    $SourceRoot = Join-Path $ProjectRoot $RelativeRoot
    if (-not (Test-Path $SourceRoot -PathType Container)) {
        continue
    }

    Get-ChildItem -LiteralPath $SourceRoot -File -Recurse | ForEach-Object {
        $RelativePath = $_.FullName.Substring($ProjectRoot.Length + 1)
        $DestinationPath = Join-Path $EvidenceRoot $RelativePath
        $DestinationDirectory = Split-Path $DestinationPath -Parent
        New-Item -ItemType Directory -Path $DestinationDirectory -Force | Out-Null
        Copy-Item -LiteralPath $_.FullName -Destination $DestinationPath -Force
    }
}

$StateLines = New-Object System.Collections.Generic.List[string]
$StateLines.Add("MarketingLabAI Handover State")
$StateLines.Add("Generated: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss zzz')")
$StateLines.Add("Project root: $ProjectRoot")
$StateLines.Add("")

Push-Location $ProjectRoot
try {
    $StateLines.Add("Branch: $(& git branch --show-current)")
    $StateLines.Add("Commit: $(& git rev-parse HEAD)")
    $StateLines.Add("")
    $StateLines.Add("Git status:")
    $Status = @(& git status --short)
    if ($Status.Count -eq 0) {
        $StateLines.Add("CLEAN")
    }
    else {
        foreach ($Line in $Status) { $StateLines.Add($Line) }
    }
    $StateLines.Add("")
    $StateLines.Add("Recent history:")
    foreach ($Line in @(& git log --oneline --decorate -20)) {
        $StateLines.Add($Line)
    }
}
finally {
    Pop-Location
}

$Utf8WithoutBom = New-Object System.Text.UTF8Encoding($false)
$StatePath = Join-Path $BundleRoot "REPOSITORY_STATE.txt"
[System.IO.File]::WriteAllLines($StatePath, $StateLines, $Utf8WithoutBom)

$ArchivePath = "$BundleRoot.zip"
Compress-Archive -Path (Join-Path $BundleRoot "*") -DestinationPath $ArchivePath -Force

Write-Host "HANDOVER CREATED: $BundleRoot" -ForegroundColor Green
Write-Host "ARCHIVE: $ArchivePath" -ForegroundColor Green
