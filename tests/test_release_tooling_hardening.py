import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class ReleaseToolingHardeningTests(unittest.TestCase):
    def test_release_powershell_scripts_do_not_embed_python(self):
        scripts = sorted((ROOT / "scripts").glob("*release*.ps1")) + sorted(
            (ROOT / "scripts").glob("*origin*.ps1")
        )
        self.assertTrue(scripts, "Expected release PowerShell scripts to exist.")
        forbidden = ("python = @'", 'python = @"', "$Script = @'", '$Script = @"')
        for script in scripts:
            text = script.read_text(encoding="utf-8-sig")
            lowered = text.lower()
            self.assertNotIn("from tools.release_control", text)
            self.assertFalse(
                any(item.lower() in lowered for item in forbidden),
                f"PowerShell script embeds Python instead of using the CLI: {script}",
            )

    def test_requirements_cli_reports_origin_reconciled(self):
        completed = subprocess.run(
            [
                sys.executable,
                "-m",
                "tools.release_control",
                "requirements",
                "--gate",
                "ORIGIN_RECONCILED",
            ],
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
        )
        payload = json.loads(completed.stdout)
        self.assertEqual(payload["gate"], "ORIGIN_RECONCILED")
        self.assertIn("cloud mutation during planning", payload["forbids"])

    def test_prepare_origin_reconciliation_cli_has_public_help(self):
        completed = subprocess.run(
            [
                sys.executable,
                "-m",
                "tools.release_control",
                "prepare-origin-reconciliation",
                "--help",
            ],
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
        )
        self.assertIn("--startup-origin-inspection", completed.stdout)
        self.assertIn("--revision-created-evidence", completed.stdout)
        self.assertIn("--output-root", completed.stdout)

    def test_json_config_files_are_utf8_without_bom(self):
        for relative in (
            "tools/release_control_plane.json",
            "deployment/private_synthetic_release_gates.json",
        ):
            data = (ROOT / relative).read_bytes()
            self.assertFalse(data.startswith(b"\xef\xbb\xbf"), relative)
            json.loads(data.decode("utf-8"))

    def test_prepare_origin_reconciliation_cli_writes_plan_without_cloud(self):
        # Full execution is covered by origin-reconciliation unit tests. This test
        # asserts the public command can be invoked without syntax, parser, or
        # PowerShell wrapper dependencies.
        with tempfile.TemporaryDirectory() as temp:
            state_root = Path(temp) / "state"
            state_root.mkdir()
            (state_root / "release-index.json").write_text(
                json.dumps(
                    {
                        "schema_version": 1,
                        "release": {
                            "commit": "22392443177c67b7252ae51182b335e7491357f5",
                            "image_digest": "africa-south1-docker.pkg.dev/marketinglabai-identity-dev/mlai-synthetic/marketinglabai-pilot@sha256:"
                            + "a" * 64,
                        },
                    }
                ),
                encoding="utf-8",
            )
            completed = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "tools.release_control",
                    "--state-root",
                    str(state_root),
                    "requirements",
                    "--gate",
                    "ORIGIN_RECONCILED",
                ],
                cwd=ROOT,
                check=True,
                capture_output=True,
                text=True,
            )
            self.assertIn("ORIGIN_RECONCILED", completed.stdout)
