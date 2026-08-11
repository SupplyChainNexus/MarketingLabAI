[CmdletBinding()]
param(
    [string]$PythonPath,

    [Parameter(Position = 0, ValueFromRemainingArguments = $true)]
    [string[]]$ControlPlaneArguments
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$ProjectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path

if (-not $PythonPath) {
    $Candidates = @()
    if ($env:VIRTUAL_ENV) {
        $Candidates += Join-Path $env:VIRTUAL_ENV "Scripts\python.exe"
    }
    $Candidates += Join-Path $ProjectRoot ".venv\Scripts\python.exe"
    $PythonPath = @(
        $Candidates | Where-Object {
            Test-Path -LiteralPath $_ -PathType Leaf
        }
    ) | Select-Object -First 1
}

if (-not $PythonPath -or
    -not (Test-Path -LiteralPath $PythonPath -PathType Leaf)) {
    throw (
        "Pinned Python was not found. Activate the repository .venv or pass " +
        "-PythonPath with the exact Python executable selected by CI."
    )
}
if (-not $ControlPlaneArguments -or @($ControlPlaneArguments).Count -eq 0) {
    throw "A release-control command is required. Use doctor, status, plan, approve, apply, resume or verify."
}

$ResolvedPython = (Resolve-Path -LiteralPath $PythonPath).Path

Push-Location $ProjectRoot
try {
    & $ResolvedPython -m tools.release_control @ControlPlaneArguments
    if ($LASTEXITCODE -ne 0) {
        throw "Release control plane failed with exit code $LASTEXITCODE."
    }
}
finally {
    Pop-Location
}
