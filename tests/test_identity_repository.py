"""Tests for membership and authorization audit persistence."""

import tempfile
import unittest
from pathlib import Path

from app.database.connection import SQLiteDatabase
from app.identity import (
    AuthenticatedPrincipal,
    AuthorizationDeniedError,
    IdentityRepository,
    Permission,
    TenantAuthorizationService,
    TenantMembership,
    TenantRole,
)


class IdentityRepositoryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.folder = tempfile.TemporaryDirectory()
        self.database = SQLiteDatabase(Path(self.folder.name) / "db.sqlite")
        self.database.initialise()
        self.repository = IdentityRepository(self.database)
        self.principal = AuthenticatedPrincipal("subject-one", "synthetic-idp")

    def tearDown(self) -> None:
        self.folder.cleanup()

    def test_membership_round_trip(self) -> None:
        membership = TenantMembership(
            "subject-one", "synthetic-idp", "default", TenantRole.MARKETER
        )
        self.repository.save_membership(membership)
        self.assertEqual(
            self.repository.get_membership(
                provider="synthetic-idp", subject_id="subject-one", tenant_id="default"
            ),
            membership,
        )

    def test_default_deny_and_allowed_decisions_are_audited(self) -> None:
        service = TenantAuthorizationService(self.repository)
        with self.assertRaises(AuthorizationDeniedError):
            service.authorize(
                self.principal,
                tenant_id="default",
                permission=Permission.VIEW,
                resource_type="tenant",
                resource_id="default",
            )
        self.repository.save_membership(
            TenantMembership(
                "subject-one", "synthetic-idp", "default", TenantRole.VIEWER
            )
        )
        service.authorize(
            self.principal,
            tenant_id="default",
            permission=Permission.VIEW,
            resource_type="tenant",
            resource_id="default",
        )
        events = self.repository.list_audit_events(tenant_id="default")
        self.assertEqual([event.outcome for event in events], ["denied", "allowed"])

    def test_resource_tenant_mismatch_is_denied_and_audited(self) -> None:
        self.repository.save_membership(
            TenantMembership(
                "subject-one", "synthetic-idp", "default", TenantRole.ADMIN
            )
        )
        service = TenantAuthorizationService(self.repository)
        with self.assertRaises(AuthorizationDeniedError):
            service.authorize(
                self.principal,
                tenant_id="default",
                permission=Permission.VIEW,
                resource_type="brand",
                resource_id="other-brand",
                resource_tenant_id="other-tenant",
            )
        event = self.repository.list_audit_events(tenant_id="default")[-1]
        self.assertEqual(event.outcome, "denied")


if __name__ == "__main__":
    unittest.main()
