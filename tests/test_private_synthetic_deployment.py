"""Tests for the controlled private synthetic Cloud Run boundary."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from app import config as application_config
from app.ai.registry import IntelligenceProviderRegistry
from app.operations.configuration import PilotConfiguration
from deployment.private_synthetic import PrivateSyntheticDeploymentSpecification
from deployment.private_synthetic_manifest import (
    ManifestRenderValues,
    render_manifest,
    validate_template,
)
from deployment.providers import create_registry
from deployment.start import configured_port


class PrivateSyntheticDeploymentTests(unittest.TestCase):
    def specification(self) -> PrivateSyntheticDeploymentSpecification:
        project = "marketinglabai-identity-dev"
        return PrivateSyntheticDeploymentSpecification(
            project_id=project,
            region="africa-south1",
            service_name="marketinglabai-velani-pilot",
            runtime_service_account=f"mlai-synthetic-runtime@{project}.iam.gserviceaccount.com",
            cloud_sql_instance=f"{project}:africa-south1:mlai-synthetic-pg18-jhb",
            artifact_image=(
                f"africa-south1-docker.pkg.dev/{project}/mlai-synthetic/"
                f"marketinglabai-pilot@sha256:{'a' * 64}"
            ),
            minimum_instances=0,
            maximum_instances=1,
            cpu=1,
            memory_mib=512,
            concurrency=8,
            ingress="all",
            allow_unauthenticated=False,
            real_customer_data=False,
            secret_bindings={
                name: f"projects/{project}/secrets/{secret}"
                for name, secret in {
                    "GEMINI_API_KEY": "mlai-gemini-api-key",
                    "MLAI_DATABASE_URL": "mlai-database-url",
                    "MLAI_SESSION_SECRET": "mlai-session-secret",
                    "MLAI_FOUNDER_INVITATION_HASHES_JSON": "mlai-founder-invitation-hashes",
                }.items()
            },
        )

    def test_complete_specification_is_ready_but_never_self_authorizes(self):
        report = self.specification().evaluate()
        self.assertTrue(report.engineering_ready)
        payload = report.to_dict()
        for key in (
            "private_synthetic_deployment_authorized",
            "public_access_authorized",
            "external_invitation_authorized",
            "real_customer_data_authorized",
            "billing_authorized",
            "publishing_authorized",
            "real_data_learning_authorized",
        ):
            self.assertFalse(payload[key])

    def test_public_real_data_mutable_images_and_scale_are_refused(self):
        values = self.specification()
        for changes in (
            {"allow_unauthenticated": True},
            {"real_customer_data": True},
            {"artifact_image": values.artifact_image.split("@", 1)[0] + ":latest"},
            {"maximum_instances": 3},
        ):
            with self.subTest(changes=changes):
                selected = {
                    field: getattr(values, field)
                    for field in values.__dataclass_fields__
                }
                selected.update(changes)
                self.assertFalse(
                    PrivateSyntheticDeploymentSpecification(**selected)
                    .evaluate()
                    .engineering_ready
                )

    def test_secret_values_and_wrong_cloud_sql_instance_are_refused(self):
        values = self.specification()
        for changes in (
            {"secret_bindings": {"GEMINI_API_KEY": "plain-text-value"}},
            {
                "cloud_sql_instance": (
                    "marketinglabai-identity-dev:africa-south1:other-instance"
                )
            },
        ):
            selected = {
                field: getattr(values, field) for field in values.__dataclass_fields__
            }
            selected.update(changes)
            self.assertFalse(
                PrivateSyntheticDeploymentSpecification(**selected)
                .evaluate()
                .engineering_ready
            )

    def test_cloud_runtime_does_not_require_source_tree_dotenv(self):
        with tempfile.TemporaryDirectory() as directory:
            with (
                patch.object(application_config, "ENV_FILE", Path(directory) / ".env"),
                patch.dict(
                    application_config.os.environ,
                    {
                        "GEMINI_API_KEY": "synthetic-test-key",
                        "GEMINI_MODEL": "gemini-test-model",
                    },
                    clear=True,
                ),
                patch.object(application_config, "create_required_folders"),
            ):
                settings = application_config.load_settings()
        self.assertEqual("synthetic-test-key", settings.gemini_api_key)
        self.assertEqual("gemini-test-model", settings.gemini_model)

    def test_provider_factory_and_port_are_bounded(self):
        registry = IntelligenceProviderRegistry()
        bootstrap = Mock()
        bootstrap.build_registry.return_value = registry
        with patch(
            "deployment.providers.gemini_provider_bootstrap", return_value=bootstrap
        ):
            self.assertIs(registry, create_registry(object()))
        self.assertEqual(8080, configured_port({}))
        self.assertEqual(9090, configured_port({"PORT": "9090"}))
        for value in ("invalid", "80", "70000"):
            with self.subTest(value=value), self.assertRaises(ValueError):
                configured_port({"PORT": value})

    def test_container_and_manifest_preserve_boundary(self):
        root = Path(__file__).resolve().parent.parent
        dockerfile = (root / "Dockerfile").read_text(encoding="utf-8")
        manifest = (
            root / "deployment" / "cloud-run.private-synthetic.yaml.template"
        ).read_text(encoding="utf-8")
        dockerignore = (root / ".dockerignore").read_text(encoding="utf-8")
        for required in ("USER 10001:10001", "deployment.start", "EXPOSE 8080"):
            self.assertIn(required, dockerfile)
        for required in (
            'marketinglabai/public-access-authorized: "false"',
            'marketinglabai/real-data-authorized: "false"',
            "MLAI_ALLOW_REAL_CUSTOMER_DATA",
            "mlai-synthetic-runtime@",
            "mlai-synthetic-pg18-jhb",
            "secretKeyRef",
            "{{IMMUTABLE_IMAGE_DIGEST}}",
        ):
            self.assertIn(required, manifest)
        self.assertNotIn("allUsers", manifest)
        self.assertNotIn("postgresql://", manifest)
        for excluded in (".env", "database", "outputs", "backups"):
            self.assertIn(excluded, dockerignore)

    def test_canonical_manifest_contract_renders_without_drift(self):
        root = Path(__file__).resolve().parent.parent
        template = (
            root / "deployment" / "cloud-run.private-synthetic.yaml.template"
        ).read_text(encoding="utf-8")
        report = validate_template(template)
        self.assertTrue(report["template_valid"])
        rendered = render_manifest(
            template,
            ManifestRenderValues(
                immutable_image_digest=(
                    "africa-south1-docker.pkg.dev/marketinglabai-identity-dev/"
                    "mlai-synthetic/marketinglabai-pilot@sha256:" + "a" * 64
                ),
                private_service_origin=(
                    "https://marketinglabai-velani-pilot-483973859553."
                    "africa-south1.run.app"
                ),
                full_git_commit="a" * 40,
                restricted_browser_api_key="AIza" + "A" * 32,
                google_oauth_client_id=(
                    "483973859553-synthetic.apps.googleusercontent.com"
                ),
            ),
        )
        self.assertNotIn("{{", rendered)
        self.assertIn("marketinglabai-pilot@sha256:", rendered)
        self.assertNotIn("allUsers", rendered)

    def test_manifest_contract_rejects_missing_or_duplicate_variables(self):
        root = Path(__file__).resolve().parent.parent
        template = (
            root / "deployment" / "cloud-run.private-synthetic.yaml.template"
        ).read_text(encoding="utf-8")
        for changed in (
            template.replace("            - name: MLAI_ENVIRONMENT\n", "", 1),
            template.replace(
                "            - name: MLAI_ENVIRONMENT\n",
                "            - name: MLAI_ENVIRONMENT\n"
                "            - name: MLAI_ENVIRONMENT\n",
                1,
            ),
        ):
            with self.subTest(), self.assertRaises(ValueError):
                validate_template(changed)

    def test_identity_provider_and_factory_must_form_one_runtime_contract(self):
        values = {
            "MLAI_PUBLIC_ORIGIN": "https://private.example.test",
            "MLAI_TRUST_PROXY_TLS": "true",
            "MLAI_ENVIRONMENT": "cloud-synthetic",
            "MLAI_SESSION_SECRET": "s" * 32,
            "MLAI_IDENTITY_PROVIDER": "synthetic",
            "MLAI_IDENTITY_ADAPTER_FACTORY": (
                "app.identity.google_cloud:create_google_cloud_adapter"
            ),
            "MLAI_PROVIDER_REGISTRY_FACTORY": "deployment.providers:create_registry",
            "MLAI_DATABASE_PATH": "/tmp/unused.sqlite3",
            "MLAI_BACKUP_DIRECTORY": "/tmp/backups",
            "MLAI_ALLOW_REAL_CUSTOMER_DATA": "false",
        }
        with self.assertRaisesRegex(ValueError, "cloud-synthetic runtime"):
            PilotConfiguration.from_environment(values)

        values.update(
            {
                "MLAI_IDENTITY_PROVIDER": "google-cloud-identity-platform",
                "MLAI_GOOGLE_CLOUD_PROJECT_ID": "marketinglabai-identity-dev",
                "MLAI_GOOGLE_WEB_API_KEY": "AIza" + "A" * 32,
                "MLAI_GOOGLE_OAUTH_CLIENT_ID": (
                    "483973859553-synthetic.apps.googleusercontent.com"
                ),
                "MLAI_GOOGLE_AUTH_DOMAIN": (
                    "marketinglabai-identity-dev.firebaseapp.com"
                ),
            }
        )
        configuration = PilotConfiguration.from_environment(values)
        self.assertEqual(
            "google-cloud-identity-platform", configuration.identity_provider
        )


class DockerBuildContextRegressionTests(unittest.TestCase):
    def test_every_docker_copy_source_is_tracked(self):
        import subprocess
        from pathlib import Path

        repository = Path(__file__).resolve().parents[1]
        dockerfile = (repository / "Dockerfile").read_text(encoding="utf-8")

        tracked_result = subprocess.run(
            ["git", "ls-files"],
            cwd=repository,
            check=True,
            capture_output=True,
            text=True,
        )
        tracked_paths = set(tracked_result.stdout.splitlines())

        copy_sources = []
        for raw_line in dockerfile.splitlines():
            line = raw_line.strip()
            if not line.startswith("COPY "):
                continue

            parts = line.split()
            self.assertGreaterEqual(
                len(parts),
                3,
                msg=f"Unsupported Docker COPY instruction: {line}",
            )

            sources = parts[1:-1]
            self.assertTrue(
                sources,
                msg=f"Docker COPY has no source: {line}",
            )
            copy_sources.extend(sources)

        self.assertTrue(copy_sources, msg="Dockerfile has no COPY sources")

        for raw_source in copy_sources:
            source = raw_source.rstrip("/")
            source_path = repository / source

            self.assertTrue(
                source_path.exists(),
                msg=f"Docker COPY source does not exist: {raw_source}",
            )

            source_is_tracked = source in tracked_paths or any(
                tracked.startswith(source + "/") for tracked in tracked_paths
            )

            self.assertTrue(
                source_is_tracked,
                msg=f"Docker COPY source is not tracked: {raw_source}",
            )


if __name__ == "__main__":
    unittest.main()
