"""CLI adapter for release executor identity discovery and planning."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path
from typing import Mapping

from tools.release_control.config import ControlConfig
from tools.release_control.executor_identity import (
    ExecutorIdentityConfig,
    ReadOnlyExecutorIdentityInspector,
    prepare_identity_bootstrap_plan_from_file,
    write_identity_bootstrap_plan,
    write_inspection,
)


def _artifact_root(config: ControlConfig) -> Path:
    configured = os.environ.get("MLAI_TOOLKIT_ROOT", "").strip()
    if configured:
        return Path(configured).expanduser().resolve()
    tooling = config.payload.get("release_tooling")
    if not isinstance(tooling, Mapping):
        raise ValueError("Release tooling artifact-root configuration is missing.")
    selected = str(tooling.get("artifact_root", "")).strip()
    if not selected:
        raise ValueError("Release tooling artifact root is missing.")
    return Path(selected).expanduser().resolve()


def _validate_output_root(config: ControlConfig, output_root: Path) -> Path:
    selected = output_root.expanduser().resolve()
    repository = config.repository_root.resolve()
    if selected == repository or repository in selected.parents:
        raise ValueError(
            "Executor identity evidence may not be written in the repository."
        )
    allowed = _artifact_root(config)
    if selected != allowed and allowed not in selected.parents:
        raise ValueError("Executor identity evidence must remain under ToolkitTemp.")
    selected.mkdir(parents=True, exist_ok=True)
    return selected


def inspect_executor_identity_from_cli(
    *,
    config: ControlConfig,
    output_root: Path,
) -> dict[str, object]:
    selected = _validate_output_root(config, output_root)
    inspector = ReadOnlyExecutorIdentityInspector(
        ExecutorIdentityConfig.from_payload(config.payload)
    )
    inspection = inspector.inspect()
    path = selected / "release-executor-identity-inspection.json"
    digest = write_inspection(path, inspection)
    return {
        **inspection,
        "inspection_path": str(path),
        "inspection_file_sha256": digest,
    }


def prepare_executor_identity_bootstrap_from_cli(
    *,
    config: ControlConfig,
    inspection_path: Path,
    output_root: Path,
) -> dict[str, object]:
    selected = _validate_output_root(config, output_root)
    completed = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=config.repository_root,
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if completed.returncode != 0:
        raise ValueError("Could not bind the executor bootstrap plan to Git HEAD.")
    repository_commit = completed.stdout.strip().casefold()
    plan = prepare_identity_bootstrap_plan_from_file(
        inspection_path,
        repository_commit=repository_commit,
    )
    path = selected / f"{plan['plan_digest']}.json"
    digest = write_identity_bootstrap_plan(path, plan)
    return {
        **plan,
        "plan_path": str(path),
        "plan_file_sha256": digest,
    }
