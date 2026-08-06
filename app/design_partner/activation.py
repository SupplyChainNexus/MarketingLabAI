"""Founder-authorized, tenant-bound controlled activation decisions."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum
from uuid import uuid4

from app.database.connection import SQLiteDatabase
from app.design_partner.acceptance import DesignPartnerAcceptanceEvaluator
from app.design_partner.registry import FounderDesignPartnerRegistry


class ActivationStage(StrEnum):
    EXTERNAL_SYNTHETIC = "external_synthetic_acceptance"
    LIMITED_REAL_BUSINESS = "limited_real_business_data"


class ActivatedDataCategory(StrEnum):
    PUBLIC_COMPANY_PROFILE = "public_company_profile"
    PUBLIC_CONTACT_INFORMATION = "public_contact_information"
    OWNED_PRODUCT_CATALOGUE = "owned_product_catalogue"
    OWNED_PRODUCT_IMAGES = "owned_product_images"
    OWNED_BRAND_ASSETS = "owned_brand_assets"
    NON_PERSONAL_TARGET_MARKETS = "non_personal_target_markets"
    APPROVED_MARKETING_OBJECTIVES = "approved_marketing_objectives"
    APPROVED_MARKETING_BUDGET = "approved_marketing_budget"
    CAMPAIGN_DRAFTS = "campaign_drafts"
    STRUCTURED_PRODUCT_FEEDBACK = "structured_product_feedback"


@dataclass(frozen=True, slots=True)
class FounderActivationDecision:
    partner_name: str
    tenant_id: str
    stage: str
    founder_id: str
    environment: str
    commit_sha: str
    starts_at: str
    expires_at: str
    allowed_categories: tuple[str, ...] = ()
    decision_id: str = ""

    def __post_init__(self) -> None:
        partner = FounderDesignPartnerRegistry().get_by_name(self.partner_name)
        if partner.tenant_id != self.tenant_id:
            raise PermissionError("Activation partner and tenant do not match.")
        stage = ActivationStage(self.stage)
        categories = tuple(dict.fromkeys(self.allowed_categories))
        for category in categories:
            ActivatedDataCategory(category)
        if stage is ActivationStage.EXTERNAL_SYNTHETIC and categories:
            raise ValueError("Synthetic acceptance cannot authorize real categories.")
        start = datetime.fromisoformat(self.starts_at.replace("Z", "+00:00"))
        expiry = datetime.fromisoformat(self.expires_at.replace("Z", "+00:00"))
        if start.tzinfo is None or expiry.tzinfo is None or expiry <= start:
            raise ValueError(
                "Activation timestamps must be ordered and timezone-aware."
            )
        if not self.founder_id.strip():
            raise ValueError("founder_id is required.")
        object.__setattr__(self, "stage", stage.value)
        object.__setattr__(self, "allowed_categories", categories)
        object.__setattr__(self, "starts_at", start.astimezone(UTC).isoformat())
        object.__setattr__(self, "expires_at", expiry.astimezone(UTC).isoformat())
        object.__setattr__(self, "decision_id", self.decision_id or str(uuid4()))


class ControlledActivationService:
    """Record explicit decisions and enforce the narrowest current scope."""

    FIRST_PARTNER = "Velani Wholesale"
    FIRST_TENANT = "velani-wholesale-pilot"

    def __init__(self, database: SQLiteDatabase) -> None:
        self.database = database
        self.database.initialise()

    def activate(
        self,
        decision: FounderActivationDecision,
        *,
        acceptance: DesignPartnerAcceptanceEvaluator,
    ) -> dict[str, object]:
        if (
            decision.partner_name != self.FIRST_PARTNER
            or decision.tenant_id != self.FIRST_TENANT
        ):
            raise PermissionError(
                "Only the founder-selected Velani tenant may activate first."
            )
        report = acceptance.evaluate(
            partner_name=decision.partner_name, tenant_id=decision.tenant_id
        )
        if not report["ready_for_founder_activation_assessment"]:
            raise PermissionError("Current partner acceptance evidence is incomplete.")
        with self.database.transaction() as connection:
            connection.execute(
                """
                INSERT INTO pilot_activation_events (
                    event_id, decision_id, tenant_id, partner_name, stage,
                    founder_id, environment, commit_sha, allowed_categories_json,
                    starts_at, expires_at, action, reason, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'activate', '', ?)
                """,
                (
                    str(uuid4()),
                    decision.decision_id,
                    decision.tenant_id,
                    decision.partner_name,
                    decision.stage,
                    decision.founder_id,
                    decision.environment,
                    decision.commit_sha,
                    __import__("json").dumps(decision.allowed_categories),
                    decision.starts_at,
                    decision.expires_at,
                    datetime.now(UTC).isoformat(),
                ),
            )
        return self.status(decision.tenant_id)

    def suspend(
        self, *, tenant_id: str, founder_id: str, reason: str
    ) -> dict[str, object]:
        current = self._latest_activation(tenant_id)
        if current is None:
            raise LookupError("No activation exists for this tenant.")
        if not founder_id.strip() or not reason.strip():
            raise ValueError("Founder identity and suspension reason are required.")
        with self.database.transaction() as connection:
            connection.execute(
                """INSERT INTO pilot_activation_events (
                    event_id, decision_id, tenant_id, partner_name, stage,
                    founder_id, environment, commit_sha, allowed_categories_json,
                    starts_at, expires_at, action, reason, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'suspend', ?, ?)""",
                (
                    str(uuid4()),
                    current["decision_id"],
                    tenant_id,
                    current["partner_name"],
                    current["stage"],
                    founder_id,
                    current["environment"],
                    current["commit_sha"],
                    current["allowed_categories_json"],
                    current["starts_at"],
                    current["expires_at"],
                    reason.strip(),
                    datetime.now(UTC).isoformat(),
                ),
            )
        return self.status(tenant_id)

    def authorize_category(self, *, tenant_id: str, category: str) -> bool:
        status = self.status(tenant_id)
        return bool(status["active"] and category in status["allowed_categories"])

    def status(self, tenant_id: str) -> dict[str, object]:
        row = self._latest_event(tenant_id)
        active = bool(
            row
            and row["action"] == "activate"
            and datetime.fromisoformat(row["starts_at"])
            <= datetime.now(UTC)
            < datetime.fromisoformat(row["expires_at"])
        )
        categories = (
            __import__("json").loads(row["allowed_categories_json"]) if row else []
        )
        return {
            "tenant_id": tenant_id,
            "active": active,
            "stage": row["stage"] if row else "frozen",
            "allowed_categories": categories if active else [],
            "public_signup_authorized": False,
            "billing_enabled": False,
            "external_publishing_authorized": False,
            "real_data_learning_authorized": False,
            "customer_records_authorized": False,
        }

    def _latest_event(self, tenant_id: str):
        with self.database.connection() as connection:
            return connection.execute(
                "SELECT * FROM pilot_activation_events WHERE tenant_id = ? ORDER BY created_at DESC LIMIT 1",
                (tenant_id,),
            ).fetchone()

    def _latest_activation(self, tenant_id: str):
        with self.database.connection() as connection:
            return connection.execute(
                "SELECT * FROM pilot_activation_events WHERE tenant_id = ? AND action = 'activate' ORDER BY created_at DESC LIMIT 1",
                (tenant_id,),
            ).fetchone()
