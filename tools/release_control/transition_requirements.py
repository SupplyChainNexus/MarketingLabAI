"""Release transition requirements inspection."""

from __future__ import annotations

from typing import Mapping

ORIGIN_RECONCILED_REQUIREMENTS: dict[str, object] = {
    "schema_version": 1,
    "gate": "ORIGIN_RECONCILED",
    "purpose": "Replace the first-service bootstrap origin with the observed real Cloud Run service URL before startup verification.",
    "requires": [
        "REVISION_CREATED gate passed",
        "revision-created evidence JSON",
        "startup-origin inspection JSON",
        "observed real Cloud Run service URL",
        "restricted browser API key supplied through environment or secure prompt",
        "Google OAuth web client ID supplied through environment or secure prompt",
        "output root outside the repository and under ToolkitTemp",
    ],
    "forbids": [
        "cloud CLI execution during planning",
        "cloud mutation during planning",
        "release-state modification during planning",
        "secret-value access",
        "rebuild",
        "public IAM change",
        "admission authority",
    ],
    "plan_command": "python -m tools.release_control prepare-origin-reconciliation --startup-origin-inspection <path> --revision-created-evidence <path> --output-root <path>",
}


def requirements_for_gate(gate: str) -> Mapping[str, object]:
    selected = gate.strip().upper()
    if selected == "ORIGIN_RECONCILED":
        return dict(ORIGIN_RECONCILED_REQUIREMENTS)
    raise ValueError(f"No release-control requirements are registered for {gate}.")
