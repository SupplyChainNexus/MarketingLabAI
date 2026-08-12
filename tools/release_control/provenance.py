"""Commit- and executor-bound provenance for deterministic release plans."""

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Mapping

from tools.release_control.config import ControlConfig
from tools.release_control.store import canonical_json, sha256_bytes, sha256_file


def _git(repository_root: Path, *arguments: str) -> str:
    completed = subprocess.run(
        ["git", "-C", str(repository_root), *arguments],
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        shell=False,
    )
    if completed.returncode != 0:
        raise ValueError(
            f"Git provenance inspection failed: {completed.stderr.strip()}"
        )
    return completed.stdout.strip()


def executor_contract(config: ControlConfig) -> dict[str, object]:
    """Hash every tracked release executor input without embedding a mutable target."""

    root = config.repository_root
    paths = sorted((root / "tools" / "release_control").glob("*.py"))
    paths.extend(
        [
            root / "tools" / "release_control_plane.json",
            root / "scripts" / "mlai_release.ps1",
        ]
    )
    files: dict[str, str] = {}
    for path in sorted(paths):
        if not path.is_file():
            raise ValueError(f"Release executor contract file is missing: {path}")
        relative = path.relative_to(root).as_posix()
        files[relative] = sha256_file(path)
    return {
        "files": files,
        "sha256": sha256_bytes(canonical_json({"files": files})),
    }


def build_executor_provenance(config: ControlConfig) -> dict[str, object]:
    """Return provenance only for a clean, commit-addressable repository state."""

    status = _git(
        config.repository_root, "status", "--porcelain", "--untracked-files=all"
    )
    if status:
        raise ValueError(
            "Release plan provenance requires a clean repository; commit or remove drift."
        )
    commit = _git(config.repository_root, "rev-parse", "HEAD")
    if len(commit) != 40:
        raise ValueError("Release plan provenance did not resolve a full Git commit.")
    contract = executor_contract(config)
    cloud_cli = config.payload["cloud_cli"]
    if not isinstance(cloud_cli, Mapping):
        raise ValueError("Cloud CLI adapter configuration is missing.")
    return {
        "control_plane_version": config.payload["control_plane_version"],
        "repository_commit": commit,
        "executor_contract_sha256": contract["sha256"],
        "platform_adapter": cloud_cli["platform_adapter"],
    }


def validate_executor_provenance(value: object) -> dict[str, object]:
    if not isinstance(value, dict):
        raise ValueError(
            "Plan lacks executor provenance and must be formally superseded."
        )
    required = {
        "control_plane_version",
        "repository_commit",
        "executor_contract_sha256",
        "platform_adapter",
    }
    if set(value) != required:
        raise ValueError("Plan executor provenance is incomplete.")
    for name in required:
        selected = value[name]
        if not isinstance(selected, str) or not selected:
            raise ValueError(f"Plan executor provenance is invalid: {name}")
    for name in ("repository_commit", "executor_contract_sha256"):
        selected = str(value[name])
        expected_length = 40 if name == "repository_commit" else 64
        if len(selected) != expected_length or any(
            character not in "0123456789abcdef" for character in selected
        ):
            raise ValueError(f"Plan executor provenance digest is invalid: {name}")
    return dict(value)
