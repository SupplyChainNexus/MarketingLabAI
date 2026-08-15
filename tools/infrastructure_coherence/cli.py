"""Command-line interface for repository integrity enforcement."""

from __future__ import annotations

import argparse
import json
from collections.abc import Sequence
from pathlib import Path

from tools.infrastructure_coherence.core import (
    apply_repair_plan,
    check_repository,
    create_repair_plan,
)
from tools.infrastructure_coherence.git_objects import (
    apply_corrective_plan,
    create_corrective_plan,
    export_commit_intake,
    inspect_git_configuration,
)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="python -m tools.infrastructure_coherence")
    parser.add_argument("--root", type=Path, default=Path.cwd())
    commands = parser.add_subparsers(dest="command", required=True)

    check = commands.add_parser("check")
    check.add_argument("--ci", action="store_true")

    plan = commands.add_parser("plan-repair")
    plan.add_argument("--replacement-root", type=Path, required=True)
    plan.add_argument("--output-root", type=Path, required=True)

    apply = commands.add_parser("apply-repair")
    apply.add_argument("--plan", type=Path, required=True)

    export = commands.add_parser("export-intake")
    export.add_argument("--commit", required=True)
    export.add_argument("--path-manifest", type=Path, required=True)
    export.add_argument("--output-root", type=Path, required=True)

    commands.add_parser("doctor-git-config")

    corrective = commands.add_parser("plan-corrective")
    corrective.add_argument("--replacement-root", type=Path, required=True)
    corrective.add_argument("--path-manifest", type=Path, required=True)
    corrective.add_argument("--output-root", type=Path, required=True)

    apply_corrective = commands.add_parser("apply-corrective")
    apply_corrective.add_argument("--plan", type=Path, required=True)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    selected = _parser().parse_args(argv)
    root = selected.root.resolve()
    if selected.command == "check":
        report = check_repository(root)
        print(json.dumps(report, indent=2, sort_keys=True))
        return 0 if report["repository_integrity_valid"] else 1
    if selected.command == "plan-repair":
        report = create_repair_plan(
            root,
            replacement_root=selected.replacement_root.resolve(),
            output_root=selected.output_root.resolve(),
        )
        print(json.dumps(report, indent=2, sort_keys=True))
        return 0
    if selected.command == "apply-repair":
        report = apply_repair_plan(root, selected.plan.resolve())
    elif selected.command == "export-intake":
        report = export_commit_intake(
            root,
            commit=selected.commit,
            path_manifest=selected.path_manifest.resolve(),
            output_root=selected.output_root.resolve(),
        )
    elif selected.command == "doctor-git-config":
        report = inspect_git_configuration(root)
    elif selected.command == "plan-corrective":
        report = create_corrective_plan(
            root,
            replacement_root=selected.replacement_root.resolve(),
            path_manifest=selected.path_manifest.resolve(),
            output_root=selected.output_root.resolve(),
        )
    else:
        report = apply_corrective_plan(root, selected.plan.resolve())
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0
