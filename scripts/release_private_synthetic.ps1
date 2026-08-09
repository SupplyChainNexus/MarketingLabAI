param(
    [Parameter(Mandatory)]
    [ValidateSet("Validate", "Start", "Status", "Verify", "Record")]
    [string]$Action,

    [string]$Run,
    [string]$Commit,
    [string]$Image,
    [string]$Operator,
    [string]$Gate,
    [ValidateSet("passed", "failed")]
    [string]$Outcome,
    [string]$Evidence,
    [switch]$MutationPerformed,
    [string]$AuthorizationReference,
    [string]$FailureClassification,
    [string]$Remediation,
    [string]$SafeNextAction,
    [string]$RunsRoot = "C:\Ai Projects\ToolkitTemp\MLAI-031.3_release_runs"
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$ProjectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$ProjectVenvPython = "$ProjectRoot.venv\Scripts\python.exe"

if (Test-Path -LiteralPath $ProjectVenvPython -PathType Leaf) {
    $Python = $ProjectVenvPython
}
else {
    $Python = (Get-Command "python" -ErrorAction Stop).Source
}

function Invoke-Controller {
    param([string[]]$ControllerArguments)

    & $Python -m deployment.release_controller @ControllerArguments
    if ($LASTEXITCODE -ne 0) {
        throw "Release controller failed with exit code $LASTEXITCODE."
    }
}

Push-Location $ProjectRoot

try {
    Write-Host ""
    Write-Host "MarketingLabAI Private Synthetic Release Controller"
    Write-Host "----------------------------------------------------"
    Write-Host "Cloud mutation performed by controller: false"
    Write-Host "Public access authorized: false"
    Write-Host "Real-customer data authorized: false"

    switch ($Action) {
        "Validate" {
            Invoke-Controller -ControllerArguments @("validate-catalog")
        }
        "Start" {
            if (-not $Commit -or -not $Image -or -not $Operator) {
                throw "Start requires Commit, Image and Operator."
            }
            Invoke-Controller -ControllerArguments @(
                "start",
                "--runs-root", $RunsRoot,
                "--commit", $Commit,
                "--image", $Image,
                "--operator", $Operator
            )
        }
        "Status" {
            if (-not $Run) { throw "Status requires Run." }
            Invoke-Controller -ControllerArguments @("status", "--run", $Run)
        }
        "Verify" {
            if (-not $Run) { throw "Verify requires Run." }
            Invoke-Controller -ControllerArguments @("verify", "--run", $Run)
        }
        "Record" {
            if (-not $Run -or -not $Gate -or -not $Outcome -or
                -not $Evidence -or -not $Operator) {
                throw "Record requires Run, Gate, Outcome, Evidence and Operator."
            }
            $Arguments = @(
                "record",
                "--run", $Run,
                "--gate", $Gate,
                "--outcome", $Outcome,
                "--evidence", $Evidence,
                "--operator", $Operator
            )
            if ($MutationPerformed) {
                $Arguments += "--mutation-performed"
            }
            if ($AuthorizationReference) {
                $Arguments += @("--authorization-reference", $AuthorizationReference)
            }
            if ($FailureClassification) {
                $Arguments += @("--failure-classification", $FailureClassification)
            }
            if ($Remediation) {
                $Arguments += @("--remediation", $Remediation)
            }
            if ($SafeNextAction) {
                $Arguments += @("--safe-next-action", $SafeNextAction)
            }
            Invoke-Controller -ControllerArguments $Arguments
        }
    }
}
finally {
    Pop-Location
}

Write-Host ""
Write-Host "RELEASE CONTROLLER ACTION COMPLETED"
Write-Host "Cloud mutation performed by controller: false"
Write-Host "Deployment executed by controller: false"
