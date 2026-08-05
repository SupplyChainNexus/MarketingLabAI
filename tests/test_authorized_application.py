"""Cross-tenant denial tests for every authorized application operation."""

import tempfile
import unittest
from pathlib import Path

from app.ai.providers.mock import MockIntelligenceProvider
from app.ai.registry import IntelligenceProviderRegistry
from app.application import CanonicalApplication
from app.database.connection import SQLiteDatabase
from app.identity import (
    AuthenticatedPrincipal,
    AuthorizationDeniedError,
    TenantMembership,
    TenantRole,
)
from app.tenants.models import Tenant


class AuthorizedApplicationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.folder = tempfile.TemporaryDirectory()
        self.application = CanonicalApplication.build(
            SQLiteDatabase(Path(self.folder.name) / "db.sqlite")
        )
        self.application.tenants.save(Tenant("tenant-two", "Tenant Two"))
        self.application.brands.save(
            {"brand_id": "brand-one", "tenant_id": "default", "name": "One"}
        )
        self.application.brands.save(
            {"brand_id": "brand-two", "tenant_id": "tenant-two", "name": "Two"}
        )
        self.principal = AuthenticatedPrincipal("subject-one", "synthetic-idp")
        self.application.identities.save_membership(
            TenantMembership(
                "subject-one", "synthetic-idp", "default", TenantRole.ADMIN
            )
        )
        self.session = self.application.authorize(self.principal, tenant_id="default")
        self.registry = IntelligenceProviderRegistry()
        self.registry.register(MockIntelligenceProvider(response_content="Synthetic"))
        self._insert_other_tenant_resources()

    def tearDown(self) -> None:
        self.folder.cleanup()

    def _insert_other_tenant_resources(self) -> None:
        with self.application.database.transaction() as connection:
            connection.execute("""
                INSERT INTO campaign_plans
                    (campaign_id, version, tenant_id, brand_id, name, status,
                     payload_json, created_at, updated_at)
                VALUES ('other-campaign', 1, 'tenant-two', 'brand-two', 'Other',
                        'planned', '{}', 'now', 'now')
                """)
            connection.execute("""
                INSERT INTO marketing_briefs
                    (brief_id, version, tenant_id, brand_id, name, status,
                     payload_json, created_at, updated_at)
                VALUES ('other-brief', 1, 'tenant-two', 'brand-two', 'Other',
                        'ready', '{}', 'now', 'now')
                """)

    def test_missing_membership_cannot_create_tenant_session(self) -> None:
        principal = AuthenticatedPrincipal("outsider", "synthetic-idp")
        with self.assertRaises(AuthorizationDeniedError):
            self.application.authorize(principal, tenant_id="default")

    def test_context_denies_cross_tenant_brand(self) -> None:
        with self.assertRaises(AuthorizationDeniedError):
            self.session.build_context(brand_id="brand-two")

    def test_generation_denies_cross_tenant_brand(self) -> None:
        with self.assertRaises(AuthorizationDeniedError):
            self.session.generate(
                self.registry, brand_id="brand-two", task="Synthetic task"
            )

    def test_campaign_approval_denies_cross_tenant_resource(self) -> None:
        with self.assertRaises(AuthorizationDeniedError):
            self.session.approve_campaign_plan("other-campaign")

    def test_brief_approval_denies_cross_tenant_resource(self) -> None:
        with self.assertRaises(AuthorizationDeniedError):
            self.session.approve_marketing_brief("other-brief")

    def test_export_denies_cross_tenant_resource(self) -> None:
        with self.assertRaises(AuthorizationDeniedError):
            self.session.authorize_export(
                resource_type="campaign_plan", resource_id="other-campaign"
            )

    def test_membership_management_denies_cross_tenant_membership(self) -> None:
        with self.assertRaises(AuthorizationDeniedError):
            self.session.save_membership(
                TenantMembership(
                    "new-subject", "synthetic-idp", "tenant-two", TenantRole.VIEWER
                )
            )

    def test_allowed_generation_is_identity_bound_and_audited(self) -> None:
        response = self.session.generate(
            self.registry, brand_id="brand-one", task="Synthetic task"
        )
        request = self.registry.active_provider().requests[0]
        self.assertEqual(response.content, "Synthetic")
        self.assertEqual(request.metadata["authenticated_subject_id"], "subject-one")
        events = self.application.identities.list_audit_events(tenant_id="default")
        self.assertIn("identity", [event.action for event in events])
        self.assertIn("generate", [event.action for event in events])
        self.assertTrue(any(event.outcome == "denied" for event in events) is False)

    def test_viewer_cannot_generate(self) -> None:
        self.application.identities.save_membership(
            TenantMembership("viewer", "synthetic-idp", "default", TenantRole.VIEWER)
        )
        viewer = self.application.authorize(
            AuthenticatedPrincipal("viewer", "synthetic-idp"), tenant_id="default"
        )
        with self.assertRaises(AuthorizationDeniedError):
            viewer.generate(self.registry, brand_id="brand-one", task="Synthetic task")


if __name__ == "__main__":
    unittest.main()
