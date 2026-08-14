"""Command-line interface for the unified release control plane."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Sequence

from tools.release_control.auth_execution import (
    CloudAuthExecutionBoundary,
    CloudAuthExecutionConfig,
)
from tools.release_control.config import load_config, validate_repository
from tools.release_control.control_plane import ReleaseControlPlane
from tools.release_control.executor_identity_cli import (
    inspect_executor_identity_from_cli,
    prepare_executor_identity_bootstrap_from_cli,
)
from tools.release_control.origin_reconciliation_cli import (
    prepare_origin_reconciliation_from_cli,
)
from tools.release_control.transition_requirements import requirements_for_gate


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="MarketingLabAI one-plan, one-approval release control plane."
    )
    parser.add_argument("--config", type=Path)
    parser.add_argument("--state-root", type=Path)
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("doctor")
    commands.add_parser("doctor-cloud")
    commands.add_parser("doctor-auth")
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
    supersede = commands.add_parser("supersede-operation")
    supersede.add_argument("--plan", required=True)
    supersede.add_argument("--operator", required=True)
    supersede.add_argument("--reason", required=True)
    supersede.add_argument("--authorization-reference", required=True)
    prepare_revision = commands.add_parser("prepare-revision")
    prepare_revision.add_argument("--output-root", type=Path, required=True)
    prepare_revision.add_argument("--origin", required=True)
    prepare_revision.add_argument("--browser-api-key", required=True)
    prepare_revision.add_argument("--oauth-client-id", required=True)
    inspect_executor = commands.add_parser("inspect-executor-identity")
    inspect_executor.add_argument("--output-root", type=Path, required=True)

    prepare_executor = commands.add_parser("prepare-executor-identity-bootstrap")
    prepare_executor.add_argument("--inspection", type=Path, required=True)
    prepare_executor.add_argument("--output-root", type=Path, required=True)
    commands.add_parser("resume")
    requirements = commands.add_parser("requirements")
    requirements.add_argument("--gate", required=True)

    prepare_origin = commands.add_parser("prepare-origin-reconciliation")
    prepare_origin.add_argument("--startup-origin-inspection", type=Path, required=True)
    prepare_origin.add_argument("--revision-created-evidence", type=Path, required=True)
    prepare_origin.add_argument("--output-root", type=Path, required=True)
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
    if selected.command == "doctor-auth":
        _print(
            CloudAuthExecutionBoundary(
                CloudAuthExecutionConfig.from_payload(config.payload)
            ).doctor()
        )
        return 0
    if selected.command == "requirements":
        _print(requirements_for_gate(selected.gate))
        return 0
    if selected.command == "inspect-executor-identity":
        _print(
            inspect_executor_identity_from_cli(
                config=config, output_root=selected.output_root
            )
        )
        return 0
    if selected.command == "prepare-executor-identity-bootstrap":
        _print(
            prepare_executor_identity_bootstrap_from_cli(
                config=config,
                inspection_path=selected.inspection,
                output_root=selected.output_root,
            )
        )
        return 0
    state_root = config.state_root(selected.state_root)
    control = ReleaseControlPlane(config, state_root)
    if selected.command == "doctor-cloud":
        _print(control.doctor_cloud())
    elif selected.command == "adopt":
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
    elif selected.command == "supersede-operation":
        _print(
            control.supersede_operation(
                plan_digest=selected.plan,
                operator=selected.operator,
                reason=selected.reason,
                authorization_reference=selected.authorization_reference,
            )
        )
    elif selected.command == "prepare-revision":
        _print(
            control.prepare_revision(
                output_root=selected.output_root,
                origin=selected.origin,
                browser_api_key=selected.browser_api_key,
                oauth_client_id=selected.oauth_client_id,
            )
        )
    elif selected.command == "resume":
        _print(control.resume())
    elif selected.command == "prepare-origin-reconciliation":
        _print(
            prepare_origin_reconciliation_from_cli(
                config=config,
                state_root=state_root,
                startup_origin_inspection=selected.startup_origin_inspection,
                revision_created_evidence=selected.revision_created_evidence,
                output_root=selected.output_root,
            )
        )
    elif selected.command == "verify":
        _print(control.verify())
    else:
        raise AssertionError(f"Unhandled command: {selected.command}")
    return 0
