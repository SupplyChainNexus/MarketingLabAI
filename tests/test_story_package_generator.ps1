$ErrorActionPreference = "Stop"
$Generator = Join-Path (Split-Path $PSScriptRoot -Parent) "scripts\generate_story_package.ps1"
$GeneratorText = Get-Content -Raw $Generator
$Templates = Get-ChildItem (Join-Path (Split-Path $PSScriptRoot -Parent) "templates\story_package") -File

if ($GeneratorText -match '(?i)-Encoding\s+utf8NoBOM') {
    throw "Generator uses an encoding name unsupported by PowerShell 5.1."
}
foreach ($Template in $Templates) {
    $Text = Get-Content -Raw $Template.FullName
    if ($Text -notmatch 'function Invoke-PythonLogged') { throw "Missing Python helper: $($Template.Name)" }
    if ($Text -match '(?m)^\s*(?:&\s+)?python(?:\.exe)?\s+-m\s+(?:unittest|py_compile)') {
        throw "Direct Python command found: $($Template.Name)"
    }
    if ($Text -match 'if \(\$LASTEXITCODE -ne 0\) \{ throw "(?:Focused|Compilation|Complete|Import)') {
        throw "Python result incorrectly checks LASTEXITCODE: $($Template.Name)"
    }
}
Write-Host "NEXUS FORGE GENERATOR REGRESSION TESTS PASSED"
