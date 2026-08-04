# Nexus Forge Story Package Generator

This toolkit addition generates consistent MarketingLabAI installer and validator
scripts from a JSON manifest. Python output is captured and replayed through a
single PowerShell 5.1-compatible helper, preventing test output from appearing
before its stage heading.

## Generate a package

```powershell
.\scripts\generate_story_package.ps1 `
    -ManifestPath .\story_packages\MLAI-025.3.json `
    -OutputRoot C:\Ai Projects\ToolkitTemp
```

## Regression test

```powershell
& .\tests\test_story_package_generator.ps1
```

The generator deliberately owns only installer/validator generation and payload
assembly. Existing `package_story.ps1` remains responsible for generic ZIP
packaging.
