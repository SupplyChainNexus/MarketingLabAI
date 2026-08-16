import json
import subprocess
import tempfile
import unittest
import zipfile
from pathlib import Path

from tools.infrastructure_coherence.core import (
    _content_sha256_bytes,
    apply_repair_plan,
    check_repository,
    create_repair_plan,
    scan_repository,
)
from tools.infrastructure_coherence.git_objects import (
    apply_corrective_plan,
    create_corrective_plan,
    export_commit_intake,
    inspect_git_configuration,
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


def _commit(root: Path, *relative_paths: str) -> str:
    _track(root, *relative_paths)
    subprocess.run(
        [
            "git",
            "-c",
            "user.name=Infrastructure Tests",
            "-c",
            "user.email=infrastructure-tests@example.invalid",
            "commit",
            "-qm",
            "fixture",
        ],
        cwd=root,
        check=True,
    )
    return subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=root,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


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

    def test_raw_git_object_export_ignores_worktree_eol_materialization(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            root = base / "repo"
            root.mkdir()
            (root / ".gitattributes").write_bytes(b"*.ps1 text eol=crlf\n")
            script = root / "sample.ps1"
            script.write_bytes(b"Write-Host 'canonical'\n")
            manifest = root / "paths.json"
            manifest.write_text(
                json.dumps({"schema_version": 1, "paths": ["sample.ps1"]}) + "\n",
                encoding="utf-8",
            )
            commit = _commit(root, ".gitattributes", "sample.ps1", "paths.json")
            script.write_bytes(b"Write-Host 'materialized'\r\n")
            report = export_commit_intake(
                root,
                commit=commit,
                path_manifest=manifest,
                output_root=base / "MLAI-031.18C-intake",
            )
            self.assertFalse(report["working_tree_bytes_used"])
            expected_zip = base / "MLAI-031.18C-intake.zip"
            reported_zip = Path(report["intake_zip"])
            self.assertEqual("MLAI-031.18C-intake.zip", reported_zip.name)
            self.assertTrue(reported_zip.samefile(expected_zip))
            self.assertFalse((base / "MLAI-031.zip").exists())
            self.assertEqual(
                b"Write-Host 'canonical'\n",
                (base / "MLAI-031.18C-intake/source/sample.ps1").read_bytes(),
            )
            with zipfile.ZipFile(report["intake_zip"]) as archive:
                self.assertEqual(
                    b"Write-Host 'canonical'\n", archive.read("source/sample.ps1")
                )

    def test_export_refuses_existing_zip_without_changing_it(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            root = base / "repo"
            root.mkdir()
            (root / "tracked.md").write_bytes(b"tracked\n")
            commit = _commit(root, "tracked.md")
            manifest = base / "paths.json"
            manifest.write_text(
                json.dumps({"schema_version": 1, "paths": ["tracked.md"]}),
                encoding="utf-8",
            )
            output_root = base / "MLAI-031.18C-intake"
            zip_path = base / "MLAI-031.18C-intake.zip"
            zip_path.write_bytes(b"preserve-existing-artifact")

            with self.assertRaisesRegex(ValueError, "ZIP destination already exists"):
                export_commit_intake(
                    root,
                    commit=commit,
                    path_manifest=manifest,
                    output_root=output_root,
                )

            self.assertEqual(b"preserve-existing-artifact", zip_path.read_bytes())
            self.assertFalse(output_root.exists())

    def test_export_rejects_ambiguous_zip_named_output_root(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            root = base / "repo"
            root.mkdir()
            (root / "tracked.md").write_bytes(b"tracked\n")
            commit = _commit(root, "tracked.md")
            manifest = base / "paths.json"
            manifest.write_text(
                json.dumps({"schema_version": 1, "paths": ["tracked.md"]}),
                encoding="utf-8",
            )

            with self.assertRaisesRegex(ValueError, "ambiguous"):
                export_commit_intake(
                    root,
                    commit=commit,
                    path_manifest=manifest,
                    output_root=base / "already-a-zip.zip",
                )

    def test_export_rejects_source_output_overlap_in_both_directions(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            root = base / "repo"
            root.mkdir()
            (root / "tracked.md").write_bytes(b"tracked\n")
            commit = _commit(root, "tracked.md")
            manifest = base / "paths.json"
            manifest.write_text(
                json.dumps({"schema_version": 1, "paths": ["tracked.md"]}),
                encoding="utf-8",
            )

            for output_root in (root / "evidence", base):
                with self.subTest(output_root=output_root):
                    with self.assertRaisesRegex(ValueError, "overlaps"):
                        export_commit_intake(
                            root,
                            commit=commit,
                            path_manifest=manifest,
                            output_root=output_root,
                        )

    def test_export_requires_exact_unique_tracked_paths(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            root = base / "repo"
            root.mkdir()
            (root / "tracked.md").write_bytes(b"tracked\n")
            commit = _commit(root, "tracked.md")
            manifest = base / "paths.json"
            manifest.write_text(
                json.dumps(
                    {"schema_version": 1, "paths": ["tracked.md", "tracked.md"]}
                ),
                encoding="utf-8",
            )
            with self.assertRaisesRegex(ValueError, "duplicate"):
                export_commit_intake(
                    root,
                    commit=commit,
                    path_manifest=manifest,
                    output_root=base / "intake",
                )

    def test_git_configuration_doctor_is_read_only(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            subprocess.run(["git", "init", "-q"], cwd=root, check=True)
            subprocess.run(
                ["git", "config", "--local", "core.autocrlf", "true"],
                cwd=root,
                check=True,
            )
            config = root / ".git/config"
            before = config.read_bytes()
            report = inspect_git_configuration(root)
            self.assertFalse(report["git_configuration_compatible"])
            self.assertEqual(before, config.read_bytes())
            self.assertFalse(report["configuration_modified"])

    def test_non_baseline_corrective_plan_is_hash_bound(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            root = base / "repo"
            replacement_root = base / "replacements"
            root.mkdir()
            replacement_root.mkdir()
            (root / "target.md").write_bytes(b"before\n")
            commit = _commit(root, "target.md")
            self.assertTrue(commit)
            (replacement_root / "target.md").write_bytes(b"after\n")
            manifest = base / "paths.json"
            manifest.write_text(
                json.dumps({"schema_version": 1, "paths": ["target.md"]}) + "\n",
                encoding="utf-8",
            )
            prepared = create_corrective_plan(
                root,
                replacement_root=replacement_root,
                path_manifest=manifest,
                output_root=base / "plans",
            )
            (root / "target.md").write_bytes(b"changed-after-planning\n")
            with self.assertRaisesRegex(ValueError, "Target bytes changed"):
                apply_corrective_plan(root, Path(prepared["plan_path"]))

    def test_canonical_security_intake_manifest_is_explicit(self) -> None:
        value = json.loads(
            (
                ROOT
                / "governance/manifests/MLAI-031.18B-security-governance-intake.paths.json"
            ).read_text(encoding="utf-8")
        )
        self.assertEqual(1, value["schema_version"])
        self.assertEqual(180, len(value["paths"]))
        self.assertEqual(len(value["paths"]), len(set(value["paths"])))


if __name__ == "__main__":
    unittest.main()
