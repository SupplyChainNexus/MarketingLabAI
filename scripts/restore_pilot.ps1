param(
    [Parameter(Mandatory = $true)][string]$BackupPath,
    [Parameter(Mandatory = $true)][string]$DestinationPath
)
$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest
Set-Location (Resolve-Path (Join-Path $PSScriptRoot ".."))
python -m app.operations.cli restore $BackupPath $DestinationPath
if ($LASTEXITCODE -ne 0) { throw "Pilot restore failed." }
