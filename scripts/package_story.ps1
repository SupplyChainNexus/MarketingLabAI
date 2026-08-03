param(
    [Parameter(Mandatory = $true, Position = 0)]
    [ValidatePattern("^MLAI-\d+(\.\d+)?$")]
    [string]$StoryId,

    [Parameter(Mandatory = $true)]
    [string[]]$Paths,

    [string]$OutputDirectory = "_build\bundles"
)

$ErrorActionPreference = "Stop"

$OutputRoot = Join-Path (Get-Location).Path $OutputDirectory
New-Item -ItemType Directory -Path $OutputRoot -Force | Out-Null

$StagingRoot = Join-Path `
    $env:TEMP `
    ("MarketingLabAI_{0}_{1}" -f $StoryId, [Guid]::NewGuid())

New-Item -ItemType Directory -Path $StagingRoot -Force | Out-Null

try {
    foreach ($Path in $Paths) {
        if (-not (Test-Path $Path)) {
            throw "Missing package path: $Path"
        }

        $Resolved = (Resolve-Path $Path).Path
        $ProjectRoot = (Get-Location).Path.TrimEnd("\")
        $Relative = $Resolved.Substring($ProjectRoot.Length).TrimStart("\")
        $Destination = Join-Path $StagingRoot $Relative
        $DestinationParent = Split-Path $Destination -Parent

        New-Item `
            -ItemType Directory `
            -Path $DestinationParent `
            -Force |
        Out-Null

        Copy-Item `
            -Path $Resolved `
            -Destination $Destination `
            -Recurse `
            -Force
    }

    $ZipPath = Join-Path $OutputRoot "$StoryId.zip"

    if (Test-Path $ZipPath) {
        Remove-Item $ZipPath -Force
    }

    Compress-Archive `
        -Path (Join-Path $StagingRoot "*") `
        -DestinationPath $ZipPath `
        -CompressionLevel Optimal

    Write-Host "CREATED: $ZipPath"
}
finally {
    if (Test-Path $StagingRoot) {
        Remove-Item $StagingRoot -Recurse -Force
    }
}
