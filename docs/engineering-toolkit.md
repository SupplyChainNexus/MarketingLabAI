# MarketingLabAI Engineering Toolkit

## Purpose

The toolkit standardises recurring development work so each story follows the
same repeatable process.

## Scripts

### `build_context.ps1`

Builds a topic-specific source and architecture context file.

Examples:

```powershell
.\scripts\build_context.ps1 prompt -StoryId MLAI-024
.\scripts\build_context.ps1 customer -StoryId MLAI-023
.\scripts\build_context.ps1 product -StoryId MLAI-025
```

Output is written to:

```text
docs\build_context\
```

### `create_story.ps1`

Creates a structured backlog story.

```powershell
.\scripts\create_story.ps1 MLAI-024 "Marketing Brief and Prompt Composition"
```

### `validate_story.ps1`

Runs formatting, focused tests, optional full tests, `git diff --check`, and
Git status.

```powershell
.\scripts\validate_story.ps1 `
    -TestModules @(
        "tests.test_ai_context_assembler",
        "tests.test_customer_context_provider"
    )

.\scripts\validate_story.ps1 -FullSuite
```

### `story_status.ps1`

Shows branch, Git state, recent commits, and optionally one story.

```powershell
.\scripts\story_status.ps1 MLAI-024
```

### `engineering_review.ps1`

Creates a review report from the current working tree and story record.

```powershell
.\scripts\engineering_review.ps1 MLAI-024
```

### `package_story.ps1`

Packages an explicit list of files while preserving repository paths.

```powershell
.\scripts\package_story.ps1 `
    MLAI-024 `
    -Paths @(
        ".\app\marketing_brief",
        ".\tests\test_marketing_brief.py",
        ".\backlog\MLAI-024.md"
    )
```

### `clean_workspace.ps1`

Previews known temporary files:

```powershell
.\scripts\clean_workspace.ps1
```

Deletes them only when explicitly requested:

```powershell
.\scripts\clean_workspace.ps1 -Apply
```

## Standard Workflow

1. Create or update the backlog story.
2. Generate the relevant build context.
3. Review and lock the architecture.
4. Implement one controlled increment.
5. Run focused validation.
6. Run affected regression tests.
7. Produce an engineering review.
8. Clean temporary artifacts.
9. Commit.
