$ErrorActionPreference = "Stop"

Write-Host ""
Write-Host "MarketingLabAI - Generate Review Pack"
Write-Host "====================================="
Write-Host ""

python tools\review_pack.py --run-checks

if ($LASTEXITCODE -ne 0) {
    throw "Review-pack generation failed."
}

Write-Host ""
Write-Host "Open the generated report with:"
Write-Host "code .\docs\THIRD_PARTY_REVIEW.md"
Write-Host ""