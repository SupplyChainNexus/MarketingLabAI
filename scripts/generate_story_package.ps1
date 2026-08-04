param(
    [Parameter(Mandatory = $true)]
    [string]$ManifestPath,

    [string]$OutputRoot = "C:\Ai Projects\ToolkitTemp",

    [switch]$Force
)

$ErrorActionPreference = "Stop"

function ConvertTo-PsSingleQuotedLiteral {
    param([AllowEmptyString()][string]$Value)
    return "'" + $Value.Replace("'", "''") + "'"
}

function ConvertTo-PsArrayItems {
    param([object[]]$Values)
    if ($null -eq $Values) { return "" }
    return (($Values | ForEach-Object {
        "    " + (ConvertTo-PsSingleQuotedLiteral ([string]$_))
    }) -join ",`r`n")
}

function Write-Utf8NoBom {
    param(
        [Parameter(Mandatory = $true)][string]$Path,
        [Parameter(Mandatory = $true)][string]$Content
    )
    $Encoding = New-Object System.Text.UTF8Encoding($false)
    [System.IO.File]::WriteAllText($Path, $Content, $Encoding)
}

function Resolve-Template {
    param(
        [Parameter(Mandatory = $true)][string]$TemplatePath,
        [Parameter(Mandatory = $true)][hashtable]$Tokens
    )
    $Text = [System.IO.File]::ReadAllText($TemplatePath)
    foreach ($Key in $Tokens.Keys) {
        $Text = $Text.Replace("{{${Key}}}", [string]$Tokens[$Key])
    }
    $Remaining = [regex]::Matches($Text, '\{\{[A-Z0-9_]+\}\}')
    if ($Remaining.Count -gt 0) {
        throw "Unresolved template token: $($Remaining[0].Value)"
    }
    return $Text
}

$ResolvedManifest = (Resolve-Path $ManifestPath).Path
$Manifest = Get-Content -Raw $ResolvedManifest | ConvertFrom-Json
$Required = @(
    "storyId", "title", "slug", "projectRoot", "sourceRoot",
    "installFiles", "newFiles", "compileFiles", "focusedTestModules",
    "expectedStatus"
)
foreach ($Name in $Required) {
    if ($null -eq $Manifest.$Name) { throw "Manifest property is required: $Name" }
}
if ([string]$Manifest.storyId -notmatch '^MLAI-\d+(\.\d+)?$') {
    throw "Invalid storyId: $($Manifest.storyId)"
}

$SafeId = ([string]$Manifest.storyId).ToLowerInvariant().Replace("-", "_").Replace(".", "_")
$PackageName = "$($Manifest.storyId)_$($Manifest.slug)"
$PackageRoot = Join-Path $OutputRoot $PackageName
if (Test-Path $PackageRoot) {
    if (-not $Force) { throw "Package already exists: $PackageRoot (use -Force to replace it)" }
    Remove-Item $PackageRoot -Recurse -Force
}
New-Item -ItemType Directory -Path (Join-Path $PackageRoot "payload") -Force | Out-Null

$SourceRoot = [string]$Manifest.sourceRoot
foreach ($RelativePath in $Manifest.installFiles) {
    $Source = Join-Path $SourceRoot ([string]$RelativePath)
    if (-not (Test-Path $Source -PathType Leaf)) { throw "Source file missing: $Source" }
    $Destination = Join-Path (Join-Path $PackageRoot "payload") ([string]$RelativePath)
    New-Item -ItemType Directory -Path (Split-Path $Destination -Parent) -Force | Out-Null
    Copy-Item $Source $Destination -Force
}

$TemplateRoot = Join-Path (Split-Path $PSScriptRoot -Parent) "templates\story_package"
$ImportArguments = @()
if ([string]$Manifest.importCommand) { $ImportArguments = @("-c", [string]$Manifest.importCommand) }
$HasImportToken = if ($ImportArguments.Count -gt 0) { '$true' } else { '$false' }

$Tokens = @{
    STORY_ID = [string]$Manifest.storyId
    STORY_TITLE = [string]$Manifest.title
    PROJECT_ROOT = [string]$Manifest.projectRoot
    INSTALL_FILES = ConvertTo-PsArrayItems $Manifest.installFiles
    NEW_FILES = ConvertTo-PsArrayItems $Manifest.newFiles
    COMPILE_ARGUMENTS = ConvertTo-PsArrayItems (@("-m", "py_compile") + @($Manifest.compileFiles))
    FOCUSED_TEST_ARGUMENTS = ConvertTo-PsArrayItems (@("-m", "unittest") + @($Manifest.focusedTestModules) + @("-v"))
    IMPORT_ARGUMENTS = ConvertTo-PsArrayItems $ImportArguments
    EXPECTED_STATUS = ConvertTo-PsArrayItems $Manifest.expectedStatus
    HAS_IMPORT = $HasImportToken
}

$Installer = Resolve-Template (Join-Path $TemplateRoot "install.ps1.template") $Tokens
$Validator = Resolve-Template (Join-Path $TemplateRoot "validate.ps1.template") $Tokens
$InstallerPath = Join-Path $PackageRoot "install_${SafeId}.ps1"
$ValidatorPath = Join-Path $PackageRoot "validate_${SafeId}.ps1"
Write-Utf8NoBom $InstallerPath $Installer
Write-Utf8NoBom $ValidatorPath $Validator

foreach ($GeneratedPath in @($InstallerPath, $ValidatorPath)) {
    $Generated = [System.IO.File]::ReadAllText($GeneratedPath)
    if ($Generated -notmatch 'function Invoke-PythonLogged') {
        throw "Generated script lacks Invoke-PythonLogged: $GeneratedPath"
    }
    if ($Generated -match '(?m)^\s*(?:&\s+)?python(?:\.exe)?\s+-m\s+(?:unittest|py_compile)') {
        throw "Generated script contains a direct Python command: $GeneratedPath"
    }
    if ($Generated -match 'utf8NoBOM') {
        throw "Generated script is not Windows PowerShell 5.1-compatible: $GeneratedPath"
    }
}

Write-Host "CREATED: $PackageRoot"
Write-Host "INSTALLER: $InstallerPath"
Write-Host "VALIDATOR: $ValidatorPath"
