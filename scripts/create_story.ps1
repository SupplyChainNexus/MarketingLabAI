param(
    [Parameter(Mandatory = $true, Position = 0)]
    [ValidatePattern("^MLAI-\d+(\.\d+)?$")]
    [string]$StoryId,

    [Parameter(Mandatory = $true, Position = 1)]
    [ValidateNotNullOrEmpty()]
    [string]$Title
)

$ErrorActionPreference = "Stop"

$BacklogDirectory = ".\backlog"
New-Item -ItemType Directory -Path $BacklogDirectory -Force | Out-Null

$StoryPath = Join-Path $BacklogDirectory "$StoryId.md"

if (Test-Path $StoryPath) {
    throw "Story already exists: $StoryPath"
}

$Content = @(
    "# $StoryId — $Title"
    ""
    "## Status"
    ""
    "Ready"
    ""
    "## Objective"
    ""
    "Describe the outcome this story must deliver."
    ""
    "## Business Value"
    ""
    "Describe the user or business value."
    ""
    "## Dependencies"
    ""
    "- None recorded."
    ""
    "## Technical Design"
    ""
    "Document the agreed architecture before implementation."
    ""
    "## Acceptance Criteria"
    ""
    "- [ ] Required behaviour is implemented."
    "- [ ] Missing context is handled without invented facts."
    "- [ ] Focused tests pass."
    "- [ ] Affected regression tests pass."
    "- [ ] Documentation matches implemented behaviour."
    ""
    "## Validation Commands"
    ""
    '```powershell'
    ".\scripts\format.ps1"
    "python -m unittest discover -s tests -p `"test_*.py`""
    "git diff --check"
    "git status --short"
    '```'
    ""
    "## Completion Evidence"
    ""
    "Not yet completed."
    ""
    "## Related ADRs"
    ""
    "- None recorded."
)

Set-Content `
    -Path $StoryPath `
    -Value $Content `
    -Encoding utf8

Write-Host "CREATED: $StoryPath"
