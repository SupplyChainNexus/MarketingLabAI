param(
    [switch]$VerboseTests
)

$ErrorActionPreference = "Stop"

function Invoke-CheckedCommand {
    param(
        [Parameter(Mandatory)]
        [string]$Description,

        [Parameter(Mandatory)]
        [scriptblock]$Command
    )

    Write-Host ""
    Write-Host $Description

    & $Command

    if ($LASTEXITCODE -ne 0) {
        throw "$Description failed with exit code $LASTEXITCODE."
    }
}

Write-Host ""
Write-Host "Running MarketingLabAI checks..."
Write-Host ""

Invoke-CheckedCommand `
    -Description "[1/4] Checking formatting..." `
    -Command {
        black --check app tests
    }

Invoke-CheckedCommand `
    -Description "[2/4] Running Ruff..." `
    -Command {
        ruff check app tests
    }

Invoke-CheckedCommand `
    -Description "[3/4] Compiling Python files..." `
    -Command {
        python -m compileall -q app tests
    }

Invoke-CheckedCommand `
    -Description "[4/4] Running tests..." `
    -Command {
        if ($VerboseTests) {
            python -m unittest discover -s tests -v
        }
        else {
            python -m unittest discover -s tests
        }
    }

Write-Host ""
Write-Host "All checks passed."
