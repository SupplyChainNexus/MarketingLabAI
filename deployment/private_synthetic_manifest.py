"""Render and validate the canonical private synthetic Cloud Run manifest."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping, Sequence

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_TEMPLATE = ROOT / "deployment" / "cloud-run.private-synthetic.yaml.template"

EXPECTED_PLACEHOLDERS = frozenset(
    {
        "FULL_GIT_COMMIT",
        "GOOGLE_OAUTH_CLIENT_ID",
        "IMMUTABLE_IMAGE_DIGEST",
        "PRIVATE_SERVICE_ORIGIN",
        "RESTRICTED_BROWSER_API_KEY",
    }
)

EXPECTED_ENVIRONMENT_NAMES = frozenset(
    {
        "GEMINI_API_KEY",
        "GEMINI_MODEL",
        "MLAI_ALLOW_REAL_CUSTOMER_DATA",
        "MLAI_BACKUP_DIRECTORY",
        "MLAI_DATABASE_PATH",
        "MLAI_DATABASE_URL",
        "MLAI_DEPLOYMENT_COMMIT",
        "MLAI_ENVIRONMENT",
        "MLAI_FOUNDER_INVITATION_HASHES_JSON",
        "MLAI_GOOGLE_AUTH_DOMAIN",
        "MLAI_GOOGLE_CLOUD_PROJECT_ID",
        "MLAI_GOOGLE_MAX_AUTH_AGE_SECONDS",
        "MLAI_GOOGLE_OAUTH_CLIENT_ID",
        "MLAI_GOOGLE_WEB_API_KEY",
        "MLAI_IDENTITY_ADAPTER_FACTORY",
        "MLAI_IDENTITY_PROVIDER",
        "MLAI_PERSISTENCE_BACKEND",
        "MLAI_PROVIDER_REGISTRY_FACTORY",
        "MLAI_PUBLIC_ORIGIN",
        "MLAI_SECURITY_EVIDENCE_JSON",
        "MLAI_SESSION_SECRET",
        "MLAI_TRUST_PROXY_TLS",
    }
)

EXPECTED_SECRET_BINDINGS = {
    "GEMINI_API_KEY": "mlai-gemini-api-key",
    "MLAI_DATABASE_URL": "mlai-database-url",
    "MLAI_FOUNDER_INVITATION_HASHES_JSON": "mlai-founder-invitation-hashes",
    "MLAI_SESSION_SECRET": "mlai-session-secret",
}

REQUIRED_STATIC_FRAGMENTS = (
    'marketinglabai/private-synthetic-only: "true"',
    'marketinglabai/public-access-authorized: "false"',
    'marketinglabai/real-data-authorized: "false"',
    "name: marketinglabai-velani-pilot",
    'autoscaling.knative.dev/minScale: "0"',
    'autoscaling.knative.dev/maxScale: "1"',
    "mlai-synthetic-runtime@marketinglabai-identity-dev.iam.gserviceaccount.com",
    "marketinglabai-identity-dev:africa-south1:mlai-synthetic-pg18-jhb",
    "value: google-cloud-identity-platform",
    "value: app.identity.google_cloud:create_google_cloud_adapter",
    "value: deployment.providers:create_registry",
    "value: marketinglabai-identity-dev.firebaseapp.com",
)


@dataclass(frozen=True, slots=True)
class ManifestRenderValues:
    immutable_image_digest: str
    private_service_origin: str
    full_git_commit: str
    restricted_browser_api_key: str
    google_oauth_client_id: str

    def substitutions(self) -> Mapping[str, str]:
        return {
            "IMMUTABLE_IMAGE_DIGEST": self.immutable_image_digest,
            "PRIVATE_SERVICE_ORIGIN": self.private_service_origin,
            "FULL_GIT_COMMIT": self.full_git_commit,
            "RESTRICTED_BROWSER_API_KEY": self.restricted_browser_api_key,
            "GOOGLE_OAUTH_CLIENT_ID": self.google_oauth_client_id,
        }


def _matches(text: str, pattern: str) -> tuple[str, ...]:
    return tuple(re.findall(pattern, text, flags=re.MULTILINE))


def _validate_render_values(values: ManifestRenderValues) -> None:
    image_pattern = (
        r"africa-south1-docker\.pkg\.dev/marketinglabai-identity-dev/"
        r"mlai-synthetic/marketinglabai-pilot@sha256:[0-9a-f]{64}"
    )
    if not re.fullmatch(image_pattern, values.immutable_image_digest):
        raise ValueError("The image must be the approved package pinned by digest.")
    if not re.fullmatch(
        r"https://[a-z0-9-]+-[0-9]+\.africa-south1\.run\.app",
        values.private_service_origin,
    ):
        raise ValueError("The private service origin must be the HTTPS Cloud Run URL.")
    if not re.fullmatch(r"[0-9a-f]{40}", values.full_git_commit):
        raise ValueError("The deployment commit must be a full 40-character Git SHA.")
    if not re.fullmatch(r"AIza[0-9A-Za-z_-]{20,}", values.restricted_browser_api_key):
        raise ValueError(
            "The restricted browser API key has an invalid identifier format."
        )
    if not re.fullmatch(
        r"[0-9]+-[0-9A-Za-z_-]+\.apps\.googleusercontent\.com",
        values.google_oauth_client_id,
    ):
        raise ValueError("The Google OAuth web client ID has an invalid format.")


def validate_template(template: str) -> dict[str, object]:
    """Validate the committed template as the only deployment authority."""

    placeholders = _matches(template, r"\{\{([A-Z0-9_]+)\}\}")
    if set(placeholders) != EXPECTED_PLACEHOLDERS:
        raise ValueError("The deployment placeholder contract has drifted.")
    if len(placeholders) != len(EXPECTED_PLACEHOLDERS):
        raise ValueError("Each deployment placeholder must occur exactly once.")

    names = _matches(template, r"^\s*- name:\s+([A-Z][A-Z0-9_]*)\s*$")
    if set(names) != EXPECTED_ENVIRONMENT_NAMES:
        raise ValueError("The Cloud Run environment-variable contract has drifted.")
    if len(names) != len(EXPECTED_ENVIRONMENT_NAMES):
        raise ValueError("Each Cloud Run environment variable must occur exactly once.")

    for fragment in REQUIRED_STATIC_FRAGMENTS:
        if fragment not in template:
            raise ValueError(
                f"Required private deployment contract is missing: {fragment}"
            )
    if "allUsers" in template or "allAuthenticatedUsers" in template:
        raise ValueError("The private template must not grant unauthenticated access.")
    if "postgresql://" in template:
        raise ValueError("Database credentials must not be embedded in the template.")

    for variable, secret in EXPECTED_SECRET_BINDINGS.items():
        binding_pattern = (
            rf"- name:\s+{re.escape(variable)}\s+"
            rf"valueFrom:\s+secretKeyRef:\s+name:\s+{re.escape(secret)}\s+"
            rf"key:\s+latest"
        )
        if not re.search(binding_pattern, template, flags=re.MULTILINE):
            raise ValueError(f"Secret binding has drifted for {variable}.")

    return {
        "environment_variable_count": len(names),
        "placeholder_count": len(placeholders),
        "secret_binding_count": len(EXPECTED_SECRET_BINDINGS),
        "template_valid": True,
    }


def render_manifest(template: str, values: ManifestRenderValues) -> str:
    """Render a fully validated manifest without writing secret values."""

    validate_template(template)
    _validate_render_values(values)
    rendered = template
    for name, value in values.substitutions().items():
        rendered = rendered.replace("{{" + name + "}}", value)
    if "{{" in rendered or "}}" in rendered:
        raise ValueError("The rendered manifest contains unresolved placeholders.")
    return rendered


def _outside_repository(output: Path) -> bool:
    try:
        output.resolve().relative_to(ROOT.resolve())
    except ValueError:
        return True
    return False


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    check = subparsers.add_parser("validate-template")
    check.add_argument("--template", type=Path, default=DEFAULT_TEMPLATE)

    render = subparsers.add_parser("render")
    render.add_argument("--template", type=Path, default=DEFAULT_TEMPLATE)
    render.add_argument("--output", type=Path, required=True)
    render.add_argument("--image", required=True)
    render.add_argument("--origin", required=True)
    render.add_argument("--commit", required=True)
    render.add_argument("--browser-api-key", required=True)
    render.add_argument("--oauth-client-id", required=True)
    return parser


def main(arguments: Sequence[str] | None = None) -> int:
    selected = _parser().parse_args(arguments)
    template = selected.template.read_text(encoding="utf-8-sig")
    if selected.command == "validate-template":
        print(json.dumps(validate_template(template), sort_keys=True))
        return 0

    if not _outside_repository(selected.output):
        raise ValueError("Rendered manifests must remain outside the repository.")
    values = ManifestRenderValues(
        immutable_image_digest=selected.image,
        private_service_origin=selected.origin,
        full_git_commit=selected.commit,
        restricted_browser_api_key=selected.browser_api_key,
        google_oauth_client_id=selected.oauth_client_id,
    )
    rendered = render_manifest(template, values)
    selected.output.parent.mkdir(parents=True, exist_ok=True)
    selected.output.write_text(rendered, encoding="utf-8", newline="\n")
    digest = hashlib.sha256(rendered.encode("utf-8")).hexdigest()
    print(
        json.dumps(
            {
                "output": str(selected.output.resolve()),
                "rendered_manifest_sha256": digest,
                "secret_values_rendered": False,
                "template_valid": True,
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
