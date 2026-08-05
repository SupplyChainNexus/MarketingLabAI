"""Controlled Founder Design Partner signup tests."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from app.database.connection import SQLiteDatabase
from app.design_partner import (
    FounderDesignPartnerSignupService,
    SignupConflictError,
)
from app.identity import AuthenticatedPrincipal, IdentityProviderAdapter


class SignupIdentityProvider(IdentityProviderAdapter):
    def authenticate(self, credential: str) -> AuthenticatedPrincipal:
        identities = {
            "strand-proof": AuthenticatedPrincipal("strand-owner", "test-oidc"),
            "velani-proof": AuthenticatedPrincipal("velani-owner", "test-oidc"),
            "other-proof": AuthenticatedPrincipal("other-owner", "test-oidc"),
        }
        if credential not in identities:
            raise PermissionError("Invalid identity proof.")
        return identities[credential]


class FounderDesignPartnerSignupTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.database = SQLiteDatabase(
            Path(self.temporary_directory.name) / "signup.sqlite3"
        )
        self.database.initialise()
        self.codes = {
            "strand-auto-parts-pilot": "strand-secret",
            "velani-wholesale-pilot": "velani-secret",
        }
        self.service = FounderDesignPartnerSignupService(
            self.database,
            SignupIdentityProvider(),
            {
                tenant_id: FounderDesignPartnerSignupService.hash_invitation(code)
                for tenant_id, code in self.codes.items()
            },
        )

    def tearDown(self) -> None:
        self.temporary_directory.cleanup()

    def signup(self, name: str, credential: str, code: str):
        return self.service.signup(
            credential=credential,
            partner_name=name,
            invitation_code=code,
            privacy_notice_accepted=True,
            synthetic_data_boundary_accepted=True,
        )

    def test_each_business_signs_up_into_an_isolated_tenant(self) -> None:
        strand = self.signup("Strand Auto Parts", "strand-proof", "strand-secret")
        velani = self.signup("Velani Wholesale", "velani-proof", "velani-secret")
        self.assertNotEqual(strand.tenant_id, velani.tenant_id)
        with self.database.connection() as connection:
            rows = connection.execute(
                """
                SELECT tenant_id, subject_id, role FROM tenant_memberships
                WHERE tenant_id IN (?, ?) ORDER BY tenant_id
                """,
                (strand.tenant_id, velani.tenant_id),
            ).fetchall()
        self.assertEqual(len(rows), 2)
        self.assertEqual({str(row["role"]) for row in rows}, {"admin"})

    def test_signup_is_retry_safe_for_the_same_authenticated_owner(self) -> None:
        first = self.signup("Strand Auto Parts", "strand-proof", "strand-secret")
        replay = self.signup("Strand Auto Parts", "strand-proof", "strand-secret")
        self.assertFalse(first.replayed)
        self.assertTrue(replay.replayed)

    def test_claimed_invitation_rejects_another_identity(self) -> None:
        self.signup("Strand Auto Parts", "strand-proof", "strand-secret")
        with self.assertRaisesRegex(SignupConflictError, "already claimed"):
            self.signup("Strand Auto Parts", "other-proof", "strand-secret")

    def test_invalid_invitation_and_missing_consent_create_nothing(self) -> None:
        with self.assertRaises(PermissionError):
            self.signup("Velani Wholesale", "velani-proof", "wrong")
        with self.assertRaisesRegex(ValueError, "privacy notice"):
            self.service.signup(
                credential="velani-proof",
                partner_name="Velani Wholesale",
                invitation_code="velani-secret",
                privacy_notice_accepted=False,
                synthetic_data_boundary_accepted=True,
            )
        with self.database.connection() as connection:
            created = connection.execute(
                "SELECT COUNT(*) AS total FROM tenants WHERE tenant_id != 'default'"
            ).fetchone()
        self.assertEqual(int(created["total"]), 0)


if __name__ == "__main__":
    unittest.main()
