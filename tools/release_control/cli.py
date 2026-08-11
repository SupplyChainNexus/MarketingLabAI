"""Command-line interface for the unified release control plane."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Sequence

from tools.release_control.config import load_config, validate_repository
from tools.release_control.control_plane import ReleaseControlPlane


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="MarketingLabAI one-plan, one-approval release control plane."
    )
    parser.add_argument("--config", type=Path)
    parser.add_argument("--state-root", type=Path)
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("doctor")
    commands.add_parser("validate-repository")

    adopt = commands.add_parser("adopt")
    adopt.add_argument("--run", type=Path, required=True)
    adopt.add_argument("--build-summary", type=Path, required=True)
    adopt.add_argument("--post-build-assessment", type=Path, required=True)
    adopt.add_argument("--operator", required=True)

    status = commands.add_parser("status")
    status.add_argument("--audit", action="store_true")
    commands.add_parser("plan")

    approve = commands.add_parser("approve")
    approve.add_argument("--plan", required=True)
    approve.add_argument("--operator", required=True)
    approve.add_argument("--authorization-reference", required=True)

    apply = commands.add_parser("apply")
    apply.add_argument("--plan", required=True)
    commands.add_parser("resume")
    commands.add_parser("verify")
    return parser


def _print(value: object) -> None:
    print(json.dumps(value, indent=2, sort_keys=True))


def main(arguments: Sequence[str] | None = None) -> int:
    selected = _parser().parse_args(arguments)
    config = load_config(selected.config) if selected.config else load_config()
    if selected.command in {"doctor", "validate-repository"}:
        _print(validate_repository(config))
        return 0
    state_root = config.state_root(selected.state_root)
    control = ReleaseControlPlane(config, state_root)
    if selected.command == "adopt":
        _print(
            control.adopt(
                run_dir=selected.run,
                build_summary_path=selected.build_summary,
                post_build_assessment_path=selected.post_build_assessment,
                operator=selected.operator,
            )
        )
    elif selected.command == "status":
        _print(control.status(audit=selected.audit))
    elif selected.command == "plan":
        _print(control.plan())
    elif selected.command == "approve":
        _print(
            control.approve(
                plan_digest=selected.plan,
                operator=selected.operator,
                authorization_reference=selected.authorization_reference,
            )
        )
    elif selected.command == "apply":
        _print(control.apply(plan_digest=selected.plan))
    elif selected.command == "resume":
        _print(control.resume())
    elif selected.command == "verify":
        _print(control.verify())
    else:
        raise AssertionError(f"Unhandled command: {selected.command}")
    return 0
