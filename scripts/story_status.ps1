param(
    [string]$StoryId = ""
)

$ErrorActionPreference = "Stop"

Write-Host "`n--- Branch ---"
git branch --show-current

Write-Host "`n--- Git status ---"
git status --short

Write-Host "`n--- Recent commits ---"
git log --oneline -10

if ($StoryId.Trim()) {
    $StoryPath = ".\backlog\$StoryId.md"

    Write-Host "`n--- Story ---"

    if (Test-Path $StoryPath) {
        Get-Content $StoryPath -Raw
    }
    else {
        Write-Host "MISSING: $StoryPath"
    }
}
else {
    Write-Host "`n--- Backlog stories ---"

    if (Test-Path ".\backlog") {
        Get-ChildItem ".\backlog" -File -Filter "MLAI-*.md" |
        Sort-Object Name |
        Select-Object Name, LastWriteTime
    }
    else {
        Write-Host "No backlog directory exists."
    }
}
