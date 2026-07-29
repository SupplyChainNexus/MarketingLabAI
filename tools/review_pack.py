"""Generate a third-party architecture review pack for MarketingLabAI.

Usage:
    python tools/review_pack.py
    python tools/review_pack.py --run-checks
    python tools/review_pack.py --output docs/CUSTOM_REVIEW.md
"""

from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Iterable, Sequence

PROJECT_NAME = "MarketingLabAI"

PROJECT_OVERVIEW = """
MarketingLabAI is being developed as a commercial marketing intelligence
and execution platform.

Its purpose is to transform structured business information, brand identity,
customer understanding, commercial goals and operating constraints into
marketing strategy, campaign plans and brand-aligned content.

The intended product is not merely an AI text generator. Its long-term value
should come from the reusable Company Brain, structured workflows, business
rules, validation, campaign history, strategic insight and controlled
execution.

Artificial-intelligence providers should operate behind a provider-neutral
application layer. Customers should mainly experience MarketingLabAI's
workflow, intelligence, safeguards and results rather than the identity or
technical operation of an underlying language-model provider.
""".strip()

END_GOAL = """
The long-term goal is to develop MarketingLabAI into a secure, maintainable,
multi-organisation commercial platform that can:

1. Build and maintain a structured Company Brain for each organisation.
2. Preserve brand identity, audience knowledge and commercial constraints.
3. Generate campaign strategies and brand-aligned content.
4. Validate claims, tone, authenticity and brand compliance.
5. Keep users responsible for review and publication approval.
6. Record campaign history, versions, approvals and performance.
7. support multiple model providers through a provider-neutral interface.
8. Protect prompts, internal rules, customer data and commercial logic.
9. Support multiple organisations and users with proper data isolation.
10. Deliver value beyond generic content generation.
""".strip()

CURRENT_STATUS = """
Known completed milestones include:

- Python application foundation
- Command-line interface
- Gemini integration
- JSON persistence
- Brand Profile model and service
- Voice analysis components
- Campaign generation components
- Brand onboarding workflow
- Business Intelligence / Company Brain profile
- Integrated Company Brain onboarding
- Input validation
- Automated tests
- Black formatting
- Ruff linting
- Local health checks
- SQLite connection layer
- SQLite repository layer
- JSON-to-SQLite migration
- Migration backup and audit logging
- SQLite integrity checks
- Windows-safe SQLite connection lifecycle
""".strip()

REVIEW_PROMPT = """
You are acting as an independent principal software architect, product
engineer, AI systems reviewer and commercial SaaS adviser.

Review the MarketingLabAI project information and selected source code
contained in this document.

MarketingLabAI is intended to become a commercial marketing intelligence
and execution platform. It should not be treated merely as a thin wrapper
around a language model.

Provide a direct and critical assessment covering:

1. What the application currently does.
2. What has genuinely been built versus what remains conceptual.
3. The quality of the overall architecture.
4. The quality and maintainability of the Python code.
5. The SQLite persistence implementation.
6. The JSON-to-SQLite migration design.
7. Repository and service boundaries.
8. Test quality and missing test categories.
9. Security and privacy weaknesses.
10. Secret-management risks.
11. Risks involving Company Brain and customer business information.
12. Dependence on Gemini or any individual model provider.
13. How to make the intelligence layer provider-neutral.
14. How to prevent model names, prompts and internal AI machinery from
    leaking unnecessarily into the interface or exported material.
15. Where disclosure of automated assistance remains necessary.
16. Whether the product has defensible value beyond generic generation.
17. The most serious technical debt.
18. The most serious commercial-product risks.
19. The correct next development increment.
20. A practical roadmap toward a secure multi-organisation product.

Separate the response into:

- Confirmed strengths
- Confirmed weaknesses
- Risks
- Missing information
- Immediate corrections
- Recommended next increment
- Medium-term roadmap
- Long-term architecture

Do not agree merely for politeness. Challenge assumptions and identify both
overengineering and underengineering. Base conclusions on evidence in this
review pack and label inferences clearly.
""".strip()

DEFAULT_INCLUDED_FILES = (
    "README.md",
    "pyproject.toml",
    "requirements.txt",
    "requirements-dev.txt",
    ".gitignore",
    "app/main.py",
    "app/config.py",
    "app/models.py",
    "app/database/__init__.py",
    "app/database/connection.py",
    "app/database/repositories.py",
    "app/database/migration.py",
    "app/services/brand_service.py",
    "app/services/business_intelligence_service.py",
    "app/services/campaign_service.py",
    "app/workflows/onboarding.py",
    "app/workflows/company_brain_onboarding.py",
    "scripts/quality.ps1",
    "scripts/migrate_to_sqlite.ps1",
)

EXCLUDED_DIRECTORY_NAMES = {
    ".git",
    ".venv",
    "venv",
    "__pycache__",
    ".pytest_cache",
    ".ruff_cache",
    ".mypy_cache",
    "node_modules",
    "outputs",
    "dist",
    "build",
    "htmlcov",
    "coverage",
    "backups",
}

EXCLUDED_FILE_SUFFIXES = {
    ".db",
    ".db-shm",
    ".db-wal",
    ".pyc",
    ".pyo",
    ".log",
    ".tmp",
    ".bak",
}

SENSITIVE_NAME_PATTERNS = (
    re.compile(r"(^|[._-])\.?env($|[._-])", re.IGNORECASE),
    re.compile(r"secret", re.IGNORECASE),
    re.compile(r"credential", re.IGNORECASE),
    re.compile(r"api[._-]?key", re.IGNORECASE),
    re.compile(r"password", re.IGNORECASE),
)

CONTENT_REDACTIONS = (
    (
        re.compile(
            r"(?im)^(\s*(?:api[_-]?key|secret|token|password)" r"\s*[:=]\s*).+$"
        ),
        r"\1[REDACTED]",
    ),
    (
        re.compile(r"AIza[0-9A-Za-z_-]{20,}"),
        "[REDACTED_GOOGLE_KEY]",
    ),
    (
        re.compile(r"sk-[0-9A-Za-z_-]{20,}"),
        "[REDACTED_API_KEY]",
    ),
)


@dataclass(frozen=True)
class CommandResult:
    """Captured result of a non-interactive command."""

    command: tuple[str, ...]
    return_code: int
    output: str

    @property
    def successful(self) -> bool:
        """Return whether the command completed successfully."""
        return self.return_code == 0


@dataclass(frozen=True)
class ProjectFile:
    """A safe project file included in the repository inventory."""

    relative_path: Path
    size_bytes: int


def find_project_root(start: Path | None = None) -> Path:
    """Find the nearest parent containing both app and .git."""
    current = (start or Path.cwd()).resolve()

    for candidate in (current, *current.parents):
        if (candidate / "app").is_dir() and (candidate / ".git").exists():
            return candidate

    raise RuntimeError(
        "MarketingLabAI project root could not be found. "
        "Run this command from inside the repository."
    )


def is_sensitive_name(path: Path) -> bool:
    """Return whether a file name appears likely to contain secrets."""
    name = path.name

    return any(pattern.search(name) for pattern in SENSITIVE_NAME_PATTERNS)


def is_excluded_path(relative_path: Path) -> bool:
    """Return whether a repository path must be excluded."""
    if any(part in EXCLUDED_DIRECTORY_NAMES for part in relative_path.parts):
        return True

    if relative_path.suffix.lower() in EXCLUDED_FILE_SUFFIXES:
        return True

    return is_sensitive_name(relative_path)


def collect_project_files(project_root: Path) -> list[ProjectFile]:
    """Collect a sorted inventory of safe project files."""
    files: list[ProjectFile] = []

    for path in project_root.rglob("*"):
        if not path.is_file():
            continue

        relative_path = path.relative_to(project_root)

        if is_excluded_path(relative_path):
            continue

        try:
            size_bytes = path.stat().st_size
        except OSError:
            continue

        files.append(
            ProjectFile(
                relative_path=relative_path,
                size_bytes=size_bytes,
            )
        )

    return sorted(files, key=lambda item: item.relative_path.as_posix())


def redact_content(content: str) -> str:
    """Redact common secret formats from text."""
    redacted = content

    for pattern, replacement in CONTENT_REDACTIONS:
        redacted = pattern.sub(replacement, redacted)

    return redacted


def read_safe_text(
    path: Path,
    *,
    maximum_characters: int = 30_000,
) -> str:
    """Read a text file with redaction and truncation."""
    try:
        content = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        try:
            content = path.read_text(encoding="utf-8-sig")
        except (OSError, UnicodeError) as exc:
            return f"[Unable to read text file: {exc}]"
    except OSError as exc:
        return f"[Unable to read file: {exc}]"

    content = redact_content(content)

    if len(content) > maximum_characters:
        return content[:maximum_characters] + "\n\n[FILE TRUNCATED FOR REVIEW PACK]"

    return content


def run_command(
    command: Sequence[str],
    *,
    project_root: Path,
    timeout_seconds: int = 120,
) -> CommandResult:
    """Run a command and capture stdout and stderr."""
    try:
        completed = subprocess.run(
            command,
            cwd=project_root,
            check=False,
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
            env=os.environ.copy(),
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return CommandResult(
            command=tuple(command),
            return_code=1,
            output=f"Command could not be completed: {exc}",
        )

    output_parts = []

    if completed.stdout.strip():
        output_parts.append(completed.stdout.strip())

    if completed.stderr.strip():
        output_parts.append(completed.stderr.strip())

    output = "\n".join(output_parts).strip()

    if not output:
        output = "Command completed without producing output."

    return CommandResult(
        command=tuple(command),
        return_code=completed.returncode,
        output=output,
    )


def git_information(project_root: Path) -> dict[str, str]:
    """Collect non-destructive Git information."""
    commands = {
        "Current branch": ("git", "branch", "--show-current"),
        "Current commit": ("git", "rev-parse", "HEAD"),
        "Short commit": ("git", "rev-parse", "--short", "HEAD"),
        "Working tree": ("git", "status", "--short"),
        "Recent history": (
            "git",
            "log",
            "--oneline",
            "--decorate",
            "-20",
        ),
    }

    information: dict[str, str] = {}

    for label, command in commands.items():
        result = run_command(command, project_root=project_root)

        if label == "Working tree" and not result.output.strip():
            information[label] = "Working tree clean."
        else:
            information[label] = result.output

    if not information["Working tree"].strip():
        information["Working tree"] = "Working tree clean."

    return information


def environment_information(project_root: Path) -> dict[str, str]:
    """Collect Python environment information."""
    python_version = run_command(
        (sys.executable, "--version"),
        project_root=project_root,
    )
    pip_version = run_command(
        (sys.executable, "-m", "pip", "--version"),
        project_root=project_root,
    )
    packages = run_command(
        (sys.executable, "-m", "pip", "freeze"),
        project_root=project_root,
    )

    return {
        "Python executable": sys.executable,
        "Python version": python_version.output,
        "Pip version": pip_version.output,
        "Installed packages": packages.output,
    }


def run_project_checks(project_root: Path) -> dict[str, CommandResult]:
    """Run non-destructive quality checks."""
    return {
        "Black": run_command(
            (sys.executable, "-m", "black", "--check", "."),
            project_root=project_root,
        ),
        "Ruff": run_command(
            (sys.executable, "-m", "ruff", "check", "."),
            project_root=project_root,
        ),
        "Tests": run_command(
            (
                sys.executable,
                "-m",
                "unittest",
                "discover",
                "-s",
                "tests",
                "-v",
            ),
            project_root=project_root,
        ),
    }


def language_for_path(path: Path) -> str:
    """Return an appropriate Markdown code-fence language."""
    return {
        ".py": "python",
        ".ps1": "powershell",
        ".toml": "toml",
        ".json": "json",
        ".md": "markdown",
        ".yaml": "yaml",
        ".yml": "yaml",
        ".sql": "sql",
    }.get(path.suffix.lower(), "text")


def select_source_files(
    project_root: Path,
    project_files: Iterable[ProjectFile],
    *,
    maximum_additional_python_files: int = 40,
) -> list[Path]:
    """Choose important files for inclusion in the report."""
    selected: list[Path] = []

    for relative_name in DEFAULT_INCLUDED_FILES:
        relative_path = Path(relative_name)
        full_path = project_root / relative_path

        if full_path.is_file() and not is_excluded_path(relative_path):
            selected.append(relative_path)

    additional_python_files = [
        item.relative_path
        for item in project_files
        if item.relative_path.suffix == ".py"
        and item.relative_path.parts
        and item.relative_path.parts[0] in {"app", "tests"}
        and item.relative_path not in selected
    ]

    selected.extend(additional_python_files[:maximum_additional_python_files])

    return selected


def markdown_section(title: str, content: str) -> str:
    """Create a Markdown section."""
    return f"## {title}\n\n{content.strip()}\n"


def markdown_code_section(
    title: str,
    content: str,
    *,
    language: str = "text",
) -> str:
    """Create a Markdown section containing a code block."""
    safe_content = content.strip() or "[No output]"
    return f"## {title}\n\n" f"```{language}\n" f"{safe_content}\n" f"```\n"


def build_repository_tree(project_files: Iterable[ProjectFile]) -> str:
    """Build a flat, deterministic repository inventory."""
    lines = [
        f"{item.relative_path.as_posix()} ({item.size_bytes} bytes)"
        for item in project_files
    ]

    return "\n".join(lines)


def build_architecture_diagram() -> str:
    """Return a Mermaid representation of the intended architecture."""
    return """
flowchart TD
    User[User] --> CLI[CLI / Future Web Interface]
    CLI --> Services[Application Services]
    Services --> Domain[Domain Models and Business Rules]
    Services --> Repositories[Repository Interfaces]
    Repositories --> SQLite[(SQLite)]
    Services --> Intelligence[Intelligence Provider Interface]
    Intelligence --> Gemini[Gemini Adapter]
    Intelligence --> Future[Future Provider Adapters]
    Services --> Validation[Content and Claim Validation]
    Validation --> Approval[User Review and Approval]
    Approval --> Export[Approved Marketing Output]
""".strip()


def build_data_flow_diagram() -> str:
    """Return a Mermaid representation of the intended data flow."""
    return """
flowchart LR
    Business[Business Information] --> Brain[Company Brain]
    Brand[Brand Profile] --> Brain
    Brain --> Strategy[Campaign Strategy]
    Strategy --> Draft[Content Draft]
    Draft --> Checks[Brand, Claim and Authenticity Checks]
    Checks --> Review[Human Review]
    Review --> Publish[Approved Export or Publication]
""".strip()


def build_report(
    *,
    project_root: Path,
    project_files: Sequence[ProjectFile],
    selected_files: Sequence[Path],
    git_info: dict[str, str],
    environment_info: dict[str, str],
    check_results: dict[str, CommandResult] | None,
) -> str:
    """Build the complete Markdown review pack."""
    generated_at = datetime.now(UTC).astimezone().isoformat(timespec="seconds")
    sections: list[str] = [
        f"# {PROJECT_NAME}: Third-Party Architecture Review Pack\n",
        (
            f"Generated from the local repository on `{generated_at}`.\n\n"
            "Secrets, likely credential files, local databases, backups, "
            "virtual environments, caches and generated outputs were excluded.\n"
        ),
        markdown_section("Executive Project Description", PROJECT_OVERVIEW),
        markdown_section("End Goal", END_GOAL),
        markdown_section("Known Current Status", CURRENT_STATUS),
        markdown_code_section(
            "Repository Identity",
            "\n".join(
                (
                    f"Project root: {project_root}",
                    f"Current branch: {git_info['Current branch']}",
                    f"Current commit: {git_info['Current commit']}",
                    f"Short commit: {git_info['Short commit']}",
                    f"Python executable: {environment_info['Python executable']}",
                    f"Python version: {environment_info['Python version']}",
                    f"Pip version: {environment_info['Pip version']}",
                )
            ),
        ),
        markdown_code_section(
            "Git Working Tree",
            git_info["Working tree"],
        ),
        markdown_code_section(
            "Recent Git History",
            git_info["Recent history"],
        ),
        markdown_code_section(
            "Repository Structure",
            build_repository_tree(project_files),
        ),
        markdown_code_section(
            "Installed Python Packages",
            environment_info["Installed packages"],
        ),
        markdown_code_section(
            "Current Architecture Diagram",
            build_architecture_diagram(),
            language="mermaid",
        ),
        markdown_code_section(
            "Business-to-Output Data Flow",
            build_data_flow_diagram(),
            language="mermaid",
        ),
        markdown_section(
            "Current Persistence Architecture",
            """
The repository currently contains both the original JSON persistence
mechanism and the newer SQLite foundation.

The SQLite foundation is expected to provide:

- Configured connections
- Foreign-key enforcement
- WAL mode
- Transaction handling
- Brand repository
- Business Intelligence repository
- Schema migrations
- Migration audit logging
- JSON backup before migration
- JSON-to-SQLite importing
- Database integrity verification

The expected next increment is to switch active application services from
JSON persistence to SQLite repositories while preserving the public service
interfaces.
""",
        ),
        markdown_section(
            "AI Visibility and Product Positioning",
            """
MarketingLabAI should present itself as a marketing intelligence and
execution platform rather than displaying model-provider branding throughout
the customer experience.

Recommended principles:

- Keep model names and raw prompts out of the normal interface.
- Use product concepts such as Company Brain, Campaign Engine, Brand Voice,
  Strategic Insight and Quality Review.
- Disclose the use of automated language and analysis technology in suitable
  help, account, policy and contractual locations.
- Do not claim human authorship or professional review when none occurred.
- Do not automatically insert AI branding into every exported item.
- Allow disclosure where legally, contractually or platform-required.
- Keep final review and publication approval with the user.
- Prevent generated content from mentioning prompts, model providers or
  system instructions unless specifically requested.
- Use a provider abstraction to avoid dependence on one vendor.
""",
        ),
    ]

    if check_results is None:
        sections.append(
            markdown_section(
                "Quality Checks",
                (
                    "Quality checks were not run while generating this pack.\n\n"
                    "Regenerate it with:\n\n"
                    "`python tools/review_pack.py --run-checks`"
                ),
            )
        )
    else:
        for name, result in check_results.items():
            status = "PASSED" if result.successful else "FAILED"
            sections.append(
                markdown_code_section(
                    f"{name} Result — {status}",
                    result.output,
                )
            )

    sections.append("# Selected Source Files\n")

    for relative_path in selected_files:
        full_path = project_root / relative_path
        content = read_safe_text(full_path)
        language = language_for_path(relative_path)

        sections.append(
            f"## File: `{relative_path.as_posix()}`\n\n"
            f"```{language}\n"
            f"{content.strip()}\n"
            f"```\n"
        )

    sections.extend(
        (
            "# Prompt for the Independent Reviewer\n",
            REVIEW_PROMPT,
            "\n",
        )
    )

    return "\n".join(sections).strip() + "\n"


def write_report(output_path: Path, report: str) -> None:
    """Write the generated report using UTF-8."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(report, encoding="utf-8")


def parse_arguments(argv: Sequence[str] | None = None) -> argparse.Namespace:
    """Parse command-line options."""
    parser = argparse.ArgumentParser(
        description=(
            "Generate a safe third-party architecture review pack for "
            "MarketingLabAI."
        )
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("docs/THIRD_PARTY_REVIEW.md"),
        help="Output Markdown file.",
    )
    parser.add_argument(
        "--run-checks",
        action="store_true",
        help="Run Black, Ruff and automated tests for inclusion in the report.",
    )

    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    """Generate the review pack."""
    arguments = parse_arguments(argv)

    try:
        project_root = find_project_root()
    except RuntimeError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    output_path = arguments.output

    if not output_path.is_absolute():
        output_path = project_root / output_path

    print()
    print("MarketingLabAI - Third-Party Review Pack")
    print("========================================")
    print()
    print(f"Project root: {project_root}")
    print("Collecting repository information...")

    project_files = collect_project_files(project_root)
    selected_files = select_source_files(project_root, project_files)
    git_info = git_information(project_root)
    environment_info = environment_information(project_root)

    check_results = None

    if arguments.run_checks:
        print("Running Black, Ruff and automated tests...")
        check_results = run_project_checks(project_root)

    print("Building report...")

    report = build_report(
        project_root=project_root,
        project_files=project_files,
        selected_files=selected_files,
        git_info=git_info,
        environment_info=environment_info,
        check_results=check_results,
    )

    write_report(output_path, report)

    report_size_kb = output_path.stat().st_size / 1024

    print()
    print("Review pack created successfully:")
    print(output_path)
    print()
    print(f"Repository files catalogued: {len(project_files)}")
    print(f"Source files included: {len(selected_files)}")
    print(f"Report size: {report_size_kb:.2f} KB")
    print()
    print("Before sharing the document:")
    print("1. Open and review it.")
    print("2. Search for key, token, password, secret and credential.")
    print("3. Confirm that it contains no confidential customer information.")
    print()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
