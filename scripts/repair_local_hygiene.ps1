param(
    [ValidateSet("check", "plan-repair", "apply-repair")]
    [string]$Command = "check",
    [string]$PythonPath = "",
    [string]$ReplacementRoot = "",
    [string]$OutputRoot = "",
    [string]$Plan = ""
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
if (-not $PythonPath) {
    $VenvPython = Join-Path $RepoRoot ".venv\Scripts\python.exe"
    if (Test-Path -LiteralPath $VenvPython -PathType Leaf) {
        $PythonPath = $VenvPython
    }
    else {
        $PythonPath = (Get-Command "python.exe" -ErrorAction Stop).Source
    }
}

Write-Host "=== CANONICAL REPOSITORY INTEGRITY BOUNDARY ==="
Write-Host "Command: $Command"
Write-Host "Repository byte rewriting by this launcher: false"
Write-Host "Cloud CLI execution: false"
Write-Host "Release-state modification: false"

$Arguments = @("-m", "tools.infrastructure_coherence", "--root", $RepoRoot, $Command)
if ($Command -eq "plan-repair") {
    if (-not $ReplacementRoot -or -not $OutputRoot) {
        throw "plan-repair requires -ReplacementRoot and -OutputRoot."
    }
    $Arguments += @("--replacement-root", $ReplacementRoot, "--output-root", $OutputRoot)
}
elseif ($Command -eq "apply-repair") {
    if (-not $Plan) { throw "apply-repair requires -Plan." }
    $Arguments += @("--plan", $Plan)
}

Push-Location $RepoRoot
try {
    & $PythonPath @Arguments
    if ($LASTEXITCODE -ne 0) { throw "Repository integrity command failed." }
}
finally {
    Pop-Location
}

Write-Host "REPOSITORY_INTEGRITY_COMMAND_COMPLETED"
Write-Host "Cloud operation performed: false"
Write-Host "Release state modified: false"
