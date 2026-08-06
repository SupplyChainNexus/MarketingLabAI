"""Pilot privacy, data-boundary, and acceptance-evidence tests."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from app.database.connection import SQLiteDatabase
from app.design_partner import (
    FounderDesignPartnerSignupService,
    PilotDataCategory,
    PilotPrivacyPolicy,
)
from tests.test_design_partner_signup import SignupIdentityProvider


class PilotPrivacyTests(unittest.TestCase):
    def test_policy_is_tenant_scoped_and_default_deny(self) -> None:
        policy = PilotPrivacyPolicy()
        allowed = policy.authorize(
            tenant_id="strand-auto-parts-pilot",
            category=PilotDataCategory.SYNTHETIC_BUSINESS_PROFILE.value,
        )
        prohibited = policy.authorize(
            tenant_id="strand-auto-parts-pilot",
            category=PilotDataCategory.CUSTOMER_RECORDS.value,
        )
        self.assertTrue(allowed.allowed)
        self.assertFalse(prohibited.allowed)
        self.assertFalse(prohibited.real_data_activation_authorized)
        with self.assertRaisesRegex(ValueError, "tenant is not approved"):
            policy.authorize(
                tenant_id="unapproved-tenant",
                category=PilotDataCategory.SYNTHETIC_BUSINESS_PROFILE.value,
            )
        with self.assertRaisesRegex(ValueError, "Unsupported pilot data category"):
            policy.authorize(
                tenant_id="strand-auto-parts-pilot",
                category="unknown_category",
            )

    def test_pack_has_explicit_categories_and_no_real_data_periods(self) -> None:
        pack = PilotPrivacyPolicy().pack(tenant_id="velani-wholesale-pilot")
        self.assertIn("synthetic_customer_persona", pack["allowed_categories"])
        self.assertIn("personal_data", pack["prohibited_categories"])
        self.assertIsNone(pack["retention"]["real_data_records_days"])
        self.assertIsNone(pack["retention"]["real_data_deletion_sla_days"])
        self.assertFalse(pack["real_data_activation_authorized"])

    def test_signup_records_versioned_acceptance_atomically(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            database = SQLiteDatabase(Path(directory) / "privacy.sqlite3")
            database.initialise()
            service = FounderDesignPartnerSignupService(
                database,
                SignupIdentityProvider(),
                {
                    "strand-auto-parts-pilot": service_hash("strand-secret"),
                },
            )
            result = service.signup(
                credential="strand-proof",
                partner_name="Strand Auto Parts",
                invitation_code="strand-secret",
                privacy_notice_accepted=True,
                synthetic_data_boundary_accepted=True,
            )
            with database.connection() as connection:
                rows = connection.execute(
                    "SELECT * FROM pilot_privacy_acceptances"
                ).fetchall()
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0]["tenant_id"], result.tenant_id)
            self.assertEqual(
                rows[0]["notice_version"], PilotPrivacyPolicy.NOTICE_VERSION
            )
            self.assertEqual(
                rows[0]["boundary_version"], PilotPrivacyPolicy.BOUNDARY_VERSION
            )

    def test_stale_policy_version_creates_no_tenant(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            database = SQLiteDatabase(Path(directory) / "stale.sqlite3")
            database.initialise()
            service = FounderDesignPartnerSignupService(
                database,
                SignupIdentityProvider(),
                {"strand-auto-parts-pilot": service_hash("strand-secret")},
            )
            with self.assertRaisesRegex(ValueError, "current privacy notice"):
                service.signup(
                    credential="strand-proof",
                    partner_name="Strand Auto Parts",
                    invitation_code="strand-secret",
                    privacy_notice_accepted=True,
                    synthetic_data_boundary_accepted=True,
                    privacy_notice_version="stale",
                )
            with database.connection() as connection:
                count = connection.execute(
                    "SELECT COUNT(*) FROM pilot_privacy_acceptances"
                ).fetchone()[0]
            self.assertEqual(count, 0)

    def test_migration_sixteen_is_idempotent(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            database = SQLiteDatabase(Path(directory) / "migration.sqlite3")
            database.initialise()
            database.initialise()
            with database.connection() as connection:
                count = connection.execute(
                    "SELECT COUNT(*) FROM schema_migrations WHERE version = 16"
                ).fetchone()[0]
            self.assertEqual(count, 1)


def service_hash(value: str) -> str:
    return FounderDesignPartnerSignupService.hash_invitation(value)


if __name__ == "__main__":
    unittest.main()
