"""Secure pilot API contract, authorization, and retry-safety tests."""

from __future__ import annotations

import io
import json
import tempfile
import unittest
from datetime import date
from pathlib import Path

from app.ai.providers.mock import MockIntelligenceProvider
from app.ai.registry import IntelligenceProviderRegistry
from app.application import CanonicalApplication
from app.campaign_planner import (
    CampaignAudience,
    CampaignChannel,
    CampaignMetric,
    CampaignObjective,
    CampaignPlan,
    CampaignStatus,
    CampaignTimeline,
)
from app.database.connection import SQLiteDatabase
from app.identity import AuthenticatedPrincipal, TenantMembership, TenantRole
from app.identity.provider import IdentityProviderAdapter
from app.marketing_brief import BriefStatus, MarketingBrief, MarketingBriefEvidence
from app.pilot_api import PilotApiService, PilotWsgiApplication
from app.pilot_api.contracts import GenerationRequest
from app.tenants.models import Tenant


class SyntheticIdentityProvider(IdentityProviderAdapter):
    def authenticate(self, credential: str) -> AuthenticatedPrincipal:
        identities = {
            "valid-token": AuthenticatedPrincipal("pilot-user", "synthetic-idp"),
            "other-token": AuthenticatedPrincipal("other-user", "synthetic-idp"),
        }
        try:
            return identities[credential]
        except KeyError as error:
            raise PermissionError("Invalid synthetic credential.") from error


class PilotApiTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory()
        database = SQLiteDatabase(
            Path(self.temporary_directory.name) / "marketinglabai.db"
        )
        self.application = CanonicalApplication.build(database)
        self.application.tenants.save(Tenant("tenant-two", "Tenant Two"))
        self.application.brands.save(
            {"brand_id": "brand-one", "tenant_id": "default", "name": "Brand One"}
        )
        self.application.brands.save(
            {
                "brand_id": "brand-two",
                "tenant_id": "tenant-two",
                "name": "Brand Two",
            }
        )
        self.application.identities.save_membership(
            TenantMembership("pilot-user", "synthetic-idp", "default", TenantRole.ADMIN)
        )
        self.application.identities.save_membership(
            TenantMembership("other-user", "synthetic-idp", "default", TenantRole.ADMIN)
        )
        self._save_approved_governance()
        self.provider = MockIntelligenceProvider(response_content="Synthetic output")
        registry = IntelligenceProviderRegistry()
        registry.register(self.provider)
        self.service = PilotApiService(
            self.application, SyntheticIdentityProvider(), registry
        )
        self.wsgi = PilotWsgiApplication(self.service)

    def tearDown(self) -> None:
        self.temporary_directory.cleanup()

    def _save_approved_governance(self) -> None:
        self.application.campaign_plans.save(
            CampaignPlan(
                campaign_id="campaign-one",
                tenant_id="default",
                brand_id="brand-one",
                name="Synthetic Pilot Campaign",
                objective=CampaignObjective(
                    "Validate the pilot", "Establish synthetic workflow evidence"
                ),
                audience=CampaignAudience("Pilot users", "Synthetic participants"),
                timeline=CampaignTimeline(date(2026, 8, 1), date(2026, 8, 31)),
                channels=(CampaignChannel("Email"),),
                success_metrics=(
                    CampaignMetric("Responses", "10", "Count synthetic responses"),
                ),
                owner="Pilot Team",
                status=CampaignStatus.APPROVED,
            )
        )
        self.application.marketing_briefs.save(
            MarketingBrief(
                brief_id="brief-one",
                tenant_id="default",
                brand_id="brand-one",
                name="Synthetic Pilot Brief",
                objective="Validate the pilot",
                audience="Synthetic participants",
                key_message="A synthetic pilot message",
                call_to_action="Review the synthetic result",
                channels=["Email"],
                deliverables=["Email draft"],
                evidence=[
                    MarketingBriefEvidence(
                        "synthetic", "evidence-one", "Synthetic evidence only"
                    )
                ],
                status=BriefStatus.APPROVED,
            )
        )

    @staticmethod
    def generation_body(**overrides) -> dict:
        body = {
            "brand_id": "brand-one",
            "campaign_id": "campaign-one",
            "campaign_version": 1,
            "brief_id": "brief-one",
            "brief_version": 1,
            "task": "Create synthetic pilot content",
            "instructions": "Use only approved context.",
        }
        body.update(overrides)
        return body

    def request(
        self,
        path: str,
        body: dict | None = None,
        *,
        token: str = "valid-token",
        tenant_id: str = "default",
        idempotency_key: str = "request-one",
    ) -> tuple[int, dict]:
        encoded = json.dumps(body or {}).encode()
        environ = {
            "REQUEST_METHOD": "POST",
            "PATH_INFO": path,
            "CONTENT_LENGTH": str(len(encoded)),
            "CONTENT_TYPE": "application/json",
            "HTTP_AUTHORIZATION": f"Bearer {token}",
            "HTTP_X_TENANT_ID": tenant_id,
            "HTTP_IDEMPOTENCY_KEY": idempotency_key,
            "wsgi.input": io.BytesIO(encoded),
        }
        captured = {}

        def start_response(status, headers):
            captured["status"] = int(status.split()[0])
            captured["headers"] = headers

        response_body = b"".join(self.wsgi(environ, start_response))
        return captured["status"], json.loads(response_body)

    def test_generation_contract_requires_approved_governance_versions(self) -> None:
        request = GenerationRequest(**self.generation_body())
        self.assertEqual(request.campaign_version, 1)
        with self.assertRaisesRegex(ValueError, "campaign_version"):
            GenerationRequest(**self.generation_body(campaign_version=0))

    def test_context_returns_transport_safe_missing_context_contract(self) -> None:
        status, payload = self.request("/v1/pilot/context", {"brand_id": "brand-one"})
        self.assertEqual(status, 200)
        self.assertEqual(payload["data"]["brand_id"], "brand-one")
        self.assertIn("missing", payload["data"])
        self.assertNotIn("repository", json.dumps(payload).lower())

    def test_generation_is_identity_bound_and_idempotent(self) -> None:
        first_status, first = self.request("/v1/pilot/generate", self.generation_body())
        second_status, second = self.request(
            "/v1/pilot/generate", self.generation_body()
        )
        self.assertEqual((first_status, second_status), (201, 201))
        self.assertFalse(first["replayed"])
        self.assertTrue(second["replayed"])
        self.assertEqual(len(self.provider.requests), 1)
        metadata = self.provider.requests[0].metadata
        self.assertEqual(metadata["approved_campaign_id"], "campaign-one")
        self.assertEqual(metadata["approved_brief_id"], "brief-one")
        self.assertEqual(metadata["authenticated_subject_id"], "pilot-user")

    def test_same_key_with_changed_request_is_a_conflict(self) -> None:
        self.request("/v1/pilot/generate", self.generation_body())
        status, payload = self.request(
            "/v1/pilot/generate", self.generation_body(task="Changed task")
        )
        self.assertEqual(status, 409)
        self.assertEqual(payload["error"]["code"], "idempotency_conflict")
        self.assertEqual(len(self.provider.requests), 1)

    def test_idempotency_scope_includes_authenticated_identity(self) -> None:
        self.request("/v1/pilot/generate", self.generation_body())
        status, payload = self.request(
            "/v1/pilot/generate", self.generation_body(), token="other-token"
        )
        self.assertEqual(status, 201)
        self.assertFalse(payload["replayed"])
        self.assertEqual(len(self.provider.requests), 2)

    def test_unapproved_plan_is_rejected_before_provider_call(self) -> None:
        plan = self.application.campaign_plans.get(
            "campaign-one", tenant_id="default", version=1
        )
        plan.version = 2
        plan.status = CampaignStatus.PLANNED
        self.application.campaign_plans.save(plan)
        status, payload = self.request(
            "/v1/pilot/generate",
            self.generation_body(campaign_version=2),
            idempotency_key="unapproved-plan",
        )
        self.assertEqual(status, 409)
        self.assertEqual(payload["error"]["code"], "lifecycle_conflict")
        self.assertEqual(len(self.provider.requests), 0)

    def test_approval_replay_and_stale_version_conflict(self) -> None:
        plan = self.application.campaign_plans.get(
            "campaign-one", tenant_id="default", version=1
        )
        plan.campaign_id = "campaign-planned"
        plan.status = CampaignStatus.PLANNED
        self.application.campaign_plans.save(plan)
        path = "/v1/pilot/campaign-plans/campaign-planned/approve"
        first_status, first = self.request(
            path, {"expected_version": 1}, idempotency_key="approve-one"
        )
        replay_status, replay = self.request(
            path, {"expected_version": 1}, idempotency_key="approve-one"
        )
        stale_status, stale = self.request(
            path, {"expected_version": 1}, idempotency_key="approve-stale"
        )
        self.assertEqual((first_status, replay_status, stale_status), (200, 200, 409))
        self.assertEqual(first["data"]["version"], 2)
        self.assertTrue(replay["replayed"])
        self.assertEqual(stale["error"]["code"], "lifecycle_conflict")
        self.assertEqual(
            len(
                self.application.campaign_plans.list_versions(
                    "campaign-planned", tenant_id="default"
                )
            ),
            2,
        )

    def test_export_authorization_is_audited_and_retry_safe(self) -> None:
        body = {"resource_type": "campaign_plan", "resource_id": "campaign-one"}
        first_status, first = self.request(
            "/v1/pilot/exports/authorize", body, idempotency_key="export-one"
        )
        replay_status, replay = self.request(
            "/v1/pilot/exports/authorize", body, idempotency_key="export-one"
        )
        self.assertEqual((first_status, replay_status), (200, 200))
        self.assertTrue(first["data"]["authorized"])
        self.assertTrue(replay["replayed"])
        events = self.application.identities.list_audit_events(tenant_id="default")
        export_events = [event for event in events if event.action == "export"]
        self.assertEqual(len(export_events), 1)

    def test_authentication_and_cross_tenant_access_are_denied(self) -> None:
        status, payload = self.request(
            "/v1/pilot/context", {"brand_id": "brand-one"}, token="invalid"
        )
        self.assertEqual(status, 401)
        self.assertEqual(payload["error"]["code"], "unauthenticated")
        status, payload = self.request("/v1/pilot/context", {"brand_id": "brand-two"})
        self.assertEqual(status, 403)
        self.assertEqual(payload["error"]["code"], "forbidden")

    def test_missing_idempotency_key_and_unknown_endpoint_are_rejected(self) -> None:
        status, payload = self.request(
            "/v1/pilot/generate", self.generation_body(), idempotency_key=""
        )
        self.assertEqual(status, 400)
        self.assertEqual(payload["error"]["code"], "idempotency_required")
        status, payload = self.request("/v1/pilot/unknown")
        self.assertEqual(status, 404)
        self.assertEqual(payload["error"]["code"], "not_found")

    def test_migration_twelve_is_idempotent(self) -> None:
        self.application.database.initialise()
        self.application.database.initialise()
        with self.application.database.connection() as connection:
            count = connection.execute(
                "SELECT COUNT(*) FROM schema_migrations WHERE version = 12"
            ).fetchone()[0]
        self.assertEqual(count, 1)
        self.assertIn(
            "api_idempotency_records", self.application.database.table_names()
        )


if __name__ == "__main__":
    unittest.main()
