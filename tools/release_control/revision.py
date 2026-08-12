"""Deterministic Cloud Run revision preparation without cloud mutation."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping

from deployment.private_synthetic_bootstrap import APPROVED_INGRESS
from deployment.private_synthetic_manifest import (
    ManifestRenderValues,
    render_manifest,
)
from tools.release_control.store import sha256_bytes, sha256_file, write_json_atomic

ORIGIN_PATTERN = re.compile(r"https://[a-z0-9-]+-[0-9]+\.africa-south1\.run\.app")


@dataclass(frozen=True, slots=True)
class RevisionInputs:
    private_service_origin: str
    restricted_browser_api_key: str
    google_oauth_client_id: str


def _outside_repository(repository_root: Path, path: Path) -> bool:
    try:
        path.resolve().relative_to(repository_root.resolve())
    except ValueError:
        return True
    return False


def _validated_mapping(value: object, label: str) -> Mapping[str, object]:
    if not isinstance(value, dict):
        raise ValueError(f"Revision preparation expected an object: {label}")
    return value


def prepare_revision_creation(
    *,
    configuration: Mapping[str, object],
    release: Mapping[str, object],
    cloud_preflight_evidence: Mapping[str, object],
    repository_root: Path,
    output_root: Path,
    inputs: RevisionInputs,
) -> dict[str, object]:
    """Render and hash the exact private revision manifest without applying it."""

    if not _outside_repository(repository_root, output_root):
        raise ValueError(
            "Revision preparation output must remain outside the repository."
        )
    if not ORIGIN_PATTERN.fullmatch(inputs.private_service_origin):
        raise ValueError("Private service origin must be the Cloud Run HTTPS URL.")
    if cloud_preflight_evidence.get("result") != "CLOUD_PREFLIGHT_PASSED":
        raise ValueError("CLOUD_PREFLIGHT_PASSED evidence is required.")
    if cloud_preflight_evidence.get("cloud_mutation_performed") is not False:
        raise ValueError("Cloud preflight evidence cannot include cloud mutation.")

    cloud_run = _validated_mapping(
        cloud_preflight_evidence.get("cloud_run"), "cloud preflight Cloud Run state"
    )
    revision_plan = _validated_mapping(
        cloud_run.get("revision_creation_plan"), "cloud preflight revision plan"
    )
    if revision_plan.get("deployable") is not True:
        raise ValueError("Cloud preflight did not produce a deployable revision plan.")
    if revision_plan.get("maximum_mutation_count") != 1:
        raise ValueError("Revision creation must be exactly one mutation.")
    if revision_plan.get("required_ingress") != APPROVED_INGRESS:
        raise ValueError("Revision creation requires private ingress.")

    project = str(configuration["project"])
    region = str(configuration["region"])
    service = str(configuration["service"])
    runtime = str(configuration["runtime_service_account"])
    template_path = repository_root / str(configuration["manifest_template"])
    image = str(release["image_digest"])
    commit = str(release["commit"])
    template = template_path.read_text(encoding="utf-8-sig")
    rendered = render_manifest(
        template,
        ManifestRenderValues(
            immutable_image_digest=image,
            private_service_origin=inputs.private_service_origin,
            full_git_commit=commit,
            restricted_browser_api_key=inputs.restricted_browser_api_key,
            google_oauth_client_id=inputs.google_oauth_client_id,
        ),
    )
    manifest_sha256 = sha256_bytes(rendered.encode("utf-8"))
    output_root.mkdir(parents=True, exist_ok=True)
    manifest_path = output_root / f"cloud-run-revision-{manifest_sha256[:16]}.yaml"
    manifest_path.write_text(rendered, encoding="utf-8", newline="\n")

    command = [
        "gcloud",
        "run",
        "services",
        "replace",
        str(manifest_path),
        f"--region={region}",
        "--platform=managed",
    ]
    return {
        "schema_version": 1,
        "result": "REVISION_CREATION_PREPARED",
        "project": project,
        "region": region,
        "service": service,
        "runtime_service_account": runtime,
        "release": dict(release),
        "cloud_preflight_evidence_sha256": (
            sha256_file(Path(str(cloud_preflight_evidence["_source_path"])))
            if "_source_path" in cloud_preflight_evidence
            else ""
        ),
        "manifest_path": str(manifest_path.resolve()),
        "manifest_sha256": manifest_sha256,
        "manifest_template_sha256": sha256_file(template_path),
        "command": command,
        "expected_creation_mode": revision_plan["creation_mode"],
        "expected_new_revision_traffic_percent": revision_plan[
            "expected_new_revision_traffic_percent"
        ],
        "maximum_mutation_count": 1,
        "traffic_routing_authorized": False,
        "public_access_authorized": False,
        "secret_values_read": False,
        "secret_value_access_authorized": False,
        "cloud_cli_executed": False,
        "cloud_mutation_performed": False,
        "deployment_authorized": False,
        "admission_authority": False,
    }


def write_revision_plan(path: Path, plan: Mapping[str, object]) -> str:
    return write_json_atomic(path, dict(plan))
