param(
    [Parameter(Mandatory = $true, Position = 0)]
    [ValidatePattern("^MLAI-\d+(\.\d+)?$")]
    [string]$StoryId,

    [string]$OutputDirectory = "docs\engineering_reviews"
)

$ErrorActionPreference = "Stop"

$OutputRoot = Join-Path (Get-Location).Path $OutputDirectory
New-Item -ItemType Directory -Path $OutputRoot -Force | Out-Null

$OutputPath = Join-Path $OutputRoot "$StoryId-review.md"
$StoryPath = ".\backlog\$StoryId.md"

$Lines = New-Object "System.Collections.Generic.List[string]"

$Lines.Add("# Engineering Review — $StoryId")
$Lines.Add("")
$Lines.Add("Generated: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')")
$Lines.Add("")
$Lines.Add("## Branch")
$Lines.Add("")
$Lines.Add('```text')
$Lines.Add([string](git branch --show-current))
$Lines.Add('```')
$Lines.Add("")
$Lines.Add("## Git Status")
$Lines.Add("")
$Lines.Add('```text')

foreach ($Line in (git status --short)) {
    $Lines.Add([string]$Line)
}

$Lines.Add('```')
$Lines.Add("")
$Lines.Add("## Diff Summary")
$Lines.Add("")
$Lines.Add('```text')

foreach ($Line in (git diff --stat)) {
    $Lines.Add([string]$Line)
}

$Lines.Add('```')
$Lines.Add("")
$Lines.Add("## Diff Check")
$Lines.Add("")
$Lines.Add('```text')

$DiffCheck = git diff --check 2>&1

if ($DiffCheck) {
    foreach ($Line in $DiffCheck) {
        $Lines.Add([string]$Line)
    }
}
else {
    $Lines.Add("PASS")
}

$Lines.Add('```')
$Lines.Add("")
$Lines.Add("## Story Record")
$Lines.Add("")

if (Test-Path $StoryPath) {
    foreach ($Line in (Get-Content $StoryPath)) {
        $Lines.Add([string]$Line)
    }
}
else {
    $Lines.Add("Story file not found: $StoryPath")
}

Set-Content `
    -Path $OutputPath `
    -Value $Lines `
    -Encoding utf8

Write-Host "CREATED: $OutputPath"
