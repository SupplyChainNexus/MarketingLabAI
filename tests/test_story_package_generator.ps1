$ErrorActionPreference = "Stop"
$Generator = Join-Path (Split-Path $PSScriptRoot -Parent) "scripts\generate_story_package.ps1"
$GeneratorText = Get-Content -Raw $Generator
$Templates = Get-ChildItem (Join-Path (Split-Path $PSScriptRoot -Parent) "templates\story_package") -File

if ($GeneratorText -match '(?i)-Encoding\s+utf8NoBOM') {
    throw "Generator uses an encoding name unsupported by PowerShell 5.1."
}
$InstallerTemplate = Get-Content -Raw (Join-Path (Split-Path $PSScriptRoot -Parent) "templates\story_package\install.ps1.template")
$ValidatorTemplate = Get-Content -Raw (Join-Path (Split-Path $PSScriptRoot -Parent) "templates\story_package\validate.ps1.template")
if ($InstallerTemplate -notmatch 'git rev-parse HEAD') {
    throw "Installer template does not verify the repository baseline."
}
if ($InstallerTemplate -notmatch 'Baseline mismatch') {
    throw "Installer template does not stop on a baseline mismatch."
}
if ($ValidatorTemplate -notmatch 'git status --short --untracked-files=all') {
    throw "Validator template does not expand nested untracked files."
}
foreach ($Template in $Templates) {
    $Text = Get-Content -Raw $Template.FullName
    if ($Text -notmatch 'function Invoke-PythonLogged') { throw "Missing Python helper: $($Template.Name)" }
    if ($Text -notmatch '\$PreviousErrorActionPreference\s*=\s*\$ErrorActionPreference') {
        throw "Python helper does not preserve ErrorActionPreference: $($Template.Name)"
    }
    if ($Text -notmatch '\$ErrorActionPreference\s*=\s*"Continue"') {
        throw "Python helper cannot safely capture native stderr on PowerShell 5.1: $($Template.Name)"
    }
    if ($Text -notmatch '\$ErrorActionPreference\s*=\s*\$PreviousErrorActionPreference') {
        throw "Python helper does not restore ErrorActionPreference: $($Template.Name)"
    }
    if ($Text -notmatch '\$_\s+-is\s+\[System\.Management\.Automation\.ErrorRecord\]') {
        throw "Python helper does not unwrap PowerShell 5.1 native stderr records: $($Template.Name)"
    }
    if ($Text -notmatch '\$Message\s*=\s*\$_\.Exception\.Message') {
        throw "Python helper can leak RemoteException type names: $($Template.Name)"
    }
    if ($Text -match '(?m)^\s*(?:&\s+)?python(?:\.exe)?\s+-m\s+(?:unittest|py_compile)') {
        throw "Direct Python command found: $($Template.Name)"
    }
    if ($Text -match 'if \(\$LASTEXITCODE -ne 0\) \{ throw "(?:Focused|Compilation|Complete|Import)') {
        throw "Python result incorrectly checks LASTEXITCODE: $($Template.Name)"
    }
}
Write-Host "MARKETINGLABAI STORY PACKAGE GENERATOR REGRESSION TESTS PASSED"
