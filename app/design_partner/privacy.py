"""Default-deny privacy and data-boundary controls for the synthetic pilot."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from enum import StrEnum

from app.design_partner.registry import FounderDesignPartnerRegistry


class PilotDataCategory(StrEnum):
    """Data categories evaluated before a pilot workflow accepts content."""

    SYNTHETIC_BUSINESS_PROFILE = "synthetic_business_profile"
    SYNTHETIC_CUSTOMER_PERSONA = "synthetic_customer_persona"
    SYNTHETIC_PRODUCT_CATALOGUE = "synthetic_product_catalogue"
    SYNTHETIC_CAMPAIGN_MATERIAL = "synthetic_campaign_material"
    SYNTHETIC_OPERATIONAL_METADATA = "synthetic_operational_metadata"
    PERSONAL_DATA = "personal_data"
    EMPLOYEE_DATA = "employee_data"
    CUSTOMER_RECORDS = "customer_records"
    SUPPLIER_RECORDS = "supplier_records"
    TRANSACTION_DATA = "transaction_data"
    CONFIDENTIAL_BUSINESS_DATA = "confidential_business_data"
    CREDENTIALS_AND_SECRETS = "credentials_and_secrets"
    EXTERNAL_PUBLISHING_PAYLOAD = "external_publishing_payload"
    REAL_OUTCOME_LEARNING = "real_outcome_learning"


@dataclass(frozen=True, slots=True)
class DataBoundaryDecision:
    tenant_id: str
    category: str
    allowed: bool
    reason: str
    policy_version: str
    synthetic_rehearsal_authorized: bool = True
    real_data_activation_authorized: bool = False

    def to_dict(self) -> dict:
        return asdict(self)


class PilotPrivacyPolicy:
    """Versioned synthetic-pilot policy; readiness never grants activation."""

    NOTICE_VERSION = "pilot-privacy-notice-v1"
    BOUNDARY_VERSION = "synthetic-data-boundary-v1"
    SYNTHETIC_RETENTION_DAYS = 30
    SYNTHETIC_DELETION_SLA_DAYS = 7
    REAL_DATA_RETENTION_DAYS = None
    REAL_DATA_DELETION_SLA_DAYS = None

    ALLOWED_SYNTHETIC_CATEGORIES = frozenset(
        {
            PilotDataCategory.SYNTHETIC_BUSINESS_PROFILE,
            PilotDataCategory.SYNTHETIC_CUSTOMER_PERSONA,
            PilotDataCategory.SYNTHETIC_PRODUCT_CATALOGUE,
            PilotDataCategory.SYNTHETIC_CAMPAIGN_MATERIAL,
            PilotDataCategory.SYNTHETIC_OPERATIONAL_METADATA,
        }
    )
    PROHIBITED_CATEGORIES = frozenset(
        set(PilotDataCategory) - set(ALLOWED_SYNTHETIC_CATEGORIES)
    )

    def authorize(self, *, tenant_id: str, category: str) -> DataBoundaryDecision:
        partner = FounderDesignPartnerRegistry().get_by_tenant(tenant_id)
        try:
            parsed = PilotDataCategory(category)
        except ValueError as error:
            raise ValueError("Unsupported pilot data category.") from error
        allowed = parsed in self.ALLOWED_SYNTHETIC_CATEGORIES
        reason = (
            "Invented synthetic data is allowed for controlled rehearsal."
            if allowed
            else "This category remains prohibited while real-data activation is frozen."
        )
        return DataBoundaryDecision(
            tenant_id=partner.tenant_id,
            category=parsed.value,
            allowed=allowed,
            reason=reason,
            policy_version=self.BOUNDARY_VERSION,
        )

    def pack(self, *, tenant_id: str) -> dict:
        partner = FounderDesignPartnerRegistry().get_by_tenant(tenant_id)
        return {
            "partner_name": partner.partner_name,
            "tenant_id": partner.tenant_id,
            "notice_version": self.NOTICE_VERSION,
            "boundary_version": self.BOUNDARY_VERSION,
            "allowed_categories": sorted(
                item.value for item in self.ALLOWED_SYNTHETIC_CATEGORIES
            ),
            "prohibited_categories": sorted(
                item.value for item in self.PROHIBITED_CATEGORIES
            ),
            "retention": {
                "synthetic_records_days": self.SYNTHETIC_RETENTION_DAYS,
                "synthetic_deletion_sla_days": self.SYNTHETIC_DELETION_SLA_DAYS,
                "real_data_records_days": self.REAL_DATA_RETENTION_DAYS,
                "real_data_deletion_sla_days": self.REAL_DATA_DELETION_SLA_DAYS,
            },
            "synthetic_rehearsal_authorized": True,
            "real_data_activation_authorized": False,
            "pilot_status": "real_data_activation_frozen",
        }
