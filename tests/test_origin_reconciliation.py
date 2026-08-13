import shutil
import tempfile
import unittest
from pathlib import Path

from tools.release_control.origin_reconciliation import (
    OriginReconciliationInputs,
    prepare_origin_reconciliation,
)


def _copy_template(repository: Path) -> None:
    template = repository / "deployment" / "cloud-run.private-synthetic.yaml.template"
    template.parent.mkdir(parents=True)
    shutil.copyfile(
        Path("deployment/cloud-run.private-synthetic.yaml.template"), template
    )


def _release(image_suffix: str = "a") -> dict[str, str]:
    return {
        "commit": "22392443177c67b7252ae51182b335e7491357f5",
        "image_digest": (
            "africa-south1-docker.pkg.dev/marketinglabai-identity-dev/"
            "mlai-synthetic/marketinglabai-pilot@sha256:" + image_suffix * 64
        ),
    }


def _configuration() -> dict[str, str]:
    return {
        "project": "marketinglabai-identity-dev",
        "region": "africa-south1",
        "service": "marketinglabai-velani-pilot",
        "runtime_service_account": (
            "mlai-synthetic-runtime@marketinglabai-identity-dev.iam.gserviceaccount.com"
        ),
        "manifest_template": "deployment/cloud-run.private-synthetic.yaml.template",
    }


def _revision_evidence() -> dict[str, object]:
    return {
        "result": "REVISION_CREATED",
        "created_revision": "marketinglabai-velani-pilot-00001-t5h",
        "mutation_count": 1,
        "requires_origin_reconciliation": True,
        "secret_value_access": False,
    }


def _startup_inspection(
    release: dict[str, str], *, startup_can_pass_now: bool = False
) -> dict[str, object]:
    return {
        "result": "STARTUP_ORIGIN_INSPECTION_COMPLETED",
        "latest_ready_revision": "marketinglabai-velani-pilot-00001-t5h",
        "latest_revision_matches_expected": True,
        "latest_revision_ready": True,
        "image": release["image_digest"],
        "image_matches_expected": True,
        "service_url": "https://marketinglabai-velani-pilot-lqye7ebcsa-bq.a.run.app",
        "observed_public_origin": "https://marketinglabai-velani-pilot-first-bootstrap.invalid",
        "private_ingress": True,
        "no_public_iam": True,
        "real_service_url_observed": True,
        "bootstrap_origin_still_configured": True,
        "startup_can_pass_now": startup_can_pass_now,
        "cloud_mutation_performed": False,
        "release_state_modified": False,
        "secret_values_accessed": False,
    }


class OriginReconciliationTests(unittest.TestCase):
    def test_first_service_bootstrap_requires_real_origin_reconciliation(self):
        with (
            tempfile.TemporaryDirectory() as repo,
            tempfile.TemporaryDirectory() as out,
        ):
            repository = Path(repo)
            _copy_template(repository)
            release = _release()

            plan = prepare_origin_reconciliation(
                configuration=_configuration(),
                release=release,
                revision_created_evidence=_revision_evidence(),
                startup_origin_inspection=_startup_inspection(release),
                repository_root=repository,
                output_root=Path(out),
                inputs=OriginReconciliationInputs(
                    restricted_browser_api_key="AIzaSySyntheticTestKey000000000000000000",
                    google_oauth_client_id="123456789012-syntheticclientid.apps.googleusercontent.com",
                ),
            )

            self.assertEqual(plan["result"], "ORIGIN_RECONCILIATION_PREPARED")
            self.assertEqual(plan["gate"], "ORIGIN_RECONCILED")
            self.assertEqual(plan["maximum_mutation_count"], 1)
            self.assertFalse(plan["cloud_cli_executed"])
            self.assertFalse(plan["cloud_mutation_performed"])
            self.assertEqual(
                plan["real_private_service_origin"],
                "https://marketinglabai-velani-pilot-lqye7ebcsa-bq.a.run.app",
            )
            self.assertTrue(Path(plan["manifest_path"]).is_file())

    def test_startup_must_not_pass_before_reconciliation(self):
        with (
            tempfile.TemporaryDirectory() as repo,
            tempfile.TemporaryDirectory() as out,
        ):
            repository = Path(repo)
            _copy_template(repository)
            release = _release("b")

            with self.assertRaisesRegex(ValueError, "Startup must not pass"):
                prepare_origin_reconciliation(
                    configuration=_configuration(),
                    release=release,
                    revision_created_evidence=_revision_evidence(),
                    startup_origin_inspection=_startup_inspection(
                        release,
                        startup_can_pass_now=True,
                    ),
                    repository_root=repository,
                    output_root=Path(out),
                    inputs=OriginReconciliationInputs(
                        "AIzaSySyntheticTestKey000000000000000000",
                        "123456789012-syntheticclientid.apps.googleusercontent.com",
                    ),
                )


if __name__ == "__main__":
    unittest.main()
