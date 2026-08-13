"""Durable first-service Cloud Run origin reconciliation planning."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Mapping

from deployment.private_synthetic_bootstrap import APPROVED_INGRESS
from deployment.private_synthetic_manifest import (
    FIRST_BOOTSTRAP_ORIGIN,
    SERVICE_ORIGIN_PATTERN,
    ManifestRenderValues,
    render_manifest,
)
from tools.release_control.store import sha256_bytes, sha256_file, write_json_atomic


@dataclass(frozen=True, slots=True)
class OriginReconciliationInputs:
    """Operator-provided values needed to render the reconciled manifest."""

    restricted_browser_api_key: str
    google_oauth_client_id: str



def _is_approved_cloud_run_origin(origin: str) -> bool:
    if SERVICE_ORIGIN_PATTERN.fullmatch(origin):
        return True
    if not origin.startswith("https://"):
        return False
    host = origin.removeprefix("https://")
    return host.endswith(".a.run.app") and "/" not in host and " " not in host


def _required_mapping(value: object, label: str) -> Mapping[str, object]:
    if not isinstance(value, dict):
        raise ValueError(f"{label} must be a JSON object.")
    return value


def _required_string(value: object, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{label} is missing or invalid.")
    return value.strip()


def _outside_repository(repository_root: Path, path: Path) -> bool:
    try:
        path.resolve().relative_to(repository_root.resolve())
    except ValueError:
        return True
    return False


def _validate_startup_origin_inspection(
    inspection: Mapping[str, object],
    *,
    expected_revision: str,
    expected_image: str,
) -> str:
    if inspection.get("result") != "STARTUP_ORIGIN_INSPECTION_COMPLETED":
        raise ValueError("Startup origin inspection evidence is required.")
    if inspection.get("cloud_mutation_performed") is not False:
        raise ValueError("Startup origin inspection must be read-only.")
    if inspection.get("release_state_modified") is not False:
        raise ValueError("Startup origin inspection must not alter release state.")
    if inspection.get("secret_values_accessed") is not False:
        raise ValueError("Startup origin inspection must not access secret values.")
    if inspection.get("latest_revision_matches_expected") is not True:
        raise ValueError("Startup origin inspection is not bound to the revision.")
    if inspection.get("latest_revision_ready") is not True:
        raise ValueError("Latest revision is not ready.")
    if inspection.get("image_matches_expected") is not True:
        raise ValueError("Startup origin inspection image mismatch.")
    if inspection.get("private_ingress") is not True:
        raise ValueError("Service ingress is not private.")
    if inspection.get("no_public_iam") is not True:
        raise ValueError("Public IAM is present.")
    if inspection.get("real_service_url_observed") is not True:
        raise ValueError("Real Cloud Run service URL was not observed.")
    if inspection.get("bootstrap_origin_still_configured") is not True:
        raise ValueError("Origin reconciliation is not required.")
    if inspection.get("startup_can_pass_now") is not False:
        raise ValueError("Startup must not pass before origin reconciliation.")
    if _required_string(
        inspection.get("latest_ready_revision"), "Latest ready revision"
    ) != expected_revision:
        raise ValueError("Latest ready revision does not match expected revision.")
    if _required_string(inspection.get("image"), "Observed image") != expected_image:
        raise ValueError("Observed image does not match expected digest.")
    service_url = _required_string(inspection.get("service_url"), "Service URL")
    if not _is_approved_cloud_run_origin(service_url):
        raise ValueError("Observed service URL is not an approved Cloud Run origin.")
    if inspection.get("observed_public_origin") != FIRST_BOOTSTRAP_ORIGIN:
        raise ValueError("Expected bootstrap origin is not the configured origin.")
    return service_url


def prepare_origin_reconciliation(
    *,
    configuration: Mapping[str, object],
    release: Mapping[str, object],
    revision_created_evidence: Mapping[str, object],
    startup_origin_inspection: Mapping[str, object],
    repository_root: Path,
    output_root: Path,
    inputs: OriginReconciliationInputs,
) -> dict[str, object]:
    """Render the exact real-origin Cloud Run manifest without applying it."""

    if not _outside_repository(repository_root, output_root):
        raise ValueError("Origin reconciliation output must remain outside the repo.")

    if revision_created_evidence.get("result") != "REVISION_CREATED":
        raise ValueError("REVISION_CREATED evidence is required.")
    if revision_created_evidence.get("mutation_count") != 1:
        raise ValueError("REVISION_CREATED must show exactly one prior mutation.")
    if revision_created_evidence.get("requires_origin_reconciliation") is not True:
        raise ValueError("Revision evidence does not require origin reconciliation.")
    if revision_created_evidence.get("secret_value_access") is not False:
        raise ValueError("Revision evidence must not include secret-value access.")

    expected_revision = _required_string(
        revision_created_evidence.get("created_revision"), "Created revision"
    )
    image = _required_string(release.get("image_digest"), "Release image digest")
    real_origin = _validate_startup_origin_inspection(
        startup_origin_inspection,
        expected_revision=expected_revision,
        expected_image=image,
    )

    project = _required_string(configuration.get("project"), "Project")
    region = _required_string(configuration.get("region"), "Region")
    service = _required_string(configuration.get("service"), "Service")
    runtime = _required_string(
        configuration.get("runtime_service_account"), "Runtime service account"
    )
    template_path = repository_root / _required_string(
        configuration.get("manifest_template"), "Manifest template"
    )
    commit = _required_string(release.get("commit"), "Release commit")

    template = template_path.read_text(encoding="utf-8-sig")
    rendered = render_manifest(
        template,
        ManifestRenderValues(
            immutable_image_digest=image,
            private_service_origin=real_origin,
            full_git_commit=commit,
            restricted_browser_api_key=inputs.restricted_browser_api_key,
            google_oauth_client_id=inputs.google_oauth_client_id,
        ),
    )
    manifest_sha256 = sha256_bytes(rendered.encode("utf-8"))
    output_root.mkdir(parents=True, exist_ok=True)
    manifest_path = output_root / f"cloud-run-origin-{manifest_sha256[:16]}.yaml"
    manifest_path.write_text(rendered, encoding="utf-8", newline="\n")

    return {
        "schema_version": 1,
        "result": "ORIGIN_RECONCILIATION_PREPARED",
        "project": project,
        "region": region,
        "service": service,
        "runtime_service_account": runtime,
        "release": dict(release),
        "previous_revision": expected_revision,
        "real_private_service_origin": real_origin,
        "old_private_service_origin": FIRST_BOOTSTRAP_ORIGIN,
        "manifest_path": str(manifest_path.resolve()),
        "manifest_sha256": manifest_sha256,
        "manifest_template_sha256": sha256_file(template_path),
        "command": [
            "gcloud",
            "run",
            "services",
            "replace",
            str(manifest_path),
            f"--region={region}",
            "--platform=managed",
        ],
        "gate": "ORIGIN_RECONCILED",
        "maximum_mutation_count": 1,
        "required_ingress": APPROVED_INGRESS,
        "public_access_authorized": False,
        "secret_value_access_authorized": False,
        "secret_values_read": False,
        "rebuild_authorized": False,
        "admission_authority": False,
        "cloud_cli_executed": False,
        "cloud_mutation_performed": False,
        "deployment_authorized": False,
    }


def write_origin_reconciliation_plan(path: Path, plan: Mapping[str, object]) -> str:
    return write_json_atomic(path, dict(plan))

