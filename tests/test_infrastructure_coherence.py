import json
import subprocess
import tempfile
import unittest
from pathlib import Path

from tools.infrastructure_coherence.core import (
    _content_sha256_bytes,
    apply_repair_plan,
    check_repository,
    create_repair_plan,
    scan_repository,
)

ROOT = Path(__file__).resolve().parents[1]


def _track(root: Path, *relative_paths: str) -> None:
    subprocess.run(["git", "init", "-q"], cwd=root, check=True)
    subprocess.run(
        ["git", "add", "--", *relative_paths],
        cwd=root,
        check=True,
        capture_output=True,
    )


class InfrastructureCoherenceTests(unittest.TestCase):
    def test_repository_contract_passes_with_exact_legacy_baseline(self) -> None:
        report = check_repository(ROOT)
        self.assertTrue(report["repository_integrity_valid"])
        self.assertEqual([], report["blocking_findings"])

    def test_mojibake_is_detected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            path = root / "broken.md"
            path.write_text("Broken: \u00c3\u00a2\n", encoding="utf-8")
            _track(root, "broken.md")
            findings = scan_repository(root)
        self.assertIn("MOJIBAKE", {item["code"] for item in findings})

    def test_checkout_line_endings_are_not_repository_findings(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "uniform.py").write_bytes(b"first\r\nsecond\r\n")
            (root / "mixed.py").write_bytes(b"first\r\nsecond\n")
            _track(root, "uniform.py", "mixed.py")
            findings = scan_repository(root)
        self.assertNotIn("MIXED_LINE_ENDINGS", {item["code"] for item in findings})

    def test_ignored_local_files_are_outside_repository_integrity(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / ".gitignore").write_bytes(b"local/\n")
            (root / "tracked.md").write_bytes(b"tracked\n")
            local = root / "local" / "broken.md"
            local.parent.mkdir()
            local.write_bytes(b"\xef\xbb\xbfBroken: \xc3\x83\xc2\xa2")
            _track(root, ".gitignore", "tracked.md")
            findings = scan_repository(root)
        self.assertNotIn("local/broken.md", {item["path"] for item in findings})

    def test_declared_package_target_is_scanned_before_commit(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "tools").mkdir()
            policy = {
                "required_repository_paths": ["planned.md"],
                "schema_version": 1,
            }
            policy_path = root / "tools" / "infrastructure_coherence_policy.json"
            policy_path.write_bytes((json.dumps(policy) + "\n").encode("utf-8"))
            (root / "planned.md").write_bytes(b"\xef\xbb\xbfplanned\n")
            _track(root, "tools/infrastructure_coherence_policy.json")
            findings = scan_repository(root)
        self.assertIn(
            ("planned.md", "UTF8_BOM"),
            {(item["path"], item["code"]) for item in findings},
        )

    def test_changed_acknowledged_bytes_block(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "tools").mkdir()
            (root / "governance").mkdir()
            broken = root / "legacy.md"
            broken.write_bytes(b"\xef\xbb\xbflegacy\n")
            digest = _content_sha256_bytes(broken.read_bytes())
            baseline = {
                "findings": [
                    {"code": "UTF8_BOM", "path": "legacy.md", "sha256": digest}
                ],
                "schema_version": 1,
            }
            baseline_path = root / "governance" / "baseline.json"
            baseline_path.write_bytes((json.dumps(baseline) + "\n").encode("utf-8"))
            policy = {"legacy_baseline": "governance/baseline.json"}
            (root / "tools" / "infrastructure_coherence_policy.json").write_bytes(
                (json.dumps(policy) + "\n").encode("utf-8")
            )
            _track(
                root,
                "legacy.md",
                "governance/baseline.json",
                "tools/infrastructure_coherence_policy.json",
            )
            self.assertTrue(check_repository(root)["repository_integrity_valid"])
            broken.write_bytes(b"\xef\xbb\xbfchanged\n")
            self.assertFalse(check_repository(root)["repository_integrity_valid"])

    def test_repair_is_plan_and_hash_bound(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            root = base / "repo"
            replacement_root = base / "replacements"
            output_root = base / "plans"
            (root / "tools").mkdir(parents=True)
            (root / "governance").mkdir()
            (replacement_root).mkdir()
            target = root / "legacy.md"
            target.write_bytes(b"\xef\xbb\xbflegacy\n")
            digest = _content_sha256_bytes(target.read_bytes())
            baseline = {
                "findings": [
                    {"code": "UTF8_BOM", "path": "legacy.md", "sha256": digest}
                ],
                "schema_version": 1,
            }
            (root / "governance" / "baseline.json").write_bytes(
                (json.dumps(baseline) + "\n").encode("utf-8")
            )
            (root / "tools" / "infrastructure_coherence_policy.json").write_bytes(
                (
                    json.dumps({"legacy_baseline": "governance/baseline.json"}) + "\n"
                ).encode("utf-8")
            )
            _track(
                root,
                "legacy.md",
                "governance/baseline.json",
                "tools/infrastructure_coherence_policy.json",
            )
            (replacement_root / "legacy.md").write_bytes(b"legacy\n")
            prepared = create_repair_plan(
                root, replacement_root=replacement_root, output_root=output_root
            )
            applied = apply_repair_plan(root, Path(prepared["plan_path"]))
            self.assertEqual("REPOSITORY_REPAIR_PLAN_APPLIED", applied["result"])
            self.assertEqual(b"legacy\n", target.read_bytes())

    def test_hygiene_launcher_has_no_rewrite_primitives(self) -> None:
        text = (ROOT / "scripts" / "repair_local_hygiene.ps1").read_text(
            encoding="utf-8"
        )
        for forbidden in (
            "Get-Content",
            "WriteAllText",
            "ruff check . --fix",
            "black .",
        ):
            self.assertNotIn(forbidden, text)


if __name__ == "__main__":
    unittest.main()
