"""MLAI-030.7 controlled activation boundary tests."""

from __future__ import annotations

import tempfile
import unittest
from datetime import UTC, datetime, timedelta
from pathlib import Path

from app.database.connection import SQLiteDatabase
from app.database.factory import bootstrap_database
from app.design_partner import (
    ActivatedDataCategory,
    ActivationStage,
    ControlledActivationService,
    FounderActivationDecision,
)
from app.tenants.models import Tenant
from app.tenants.repository import TenantRepository


class AcceptanceStub:
    def __init__(self, ready: bool) -> None:
        self.ready = ready

    def evaluate(self, **_kwargs):
        return {"ready_for_founder_activation_assessment": self.ready}


class ControlledActivationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.database = SQLiteDatabase(Path(self.temp.name) / "activation.sqlite3")
        bootstrap_database(self.database)
        TenantRepository(self.database).save(
            Tenant("velani-wholesale-pilot", "Velani Wholesale")
        )
        TenantRepository(self.database).save(
            Tenant("strand-auto-parts-pilot", "Strand Auto Parts")
        )
        self.service = ControlledActivationService(self.database)

    def tearDown(self) -> None:
        self.temp.cleanup()

    def decision(
        self,
        *,
        partner="Velani Wholesale",
        tenant="velani-wholesale-pilot",
        stage=ActivationStage.EXTERNAL_SYNTHETIC,
        categories=(),
    ):
        now = datetime.now(UTC) - timedelta(seconds=1)
        return FounderActivationDecision(
            partner_name=partner,
            tenant_id=tenant,
            stage=stage.value,
            founder_id="founder-operator",
            environment="controlled-pilot",
            commit_sha="e164fdda1b190b031115007a5e703267b8aef016",
            starts_at=now.isoformat(),
            expires_at=(now + timedelta(days=14)).isoformat(),
            allowed_categories=categories,
        )

    def test_readiness_never_self_authorizes_activation(self) -> None:
        with self.assertRaisesRegex(PermissionError, "evidence is incomplete"):
            self.service.activate(self.decision(), acceptance=AcceptanceStub(False))
        self.assertFalse(self.service.status("velani-wholesale-pilot")["active"])

    def test_velani_synthetic_stage_keeps_every_real_boundary_closed(self) -> None:
        status = self.service.activate(self.decision(), acceptance=AcceptanceStub(True))
        self.assertTrue(status["active"])
        self.assertEqual(status["allowed_categories"], [])
        self.assertFalse(status["customer_records_authorized"])
        self.assertFalse(status["external_publishing_authorized"])
        self.assertFalse(status["real_data_learning_authorized"])
        self.assertFalse(status["billing_enabled"])

    def test_limited_stage_allows_only_enumerated_categories(self) -> None:
        category = ActivatedDataCategory.OWNED_PRODUCT_CATALOGUE.value
        status = self.service.activate(
            self.decision(
                stage=ActivationStage.LIMITED_REAL_BUSINESS,
                categories=(category,),
            ),
            acceptance=AcceptanceStub(True),
        )
        self.assertEqual(status["allowed_categories"], [category])
        self.assertTrue(
            self.service.authorize_category(
                tenant_id="velani-wholesale-pilot", category=category
            )
        )
        self.assertFalse(
            self.service.authorize_category(
                tenant_id="velani-wholesale-pilot", category="customer_records"
            )
        )

    def test_strand_cannot_reuse_velani_activation(self) -> None:
        with self.assertRaisesRegex(PermissionError, "Velani"):
            self.service.activate(
                self.decision(
                    partner="Strand Auto Parts", tenant="strand-auto-parts-pilot"
                ),
                acceptance=AcceptanceStub(True),
            )

    def test_founder_suspension_is_immediate_and_immutable(self) -> None:
        self.service.activate(self.decision(), acceptance=AcceptanceStub(True))
        status = self.service.suspend(
            tenant_id="velani-wholesale-pilot",
            founder_id="founder-operator",
            reason="Controlled rollback rehearsal",
        )
        self.assertFalse(status["active"])
        with self.database.connection() as connection:
            count = connection.execute(
                "SELECT COUNT(*) FROM pilot_activation_events"
            ).fetchone()[0]
        self.assertEqual(count, 2)


if __name__ == "__main__":
    unittest.main()
