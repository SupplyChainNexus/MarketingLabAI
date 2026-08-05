$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

Set-Location (Resolve-Path (Join-Path $PSScriptRoot ".."))
python -m waitress.runner --call app.operations.runtime:create_application `
    --host=127.0.0.1 `
    --port=8080 `
    --threads=4 `
    --channel-timeout=30

if ($LASTEXITCODE -ne 0) {
    throw "Pilot service exited with an error."
}
