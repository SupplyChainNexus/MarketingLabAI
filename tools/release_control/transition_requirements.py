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


NON_INTERACTIVE_CLOUD_AUTH_REQUIREMENTS: dict[str, object] = {
    "schema_version": 1,
    "gate": "NON_INTERACTIVE_CLOUD_AUTH",
    "purpose": "Prove the pinned release executor service account can be impersonated before any release mutation.",
    "requires": [
        "local operator authenticated as info@supplychainnexus.co.za",
        "release executor service account pinned in tools/release_control_plane.json",
        "Service Account Token Creator grant for the local operator or CI principal",
        "no service-account key-file environment variables",
        "doctor-auth passes before mutation planning or application",
    ],
    "forbids": [
        "service-account key files",
        "browser-user credentials as direct mutation authority",
        "cloud mutation during doctor",
        "release-state modification during doctor",
        "deployment during doctor",
    ],
    "doctor_command": "python -m tools.release_control doctor-auth",
}


def requirements_for_gate(gate: str) -> Mapping[str, object]:
    selected = gate.strip().upper()
    if selected == "ORIGIN_RECONCILED":
        return dict(ORIGIN_RECONCILED_REQUIREMENTS)
    if selected == "NON_INTERACTIVE_CLOUD_AUTH":
        return dict(NON_INTERACTIVE_CLOUD_AUTH_REQUIREMENTS)
    raise ValueError(f"No release-control requirements are registered for {gate}.")
