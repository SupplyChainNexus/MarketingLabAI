param(
    [Parameter(Mandatory = $true, Position = 0)]
    [ValidateNotNullOrEmpty()]
    [string]$Topic,

    [string]$StoryId = "",

    [string[]]$Roots = @(
        "app",
        "tests",
        "docs",
        "governance",
        "backlog"
    ),

    [string]$OutputDirectory = "docs\build_context"
)

$ErrorActionPreference = "Stop"

$ProjectRoot = (Get-Location).Path

function Get-ProjectRelativePath {
    param(
        [Parameter(Mandatory = $true)]
        [string]$FullPath
    )

    $BasePath = $ProjectRoot.TrimEnd("\") + "\"
    $BaseUri = New-Object System.Uri($BasePath)
    $ResolvedPath = (Resolve-Path $FullPath).Path
    $FileUri = New-Object System.Uri($ResolvedPath)

    return [System.Uri]::UnescapeDataString(
        $BaseUri.MakeRelativeUri($FileUri).ToString()
    ).Replace("/", "\")
}

$NormalisedTopic = $Topic.Trim().ToLowerInvariant()

if (-not $NormalisedTopic) {
    throw "Topic is required."
}

$TopicPatterns = @{
    "customer" = @(
        "customer",
        "persona",
        "segment",
        "audience",
        "journey"
    )
    "product" = @(
        "product",
        "sku",
        "catalog",
        "warranty",
        "feature",
        "benefit"
    )
    "prompt" = @(
        "prompt",
        "brief",
        "composer",
        "composition",
        "prompt_pack",
        "section",
        "campaign",
        "compliance"
    )
    "seo" = @(
        "seo",
        "search",
        "keyword",
        "metadata",
        "ranking",
        "serp"
    )
    "campaign" = @(
        "campaign",
        "generation",
        "channel",
        "creative",
        "advert",
        "ad_"
    )
    "architecture" = @(
        "architecture",
        "adr",
        "principle",
        "governance",
        "methodology",
        "quality"
    )
}

if ($TopicPatterns.ContainsKey($NormalisedTopic)) {
    $Patterns = $TopicPatterns[$NormalisedTopic]
}
else {
    $Patterns = @($NormalisedTopic)
}

$ExistingRoots = @()

foreach ($Root in $Roots) {
    if (Test-Path $Root) {
        $ExistingRoots += $Root
    }
}

if ($ExistingRoots.Count -eq 0) {
    throw "None of the configured roots exist."
}

$CandidateFiles = Get-ChildItem `
    -Path $ExistingRoots `
    -Recurse `
    -File `
    -ErrorAction SilentlyContinue |
Where-Object {
    $PathText = $_.FullName.ToLowerInvariant()
    $Matches = $false

    foreach ($Pattern in $Patterns) {
        if ($PathText.Contains($Pattern.ToLowerInvariant())) {
            $Matches = $true
            break
        }
    }

    $Matches
} |
Sort-Object FullName -Unique

$SafeTopic = ($NormalisedTopic -replace "[^a-z0-9_-]", "_")
$StoryPrefix = ""

if ($StoryId.Trim()) {
    $StoryPrefix = ($StoryId.Trim() -replace "[^A-Za-z0-9._-]", "_") + "_"
}

$OutputDirectoryPath = Join-Path $ProjectRoot $OutputDirectory
New-Item -ItemType Directory -Path $OutputDirectoryPath -Force | Out-Null

$OutputPath = Join-Path `
    $OutputDirectoryPath `
    ("{0}{1}_CONTEXT.txt" -f $StoryPrefix, $SafeTopic.ToUpperInvariant())

$Output = New-Object "System.Collections.Generic.List[string]"

$Output.Add("MarketingLabAI Engineering Build Context")
$Output.Add("Story: $StoryId")
$Output.Add("Topic: $Topic")
$Output.Add("Generated: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')")
$Output.Add("Project root: $ProjectRoot")
$Output.Add("")

$Output.Add("============================================================")
$Output.Add("DISCOVERED FILES")
$Output.Add("============================================================")

foreach ($File in $CandidateFiles) {
    $Output.Add(
        (Get-ProjectRelativePath -FullPath $File.FullName)
    )
}

$Output.Add("")

foreach ($File in $CandidateFiles) {
    $RelativePath = Get-ProjectRelativePath -FullPath $File.FullName

    $Output.Add("============================================================")
    $Output.Add("FILE: $RelativePath")
    $Output.Add("============================================================")

    try {
        foreach ($Line in (Get-Content $File.FullName -ErrorAction Stop)) {
            $Output.Add([string]$Line)
        }
    }
    catch {
        $Output.Add("ERROR READING FILE: $($_.Exception.Message)")
    }

    $Output.Add("")
}

$SearchExpression = ($Patterns | ForEach-Object {
    [Regex]::Escape($_)
}) -join "|"

$Output.Add("============================================================")
$Output.Add("TOPIC REFERENCES")
$Output.Add("============================================================")

$GitArguments = @(
    "grep",
    "-n",
    "-i",
    "-E",
    $SearchExpression,
    "--"
) + $ExistingRoots

$GitOutput = & git @GitArguments 2>&1

if ($LASTEXITCODE -le 1) {
    foreach ($Line in $GitOutput) {
        $Output.Add([string]$Line)
    }
}
else {
    $Output.Add("git grep failed with exit code $LASTEXITCODE")

    foreach ($Line in $GitOutput) {
        $Output.Add([string]$Line)
    }
}

$Output.Add("")
$Output.Add("============================================================")
$Output.Add("CURRENT GIT STATE")
$Output.Add("============================================================")

foreach ($Line in (git status --short)) {
    $Output.Add([string]$Line)
}

$Output.Add("")
$Output.Add("============================================================")
$Output.Add("RECENT COMMITS")
$Output.Add("============================================================")

foreach ($Line in (git log --oneline -15)) {
    $Output.Add([string]$Line)
}

Set-Content `
    -Path $OutputPath `
    -Value $Output `
    -Encoding utf8

Write-Host "CREATED: $OutputPath"

Get-Item $OutputPath |
Format-List Name, Length, LastWriteTime

Write-Host "`nFirst 8 lines:"
Get-Content $OutputPath -First 8

Write-Host "`nLast 8 lines:"
Get-Content $OutputPath -Tail 8
