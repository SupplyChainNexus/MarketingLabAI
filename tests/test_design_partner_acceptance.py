"""MLAI-030.6 partner-specific synthetic acceptance tests."""

from __future__ import annotations

import json
import tempfile
import unittest
from datetime import UTC, datetime, timedelta
from pathlib import Path

from app.database.connection import SQLiteDatabase
from app.design_partner import DesignPartnerAcceptanceEvaluator, PilotPrivacyPolicy
from app.operations import (
    OperationalReadinessEvaluator,
    PilotConfiguration,
    ReadinessEvidence,
    ReadinessEvidenceRepository,
)
from app.operations.security import ProductionSecurityEvaluator
from app.tenants.models import Tenant
from app.tenants.repository import TenantRepository


class DesignPartnerAcceptanceTests(unittest.TestCase):
    commit_sha = "724eaa7271e0c8cec1c7bb2752dc1f73d26c2fe5"

    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.database = SQLiteDatabase(Path(self.temp.name) / "acceptance.sqlite3")
        self.config = PilotConfiguration.from_environment(
            {
                "MLAI_ENVIRONMENT": "controlled-acceptance-rehearsal",
                "MLAI_DATABASE_PATH": str(self.database.database_path),
                "MLAI_BACKUP_DIRECTORY": str(Path(self.temp.name) / "backups"),
                "MLAI_PUBLIC_ORIGIN": "https://pilot.example.test",
                "MLAI_TRUST_PROXY_TLS": "false",
                "MLAI_SESSION_SECRET": "s" * 48,
                "MLAI_SESSION_TTL_SECONDS": "3600",
                "MLAI_IDENTITY_PROVIDER": "google-cloud-identity-platform",
                "MLAI_IDENTITY_ADAPTER_FACTORY": "test:factory",
                "MLAI_PROVIDER_REGISTRY_FACTORY": "test:registry",
                "MLAI_GOOGLE_CLOUD_PROJECT_ID": "marketinglabai-identity-dev",
                "MLAI_GOOGLE_WEB_API_KEY": "restricted-browser-key",
                "MLAI_GOOGLE_OAUTH_CLIENT_ID": "test.apps.googleusercontent.com",
                "MLAI_GOOGLE_AUTH_DOMAIN": "marketinglabai-identity-dev.firebaseapp.com",
                "MLAI_FOUNDER_INVITATION_HASHES_JSON": json.dumps(
                    {
                        "strand-auto-parts-pilot": "a" * 64,
                        "velani-wholesale-pilot": "b" * 64,
                    }
                ),
                "MLAI_ALLOW_REAL_CUSTOMER_DATA": "false",
                "MLAI_DEPLOYMENT_COMMIT": self.commit_sha,
            }
        )
        self.repository = ReadinessEvidenceRepository(self.database)
        TenantRepository(self.database).save(
            Tenant("strand-auto-parts-pilot", "Strand Auto Parts")
        )
        self.evaluator = DesignPartnerAcceptanceEvaluator(self.config, self.database)

    def tearDown(self) -> None:
        self.temp.cleanup()

    def add_pass(self, name: str) -> None:
        now = datetime.now(UTC)
        self.repository.add(
            ReadinessEvidence(
                check_name=name,
                environment=self.config.environment,
                commit_sha=self.commit_sha,
                operator_id="founder-operator",
                passed=True,
                evidence_reference=f"ToolkitTemp/evidence/{name}.json",
                observed_at=now.isoformat(),
                expires_at=(now + timedelta(days=30)).isoformat(),
            )
        )

    def complete_prerequisites(self) -> None:
        for name in (
            *ProductionSecurityEvaluator.EXTERNAL_EVIDENCE,
            *OperationalReadinessEvaluator.REQUIRED_EVIDENCE,
        ):
            self.add_pass(name)

    def accept_privacy(self) -> None:
        with self.database.transaction() as connection:
            connection.execute(
                """
                INSERT INTO pilot_privacy_acceptances (
                    tenant_id, provider, subject_id, notice_version,
                    boundary_version, accepted_at
                ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    "strand-auto-parts-pilot",
                    "synthetic-idp",
                    "synthetic-user",
                    PilotPrivacyPolicy.NOTICE_VERSION,
                    PilotPrivacyPolicy.BOUNDARY_VERSION,
                    datetime.now(UTC).isoformat(),
                ),
            )

    def test_missing_prerequisites_refuse_actual_acceptance_rehearsal(self) -> None:
        report = self.evaluator.evaluate(
            partner_name="Strand Auto Parts", tenant_id="strand-auto-parts-pilot"
        )
        self.assertFalse(report["synthetic_rehearsal_authorized"])
        self.assertIn(
            "production_security_and_operational_prerequisites", report["blockers"]
        )
        self.assertFalse(report["real_data_activation_authorized"])

    def test_tenant_mismatch_is_denied(self) -> None:
        with self.assertRaisesRegex(PermissionError, "does not match"):
            self.evaluator.evaluate(
                partner_name="Strand Auto Parts",
                tenant_id="velani-wholesale-pilot",
            )

    def test_complete_partner_evidence_is_independent_and_never_activates(self) -> None:
        self.complete_prerequisites()
        self.accept_privacy()
        for scenario in self.evaluator.REQUIRED_SCENARIOS:
            self.add_pass(
                self.evaluator.evidence_name("strand-auto-parts-pilot", scenario)
            )
        report = self.evaluator.evaluate(
            partner_name="Strand Auto Parts", tenant_id="strand-auto-parts-pilot"
        )
        self.assertTrue(report["acceptance_rehearsal_passed"])
        self.assertTrue(report["ready_for_founder_activation_assessment"])
        self.assertFalse(report["real_data_activation_authorized"])
        self.assertFalse(report["external_invitations_authorized"])
        self.assertFalse(report["billing_enabled"])
        self.assertFalse(report["market_validation_claimed"])


if __name__ == "__main__":
    unittest.main()
