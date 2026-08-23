"""Secure pilot API contract, authorization, and retry-safety tests."""

from __future__ import annotations

import base64
import hashlib
import io
import json
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from datetime import date
from pathlib import Path
from unittest.mock import patch

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
from app.design_partner import FounderDesignPartnerSignupService, PilotPrivacyPolicy
from app.identity import AuthenticatedPrincipal, TenantMembership, TenantRole
from app.identity.provider import IdentityProviderAdapter
from app.marketing_brief import BriefStatus, MarketingBrief, MarketingBriefEvidence
from app.marketing_workflow import MarketingWorkflowService
from app.marketing_workflow.canonical import canonical_json, record_sha256
from app.pilot_api import PilotApiService, PilotWsgiApplication
from app.pilot_api.contracts import GenerationRequest
from app.positioning_intelligence import (
    PositioningDecision,
    PositioningEvidence,
    PositioningStatus,
    TargetKind,
)
from app.strategy_intelligence import (
    StrategyDecision,
    StrategyEvidence,
    StrategyStatus,
)
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

    @staticmethod
    def verify_csrf(credential: str, csrf_token: str, tenant_id: str) -> bool:
        return bool(credential and tenant_id and csrf_token == "synthetic-csrf")


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
            self.application,
            SyntheticIdentityProvider(),
            registry,
            founder_invitation_hashes={
                "strand-auto-parts-pilot": FounderDesignPartnerSignupService.hash_invitation(
                    "strand-invitation"
                ),
                "velani-wholesale-pilot": FounderDesignPartnerSignupService.hash_invitation(
                    "velani-invitation"
                ),
            },
        )
        self.wsgi = PilotWsgiApplication(self.service)

    def tearDown(self) -> None:
        self.temporary_directory.cleanup()

    def _save_approved_governance(self) -> None:
        self.application.positioning_intelligence.save(
            PositioningDecision(
                positioning_id="positioning-one",
                version=1,
                tenant_id="default",
                brand_id="brand-one",
                target_kind=TargetKind.SEGMENT,
                target_id="segment-one",
                product_id="product-one",
                value_proposition="Verified synthetic value proposition.",
                evidence=[
                    PositioningEvidence(
                        "Synthetic evidence",
                        "Verified for workflow tests.",
                        1.0,
                        verified=True,
                    )
                ],
                status=PositioningStatus.APPROVED,
                approved_at="2026-08-06T00:00:00+00:00",
            )
        )
        self.application.strategy_intelligence.save(
            StrategyDecision(
                strategy_id="strategy-one",
                version=1,
                tenant_id="default",
                brand_id="brand-one",
                positioning_id="positioning-one",
                positioning_version=1,
                status=StrategyStatus.APPROVED,
                business_objectives=["Validate synthetic demand"],
                evidence=[
                    StrategyEvidence("Synthetic", "Reviewed objective", 0.9, True)
                ],
                approved_at="2026-08-06T00:00:00+00:00",
            )
        )
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
                positioning_id="positioning-one",
                positioning_version=1,
                strategy_id="strategy-one",
                strategy_version=1,
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
                positioning_id="positioning-one",
                positioning_version=1,
                strategy_id="strategy-one",
                strategy_version=1,
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
        method: str = "POST",
        token: str = "valid-token",
        tenant_id: str = "default",
        idempotency_key: str = "request-one",
        csrf_token: str = "",
        raw: bool = False,
    ) -> tuple:
        encoded = json.dumps(body or {}).encode()
        environ = {
            "REQUEST_METHOD": method,
            "PATH_INFO": path,
            "CONTENT_LENGTH": str(len(encoded)),
            "CONTENT_TYPE": "application/json",
            "HTTP_AUTHORIZATION": f"Bearer {token}",
            "HTTP_X_TENANT_ID": tenant_id,
            "HTTP_IDEMPOTENCY_KEY": idempotency_key,
            "HTTP_X_CSRF_TOKEN": csrf_token,
            "HTTP_X_BRAND_ID": "brand-one",
            "wsgi.input": io.BytesIO(encoded),
        }
        captured = {}

        def start_response(status, headers):
            captured["status"] = int(status.split()[0])
            captured["headers"] = headers

        response_body = b"".join(self.wsgi(environ, start_response))
        result = captured["status"], json.loads(response_body)
        if raw:
            return (*result, captured["headers"], response_body)
        return result

    def test_founder_signup_creates_owner_without_a_tenant_header(self) -> None:
        status, payload = self.request(
            "/v1/pilot/design-partner/signup",
            {
                "partner_name": "Velani Wholesale",
                "invitation_code": "velani-invitation",
                "privacy_notice_accepted": True,
                "synthetic_data_boundary_accepted": True,
            },
            tenant_id="",
        )
        self.assertEqual(status, 201)
        self.assertEqual(payload["data"]["tenant_id"], "velani-wholesale-pilot")
        membership = self.application.identities.get_membership(
            provider="synthetic-idp",
            subject_id="pilot-user",
            tenant_id="velani-wholesale-pilot",
        )
        self.assertEqual(membership.role, TenantRole.ADMIN)
        self.assertFalse(payload["data"]["real_data_activation_authorized"])
        self.assertEqual(
            payload["data"]["privacy_notice_version"],
            PilotPrivacyPolicy.NOTICE_VERSION,
        )

    def test_privacy_pack_is_identity_and_tenant_bound(self) -> None:
        signup_status, _ = self.request(
            "/v1/pilot/design-partner/signup",
            {
                "partner_name": "Velani Wholesale",
                "invitation_code": "velani-invitation",
                "privacy_notice_accepted": True,
                "synthetic_data_boundary_accepted": True,
            },
            tenant_id="",
        )
        self.assertEqual(signup_status, 201)
        status, payload = self.request(
            "/v1/pilot/privacy/pack",
            {},
            tenant_id="velani-wholesale-pilot",
        )
        self.assertEqual(status, 200)
        self.assertTrue(payload["data"]["acceptance"]["current"])
        self.assertFalse(payload["data"]["real_data_activation_authorized"])

    def test_data_boundary_api_denies_real_customer_records(self) -> None:
        self.request(
            "/v1/pilot/design-partner/signup",
            {
                "partner_name": "Strand Auto Parts",
                "invitation_code": "strand-invitation",
                "privacy_notice_accepted": True,
                "synthetic_data_boundary_accepted": True,
            },
            tenant_id="",
        )
        status, payload = self.request(
            "/v1/pilot/privacy/authorize",
            {"category": "customer_records"},
            tenant_id="strand-auto-parts-pilot",
        )
        self.assertEqual(status, 200)
        self.assertFalse(payload["data"]["allowed"])
        self.assertFalse(payload["data"]["real_data_activation_authorized"])

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
        self.assertEqual(metadata["approved_positioning_id"], "positioning-one")
        self.assertEqual(metadata["authenticated_subject_id"], "pilot-user")

    def test_workflow_create_plan_requires_csrf_and_replays(self) -> None:
        body = {
            "brand_id": "brand-one",
            "campaign_plan_id": "campaign-one",
            "campaign_plan_version": 1,
            "marketing_brief_id": "brief-one",
            "marketing_brief_version": 1,
        }
        status, payload = self.request(
            "/v1/pilot/workflows", body, idempotency_key="a" * 22
        )
        self.assertEqual(status, 403)
        self.assertEqual(payload["error"]["code"], "csrf_required")
        status, payload = self.request(
            "/v1/pilot/workflows",
            body,
            idempotency_key="a" * 22,
            csrf_token="synthetic-csrf",
        )
        self.assertEqual(status, 202)
        self.assertEqual(payload["data"]["state"], "awaiting_approval")
        replay_status, replay = self.request(
            "/v1/pilot/workflows",
            body,
            idempotency_key="a" * 22,
            csrf_token="synthetic-csrf",
        )
        self.assertEqual(replay_status, 202)
        self.assertNotIn("replayed", replay)
        self.assertEqual(payload["data"]["workflow_id"], replay["data"]["workflow_id"])

    def test_workflow_status_and_approval_stop_at_approved(self) -> None:
        body = {
            "brand_id": "brand-one",
            "campaign_plan_id": "campaign-one",
            "campaign_plan_version": 1,
            "marketing_brief_id": "brief-one",
            "marketing_brief_version": 1,
        }
        _, created = self.request(
            "/v1/pilot/workflows",
            body,
            idempotency_key="b" * 22,
            csrf_token="synthetic-csrf",
        )
        workflow_id = created["data"]["workflow_id"]
        status, payload = self.request(
            f"/v1/pilot/workflows/{workflow_id}",
            method="GET",
            body=None,
        )
        self.assertEqual(status, 200)
        self.assertEqual(payload["data"]["state"], "awaiting_approval")
        self.assertIn("technical_details", payload["data"])
        status, payload = self.request(
            f"/v1/pilot/workflows/{workflow_id}/approval",
            {"brand_id": "brand-one", "expected_version": 3, "decision": "approved"},
            idempotency_key="c" * 22,
            csrf_token="synthetic-csrf",
        )
        self.assertEqual(status, 200)
        self.assertEqual(payload["data"]["state"], "approved")

        status, payload = self.request(
            f"/v1/pilot/workflows/{workflow_id}", method="GET", body=None
        )
        self.assertEqual(status, 200)
        self.assertEqual(payload["data"]["state"], "approved")

    def test_workflow_operations_use_child_claims_and_exact_replay(self) -> None:
        body = {
            "brand_id": "brand-one",
            "campaign_plan_id": "campaign-one",
            "campaign_plan_version": 1,
            "marketing_brief_id": "brief-one",
            "marketing_brief_version": 1,
        }
        _, created = self.request(
            "/v1/pilot/workflows",
            body,
            idempotency_key="child-create-key-1234567890",
            csrf_token="synthetic-csrf",
        )
        workflow_id = created["data"]["workflow_id"]
        with self.application.database.connection() as connection:
            create_claim = connection.execute("""
                SELECT final_response_status, final_response_json,
                       final_response_sha256
                FROM workflow_api_operation_claims
                WHERE operation = 'create_and_plan'
                """).fetchone()
        self.assertEqual(create_claim["final_response_status"], 202)
        self.assertIsNotNone(create_claim["final_response_json"])
        self.assertIsNotNone(create_claim["final_response_sha256"])

        first_status, status_payload, first_headers, first_bytes = self.request(
            f"/v1/pilot/workflows/{workflow_id}", method="GET", body=None, raw=True
        )
        replay_status, replay_payload, replay_headers, replay_bytes = self.request(
            f"/v1/pilot/workflows/{workflow_id}", method="GET", body=None, raw=True
        )
        self.assertEqual((first_status, replay_status), (200, 200))
        self.assertEqual(status_payload["data"], replay_payload["data"])
        self.assertNotIn("replayed", replay_payload)
        self.assertEqual(first_headers, replay_headers)
        self.assertEqual(first_bytes, replay_bytes)
        with self.application.database.connection() as connection:
            status_claim = connection.execute("""
                SELECT final_response_json, final_response_sha256
                FROM workflow_api_operation_claims
                WHERE operation = 'status'
                """).fetchone()
        envelope = json.loads(status_claim["final_response_json"])
        body = base64.b64decode(envelope["body_utf8_b64"])
        self.assertEqual(body, first_bytes)
        self.assertEqual(hashlib.sha256(body).hexdigest(), envelope["body_sha256"])
        self.assertEqual(
            hashlib.sha256(
                json.dumps(
                    {
                        key: value
                        for key, value in envelope.items()
                        if key != "envelope_sha256"
                    },
                    ensure_ascii=False,
                    sort_keys=True,
                    separators=(",", ":"),
                ).encode("utf-8")
            ).hexdigest(),
            envelope["envelope_sha256"],
        )
        self.assertIsNotNone(status_claim["final_response_sha256"])

        approval_request = {
            "brand_id": "brand-one",
            "expected_version": 3,
        }
        first_status, first = self.request(
            f"/v1/pilot/workflows/{workflow_id}/request-approval",
            approval_request,
            idempotency_key="child-request-key-1234567890",
            csrf_token="synthetic-csrf",
        )
        replay_status, replay = self.request(
            f"/v1/pilot/workflows/{workflow_id}/request-approval",
            approval_request,
            idempotency_key="child-request-key-1234567890",
            csrf_token="synthetic-csrf",
        )
        self.assertEqual((first_status, replay_status), (200, 200))
        self.assertEqual(first["data"], replay["data"])
        self.assertNotIn("replayed", replay)

        changed_status, changed = self.request(
            f"/v1/pilot/workflows/{workflow_id}/request-approval",
            {"brand_id": "brand-one", "expected_version": 2},
            idempotency_key="child-request-key-1234567890",
            csrf_token="synthetic-csrf",
        )
        self.assertEqual(changed_status, 409)
        self.assertEqual(changed["error"]["code"], "idempotency_conflict")

        decision = {
            "brand_id": "brand-one",
            "expected_version": 3,
            "decision": "approved",
        }
        first_status, first = self.request(
            f"/v1/pilot/workflows/{workflow_id}/approval",
            decision,
            idempotency_key="child-approval-key-1234567890",
            csrf_token="synthetic-csrf",
        )
        replay_status, replay = self.request(
            f"/v1/pilot/workflows/{workflow_id}/approval",
            decision,
            idempotency_key="child-approval-key-1234567890",
            csrf_token="synthetic-csrf",
        )
        self.assertEqual((first_status, replay_status), (200, 200))
        self.assertEqual(first["data"], replay["data"])
        self.assertNotIn("replayed", replay)
        with self.application.database.connection() as connection:
            rows = connection.execute("""
                SELECT operation, final_response_status, final_response_json
                FROM workflow_api_operation_claims
                WHERE operation IN ('status', 'request_approval', 'approval_decision')
                ORDER BY operation
                """).fetchall()
        self.assertEqual(
            {str(row["operation"]) for row in rows},
            {"status", "request_approval", "approval_decision"},
        )
        self.assertTrue(all(row["final_response_json"] for row in rows))

    def test_approval_rejects_tampered_evidence_chain(self) -> None:
        body = {
            "brand_id": "brand-one",
            "campaign_plan_id": "campaign-one",
            "campaign_plan_version": 1,
            "marketing_brief_id": "brief-one",
            "marketing_brief_version": 1,
        }
        _, created = self.request(
            "/v1/pilot/workflows",
            body,
            idempotency_key="tamper-create-key-1234567890",
            csrf_token="synthetic-csrf",
        )
        with self.application.database.transaction() as connection:
            connection.execute(
                """
                UPDATE workflow_evidence
                SET canonical_json = ?
                WHERE sequence = 3
                """,
                ('{"tampered":true}',),
            )
        status, payload = self.request(
            f"/v1/pilot/workflows/{created['data']['workflow_id']}/approval",
            {
                "brand_id": "brand-one",
                "expected_version": 3,
                "decision": "approved",
            },
            idempotency_key="tamper-approval-key-1234567890",
            csrf_token="synthetic-csrf",
        )
        self.assertIn(status, {400, 409})
        self.assertIn(
            payload["error"]["code"], {"invalid_request", "workflow_conflict"}
        )

    def test_create_recovers_after_workflow_creation_before_child_claim(self) -> None:
        body = {
            "brand_id": "brand-one",
            "campaign_plan_id": "campaign-one",
            "campaign_plan_version": 1,
            "marketing_brief_id": "brief-one",
            "marketing_brief_version": 1,
        }
        original_claim = self.application.workflow_operation_claims.claim

        def crash_before_child(*args, **kwargs):
            raise RuntimeError("simulated child-claim crash")

        self.application.workflow_operation_claims.claim = crash_before_child
        try:
            failed_status, failed = self.request(
                "/v1/pilot/workflows",
                body,
                idempotency_key="crash-child-claim-key-123456",
                csrf_token="synthetic-csrf",
            )
        finally:
            self.application.workflow_operation_claims.claim = original_claim
        self.assertEqual(failed_status, 409)
        self.assertEqual(failed["error"]["code"], "workflow_conflict")
        with self.application.database.connection() as connection:
            self.assertEqual(
                connection.execute(
                    "SELECT COUNT(*) FROM marketing_workflows"
                ).fetchone()[0],
                1,
            )
            gap_workflow_id = connection.execute(
                "SELECT workflow_id FROM marketing_workflows"
            ).fetchone()["workflow_id"]
            self.assertEqual(
                connection.execute(
                    "SELECT COUNT(*) FROM workflow_api_operation_claims "
                    "WHERE operation = 'create_and_plan'"
                ).fetchone()[0],
                0,
            )
        gap_status, gap_payload = self.request(
            f"/v1/pilot/workflows/{gap_workflow_id}",
            method="GET",
            body=None,
        )
        self.assertEqual(gap_status, 200)
        self.assertEqual(gap_payload["data"]["state"], "draft")
        with self.application.database.connection() as connection:
            parent = connection.execute(
                "SELECT progress_state FROM workflow_api_orchestrations"
            ).fetchone()
            self.assertEqual(parent["progress_state"], "claimed")
            self.assertEqual(
                connection.execute(
                    "SELECT COUNT(*) FROM workflow_api_operation_claims "
                    "WHERE operation = 'create_and_plan'"
                ).fetchone()[0],
                0,
            )
        recovered_status, recovered, recovered_headers, recovered_bytes = self.request(
            "/v1/pilot/workflows",
            body,
            idempotency_key="crash-child-claim-key-123456",
            csrf_token="synthetic-csrf",
            raw=True,
        )
        self.assertEqual(recovered_status, 202, recovered)
        self.assertEqual(recovered["data"]["state"], "awaiting_approval")
        replay_status, replay_payload, replay_headers, replay_bytes = self.request(
            "/v1/pilot/workflows",
            body,
            idempotency_key="crash-child-claim-key-123456",
            csrf_token="synthetic-csrf",
            raw=True,
        )
        self.assertEqual(replay_status, recovered_status)
        self.assertEqual(replay_payload, recovered)
        self.assertNotIn("replayed", replay_payload)
        self.assertEqual(replay_headers, recovered_headers)
        self.assertEqual(replay_bytes, recovered_bytes)
        with self.application.database.connection() as connection:
            self.assertEqual(
                connection.execute(
                    "SELECT COUNT(*) FROM marketing_workflows"
                ).fetchone()[0],
                1,
            )
            self.assertEqual(
                connection.execute(
                    "SELECT COUNT(*) FROM workflow_api_operation_claims "
                    "WHERE operation = 'create_and_plan'"
                ).fetchone()[0],
                1,
            )

    def test_concurrent_first_submissions_converge_on_one_workflow(self) -> None:
        body = {
            "brand_id": "brand-one",
            "campaign_plan_id": "campaign-one",
            "campaign_plan_version": 1,
            "marketing_brief_id": "brief-one",
            "marketing_brief_version": 1,
        }

        def submit():
            return self.request(
                "/v1/pilot/workflows",
                body,
                idempotency_key="concurrent-first-key-123456",
                csrf_token="synthetic-csrf",
            )

        with ThreadPoolExecutor(max_workers=2) as executor:
            results = list(executor.map(lambda _: submit(), (1, 2)))
        self.assertEqual([status for status, _ in results], [202, 202], results)
        self.assertEqual(
            results[0][1]["data"]["workflow_id"], results[1][1]["data"]["workflow_id"]
        )
        with self.application.database.connection() as connection:
            self.assertEqual(
                connection.execute(
                    "SELECT COUNT(*) FROM marketing_workflows"
                ).fetchone()[0],
                1,
            )
            self.assertEqual(
                connection.execute(
                    "SELECT COUNT(*) FROM workflow_api_orchestrations"
                ).fetchone()[0],
                1,
            )

    def test_approval_recovers_after_approval_persistence_crash(self) -> None:
        body = {
            "brand_id": "brand-one",
            "campaign_plan_id": "campaign-one",
            "campaign_plan_version": 1,
            "marketing_brief_id": "brief-one",
            "marketing_brief_version": 1,
        }
        _, created = self.request(
            "/v1/pilot/workflows",
            body,
            idempotency_key="approval-recovery-create-123456",
            csrf_token="synthetic-csrf",
        )
        workflow_id = created["data"]["workflow_id"]
        original_record_approval = MarketingWorkflowService.record_approval

        def persist_then_crash(service, command, **kwargs):
            original_record_approval(service, command, **kwargs)
            raise RuntimeError("simulated crash after approval persistence")

        with patch.object(
            MarketingWorkflowService, "record_approval", new=persist_then_crash
        ):
            failed_status, failed = self.request(
                f"/v1/pilot/workflows/{workflow_id}/approval",
                {
                    "brand_id": "brand-one",
                    "expected_version": 3,
                    "decision": "approved",
                },
                idempotency_key="approval-recovery-key-123456",
                csrf_token="synthetic-csrf",
            )
        self.assertEqual(failed_status, 409)
        self.assertEqual(failed["error"]["code"], "workflow_conflict")
        recovered_status, recovered = self.request(
            f"/v1/pilot/workflows/{workflow_id}/approval",
            {
                "brand_id": "brand-one",
                "expected_version": 3,
                "decision": "approved",
            },
            idempotency_key="approval-recovery-key-123456",
            csrf_token="synthetic-csrf",
        )
        self.assertEqual(recovered_status, 200, recovered)
        self.assertEqual(recovered["data"]["state"], "approved")

    def test_approval_rejects_ambiguous_evidence(self) -> None:
        body = {
            "brand_id": "brand-one",
            "campaign_plan_id": "campaign-one",
            "campaign_plan_version": 1,
            "marketing_brief_id": "brief-one",
            "marketing_brief_version": 1,
        }
        _, created = self.request(
            "/v1/pilot/workflows",
            body,
            idempotency_key="ambiguous-evidence-create-123456",
            csrf_token="synthetic-csrf",
        )
        workflow_id = created["data"]["workflow_id"]
        with self.application.database.transaction() as connection:
            source = connection.execute(
                """
                SELECT * FROM workflow_evidence
                WHERE workflow_id = ? AND sequence = 3
                """,
                (workflow_id,),
            ).fetchone()
            envelope = json.loads(source["canonical_json"])
            envelope["evidence_id"] = "mwe_ambiguous"
            envelope["sequence"] = 4
            envelope["predecessor_sha256"] = source["evidence_sha256"]
            digest = record_sha256("workflow_evidence", envelope)
            connection.execute(
                """
                INSERT INTO workflow_evidence (
                    evidence_id, tenant_id, brand_id, workflow_id,
                    workflow_version, sequence, predecessor_sha256,
                    evidence_sha256, canonical_json, occurred_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    envelope["evidence_id"],
                    envelope["tenant_id"],
                    envelope["brand_id"],
                    envelope["workflow_id"],
                    envelope["workflow_version"],
                    envelope["sequence"],
                    envelope["predecessor_sha256"],
                    digest,
                    canonical_json(envelope),
                    envelope["occurred_at"],
                ),
            )
        status, payload = self.request(
            f"/v1/pilot/workflows/{workflow_id}/approval",
            {
                "brand_id": "brand-one",
                "expected_version": 3,
                "decision": "approved",
            },
            idempotency_key="ambiguous-evidence-approval-123456",
            csrf_token="synthetic-csrf",
        )
        self.assertIn(status, {400, 409})
        self.assertIn(
            payload["error"]["code"], {"invalid_request", "workflow_conflict"}
        )

    def test_workflow_cross_tenant_create_does_not_disclose(self) -> None:
        status, payload = self.request(
            "/v1/pilot/workflows",
            {
                "brand_id": "brand-one",
                "campaign_plan_id": "campaign-one",
                "campaign_plan_version": 1,
            },
            tenant_id="tenant-two",
            idempotency_key="cross-tenant-create-123456",
            csrf_token="synthetic-csrf",
        )
        self.assertIn(status, {403, 404})
        self.assertNotIn("campaign-one", json.dumps(payload))

    def test_workflow_cross_tenant_status_does_not_disclose(self) -> None:
        status, payload = self.request(
            "/v1/pilot/workflows/mwf_missing",
            method="GET",
            tenant_id="tenant-two",
            body=None,
        )
        self.assertIn(status, {403, 404})
        self.assertNotIn("mwf_missing", json.dumps(payload))

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
