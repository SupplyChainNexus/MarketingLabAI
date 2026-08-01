"""Detect deprecated application API usage."""

from __future__ import annotations

import ast
from pathlib import Path


EXCLUDED_DIRECTORIES = {
    ".git",
    ".venv",
    ".ruff_cache",
    "__pycache__",
    "backups",
}

DEPRECATED_ORCHESTRATOR_KEYWORDS = {
    "intelligence_repository",
    "company_brain_prompt_builder",
    "memory_repository",
    "memory_prompt_builder",
    "memory_limit",
}


def is_excluded(path: Path) -> bool:
    """Return whether a file belongs to an excluded directory."""

    return any(
        part in EXCLUDED_DIRECTORIES
        for part in path.parts
    )


def is_orchestrator_call(node: ast.Call) -> bool:
    """Return whether a call constructs AIOrchestrator."""

    function = node.func

    if isinstance(function, ast.Name):
        return function.id == "AIOrchestrator"

    if isinstance(function, ast.Attribute):
        return function.attr == "AIOrchestrator"

    return False


def main() -> int:
    """Inspect Python files for deprecated API usage."""

    failures: list[str] = []

    for path in Path(".").rglob("*.py"):
        if is_excluded(path):
            continue

        try:
            source = path.read_text(
                encoding="utf-8-sig",
            )
            tree = ast.parse(
                source,
                filename=str(path),
            )
        except (
            OSError,
            UnicodeError,
            SyntaxError,
        ) as error:
            failures.append(
                f"{path}: unable to inspect file: {error}"
            )
            continue

        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue

            if not is_orchestrator_call(node):
                continue

            for keyword in node.keywords:
                if (
                    keyword.arg
                    in DEPRECATED_ORCHESTRATOR_KEYWORDS
                ):
                    failures.append(
                        f"{path}:{node.lineno}: "
                        "AIOrchestrator uses deprecated "
                        f"keyword '{keyword.arg}'."
                    )

    if failures:
        print("Deprecated references found:")

        for failure in failures:
            print(f"  {failure}")

        return 1

    print(
        "No deprecated AIOrchestrator "
        "constructor arguments found."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
