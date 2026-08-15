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
    report = apply_repair_plan(root, selected.plan.resolve())
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0
