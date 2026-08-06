"""Founder Design Partner readiness contracts."""

from app.design_partner.acceptance import DesignPartnerAcceptanceEvaluator
from app.design_partner.activation import (
    ActivatedDataCategory,
    ActivationStage,
    ControlledActivationService,
    FounderActivationDecision,
)
from app.design_partner.privacy import (
    DataBoundaryDecision,
    PilotDataCategory,
    PilotPrivacyPolicy,
)
from app.design_partner.readiness import DesignPartnerReadinessEvaluator
from app.design_partner.registry import (
    APPROVED_FOUNDER_DESIGN_PARTNERS,
    FounderDesignPartner,
    FounderDesignPartnerRegistry,
)
from app.design_partner.signup import (
    FounderDesignPartnerSignupService,
    FounderSignupResult,
    SignupConflictError,
)

__all__ = [
    "APPROVED_FOUNDER_DESIGN_PARTNERS",
    "DesignPartnerReadinessEvaluator",
    "DesignPartnerAcceptanceEvaluator",
    "ActivatedDataCategory",
    "ActivationStage",
    "ControlledActivationService",
    "FounderActivationDecision",
    "DataBoundaryDecision",
    "FounderDesignPartner",
    "FounderDesignPartnerRegistry",
    "FounderDesignPartnerSignupService",
    "FounderSignupResult",
    "PilotDataCategory",
    "PilotPrivacyPolicy",
    "SignupConflictError",
]
