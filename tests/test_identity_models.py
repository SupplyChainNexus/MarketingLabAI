"""Tests for provider-neutral identity and role permissions."""

import unittest

from app.identity import (
    AuthenticatedPrincipal,
    IdentityProviderAdapter,
    Permission,
    TenantMembership,
    TenantRole,
)


class SyntheticIdentityAdapter(IdentityProviderAdapter):
    def authenticate(self, credential: str) -> AuthenticatedPrincipal:
        if credential != "synthetic-valid-token":
            raise PermissionError("Credential was rejected.")
        return AuthenticatedPrincipal("subject-one", "synthetic-idp")


class IdentityModelTests(unittest.TestCase):
    def test_external_adapter_returns_trusted_principal(self) -> None:
        principal = SyntheticIdentityAdapter().authenticate("synthetic-valid-token")
        self.assertEqual(principal.subject_id, "subject-one")
        self.assertEqual(principal.provider, "synthetic-idp")

    def test_adapter_rejects_untrusted_credential(self) -> None:
        with self.assertRaises(PermissionError):
            SyntheticIdentityAdapter().authenticate("invalid")

    def test_roles_grant_only_declared_permissions(self) -> None:
        viewer = TenantMembership("subject", "idp", "tenant", TenantRole.VIEWER)
        approver = TenantMembership("subject", "idp", "tenant", TenantRole.APPROVER)
        self.assertTrue(viewer.grants(Permission.VIEW))
        self.assertFalse(viewer.grants(Permission.GENERATE))
        self.assertTrue(approver.grants(Permission.APPROVE))
        self.assertFalse(approver.grants(Permission.MANAGE_MEMBERS))

    def test_inactive_membership_grants_nothing(self) -> None:
        membership = TenantMembership(
            "subject", "idp", "tenant", TenantRole.ADMIN, active=False
        )
        self.assertFalse(membership.grants(Permission.VIEW))


if __name__ == "__main__":
    unittest.main()
