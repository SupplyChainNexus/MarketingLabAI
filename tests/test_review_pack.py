"""Tests for the MarketingLabAI review-pack generator."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from tools.review_pack import (
    ProjectFile,
    build_report,
    collect_project_files,
    is_excluded_path,
    read_safe_text,
    redact_content,
    select_source_files,
)


class ExclusionTests(unittest.TestCase):
    """Verify that private and generated files are excluded."""

    def test_excludes_virtual_environment(self) -> None:
        self.assertTrue(is_excluded_path(Path(".venv/Lib/site-packages/example.py")))

    def test_excludes_sqlite_database(self) -> None:
        self.assertTrue(is_excluded_path(Path("database/marketinglabai.db")))

    def test_excludes_environment_file(self) -> None:
        self.assertTrue(is_excluded_path(Path(".env")))

    def test_allows_normal_python_source(self) -> None:
        self.assertFalse(is_excluded_path(Path("app/services/brand_service.py")))


class RedactionTests(unittest.TestCase):
    """Verify that common secret formats are removed."""

    def test_redacts_named_api_key(self) -> None:
        content = "API_KEY=super-secret-value"

        redacted = redact_content(content)

        self.assertNotIn("super-secret-value", redacted)
        self.assertIn("[REDACTED]", redacted)

    def test_redacts_google_key_pattern(self) -> None:
        content = "AIza1234567890abcdefghijklmnop"

        redacted = redact_content(content)

        self.assertEqual(redacted, "[REDACTED_GOOGLE_KEY]")


class FileCollectionTests(unittest.TestCase):
    """Verify safe repository file collection."""

    def test_collection_skips_database_and_cache_files(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            (root / "app").mkdir()
            (root / "database").mkdir()
            (root / "__pycache__").mkdir()

            (root / "app" / "main.py").write_text(
                "print('hello')",
                encoding="utf-8",
            )
            (root / "database" / "app.db").write_bytes(b"database")
            (root / "__pycache__" / "main.pyc").write_bytes(b"cache")

            files = collect_project_files(root)
            paths = {item.relative_path.as_posix() for item in files}

            self.assertIn("app/main.py", paths)
            self.assertNotIn("database/app.db", paths)
            self.assertNotIn("__pycache__/main.pyc", paths)

    def test_safe_reader_truncates_large_file(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            path = Path(temporary_directory) / "large.txt"
            path.write_text("x" * 100, encoding="utf-8")

            content = read_safe_text(path, maximum_characters=10)

            self.assertTrue(content.startswith("x" * 10))
            self.assertIn("FILE TRUNCATED", content)


class ReportGenerationTests(unittest.TestCase):
    """Verify deterministic review-pack generation."""

    def test_selects_existing_preferred_and_python_files(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            (root / "app").mkdir()
            (root / "tests").mkdir()

            (root / "README.md").write_text("# Example", encoding="utf-8")
            (root / "app" / "main.py").write_text("", encoding="utf-8")
            (root / "tests" / "test_example.py").write_text(
                "",
                encoding="utf-8",
            )

            files = [
                ProjectFile(Path("README.md"), 9),
                ProjectFile(Path("app/main.py"), 0),
                ProjectFile(Path("tests/test_example.py"), 0),
            ]

            selected = select_source_files(root, files)

            self.assertIn(Path("README.md"), selected)
            self.assertIn(Path("app/main.py"), selected)
            self.assertIn(Path("tests/test_example.py"), selected)

    def test_report_contains_core_sections(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)

            report = build_report(
                project_root=root,
                project_files=[],
                selected_files=[],
                git_info={
                    "Current branch": "feature/example",
                    "Current commit": "abc123",
                    "Short commit": "abc123",
                    "Working tree": "Working tree clean.",
                    "Recent history": "abc123 Example commit",
                },
                environment_info={
                    "Python executable": "python",
                    "Python version": "Python 3",
                    "Pip version": "pip",
                    "Installed packages": "example==1.0",
                },
                check_results=None,
            )

            self.assertIn("Executive Project Description", report)
            self.assertIn("End Goal", report)
            self.assertIn("Repository Structure", report)
            self.assertIn("Prompt for the Independent Reviewer", report)


if __name__ == "__main__":
    unittest.main()
