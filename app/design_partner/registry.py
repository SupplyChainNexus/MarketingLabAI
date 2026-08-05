"""Approved Founder Design Partner registry for controlled signup."""

from __future__ import annotations

from dataclasses import asdict, dataclass


@dataclass(frozen=True, slots=True)
class FounderDesignPartner:
    """Founder-approved partner identity without customer-data authority."""

    partner_name: str
    tenant_id: str
    commercial_tier: str = "founder_design_partner_free"
    full_feature_access: bool = True
    billing_enabled: bool = False
    synthetic_only: bool = True
    real_data_activation_authorized: bool = False

    def __post_init__(self) -> None:
        if not self.partner_name.strip():
            raise ValueError("partner_name is required.")
        if not self.tenant_id.strip():
            raise ValueError("tenant_id is required.")
        if self.billing_enabled:
            raise ValueError("Founder Design Partner billing must remain disabled.")
        if not self.synthetic_only or self.real_data_activation_authorized:
            raise ValueError("Registry provisioning must remain synthetic-only.")

    def to_dict(self) -> dict:
        return asdict(self)


APPROVED_FOUNDER_DESIGN_PARTNERS = (
    FounderDesignPartner(
        partner_name="Strand Auto Parts",
        tenant_id="strand-auto-parts-pilot",
    ),
    FounderDesignPartner(
        partner_name="Velani Wholesale",
        tenant_id="velani-wholesale-pilot",
    ),
)


class FounderDesignPartnerRegistry:
    """Resolve founder-approved partners by exact name or tenant identity."""

    def __init__(self) -> None:
        self._by_name = {
            partner.partner_name.casefold(): partner
            for partner in APPROVED_FOUNDER_DESIGN_PARTNERS
        }
        self._by_tenant = {
            partner.tenant_id: partner for partner in APPROVED_FOUNDER_DESIGN_PARTNERS
        }

    def get_by_name(self, partner_name: str) -> FounderDesignPartner:
        if not isinstance(partner_name, str) or not partner_name.strip():
            raise ValueError("partner_name is required.")
        partner = self._by_name.get(partner_name.strip().casefold())
        if partner is None:
            raise ValueError("The Founder Design Partner candidate is not approved.")
        return partner

    def get_by_tenant(self, tenant_id: str) -> FounderDesignPartner:
        if not isinstance(tenant_id, str) or not tenant_id.strip():
            raise ValueError("tenant_id is required.")
        partner = self._by_tenant.get(tenant_id.strip())
        if partner is None:
            raise ValueError("The Founder Design Partner tenant is not approved.")
        return partner

    def list(self) -> list[FounderDesignPartner]:
        return list(APPROVED_FOUNDER_DESIGN_PARTNERS)
