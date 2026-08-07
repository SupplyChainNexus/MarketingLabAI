"""Tests for default-deny controlled hosting readiness."""

import unittest

from app.operations.hosting_readiness import (
    ControlledHostingConfiguration,
    HostingConfigurationError,
    require_cloud_deployment_authorization,
)


class ControlledHostingTests(unittest.TestCase):
    def values(self) -> dict[str, str]:
        return {
            "MLAI_CLOUD_PROJECT_ID": "marketinglabai-identity-dev",
            "MLAI_CLOUD_REGION": "africa-south1",
            "MLAI_CLOUD_RUN_SERVICE": "marketinglabai-velani-pilot",
            "MLAI_DEPLOYMENT_COMMIT": "a" * 40,
            "MLAI_PERSISTENCE_BACKEND": "postgresql",
            "MLAI_DATABASE_SECRET_REFERENCE": (
                "projects/marketinglabai-identity-dev/secrets/database-url"
            ),
            "MLAI_CLOUD_SQL_INSTANCE": (
                "marketinglabai-identity-dev:africa-south1:mlai-synthetic-pg18-jhb"
            ),
            "MLAI_CLOUD_RUN_MAX_INSTANCES": "1",
            "MLAI_CLOUD_RUN_MIN_INSTANCES": "0",
            "MLAI_CLOUD_RUN_CONCURRENCY": "8",
            "MLAI_CLOUD_RUN_CPU": "1",
            "MLAI_CLOUD_RUN_MEMORY_MIB": "512",
            "MLAI_MONTHLY_BUDGET_ZAR": "500",
            "MLAI_SECRET_BINDINGS_JSON": (
                '{"GEMINI_API_KEY":"projects/p/secrets/gemini-api-key",'
                '"MLAI_DATABASE_URL":"projects/p/secrets/database-url",'
                '"MLAI_SESSION_SECRET":"projects/p/secrets/session-secret",'
                '"MLAI_FOUNDER_INVITATION_HASHES_JSON":'
                '"projects/p/secrets/invitation-hashes"}'
            ),
            "MLAI_DURABLE_ADAPTER_VERIFIED": "true",
            "MLAI_DURABLE_ADAPTER_EVIDENCE_REFERENCE": (
                "evidence://synthetic-postgresql-rehearsal/commit"
            ),
        }

    def test_complete_configuration_is_engineering_ready_but_never_authorizes(self):
        report = ControlledHostingConfiguration.from_environment(
            self.values()
        ).evaluate()

        self.assertTrue(report.engineering_ready)
        self.assertFalse(report.cloud_build_authorized)
        self.assertFalse(report.cloud_deployment_authorized)
        self.assertFalse(report.external_invitation_authorized)
        self.assertFalse(report.real_data_activation_authorized)

    def test_sqlite_is_explicitly_refused_for_cloud_run(self):
        values = self.values()
        values["MLAI_PERSISTENCE_BACKEND"] = "sqlite"

        report = ControlledHostingConfiguration.from_environment(values).evaluate()

        self.assertFalse(report.engineering_ready)
        self.assertFalse(
            next(
                check for check in report.checks if check.name == "durable_backend"
            ).passed
        )

    def test_unverified_adapter_blocks_engineering_readiness(self):
        values = self.values()
        values["MLAI_DURABLE_ADAPTER_VERIFIED"] = "false"

        report = ControlledHostingConfiguration.from_environment(values).evaluate()

        self.assertFalse(report.engineering_ready)
        with self.assertRaises(PermissionError):
            require_cloud_deployment_authorization(
                report, founder_decision_recorded=True
            )

    def test_adapter_boolean_without_traceable_evidence_is_refused(self):
        values = self.values()
        values["MLAI_DURABLE_ADAPTER_EVIDENCE_REFERENCE"] = ""

        report = ControlledHostingConfiguration.from_environment(values).evaluate()

        self.assertFalse(report.engineering_ready)

    def test_founder_decision_is_required_after_engineering_passes(self):
        report = ControlledHostingConfiguration.from_environment(
            self.values()
        ).evaluate()

        with self.assertRaises(PermissionError):
            require_cloud_deployment_authorization(
                report, founder_decision_recorded=False
            )

    def test_unbounded_cost_and_scale_values_are_rejected(self):
        for key, value in (
            ("MLAI_CLOUD_RUN_MAX_INSTANCES", "100"),
            ("MLAI_CLOUD_RUN_MEMORY_MIB", "4096"),
            ("MLAI_MONTHLY_BUDGET_ZAR", "5000"),
        ):
            with self.subTest(key=key):
                values = self.values()
                values[key] = value
                with self.assertRaises(HostingConfigurationError):
                    ControlledHostingConfiguration.from_environment(values)

    def test_required_secrets_must_be_external_bindings(self):
        values = self.values()
        values["MLAI_SECRET_BINDINGS_JSON"] = (
            '{"MLAI_DATABASE_URL":"postgresql://plain-text-password"}'
        )

        with self.assertRaises(HostingConfigurationError):
            ControlledHostingConfiguration.from_environment(values)


if __name__ == "__main__":
    unittest.main()
