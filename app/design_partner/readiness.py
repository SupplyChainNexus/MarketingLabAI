"""Deterministic Founder Design Partner readiness assessment."""

from __future__ import annotations


class DesignPartnerReadinessEvaluator:
    """Assess evidence without activating a real-data pilot."""

    APPROVED_CANDIDATE = "Strand Auto Parts"

    REQUIRED_GATES = (
        "founder_approval",
        "privacy_choices_complete",
        "external_identity_ready",
        "backup_recovery_rehearsed",
        "support_owner_assigned",
        "data_boundary_accepted",
    )

    def evaluate(self, *, partner_name: str, evidence: dict[str, bool]) -> dict:
        if not isinstance(partner_name, str) or not partner_name.strip():
            raise ValueError("partner_name is required.")
        if partner_name.strip().casefold() != self.APPROVED_CANDIDATE.casefold():
            raise ValueError("The Founder Design Partner candidate is not approved.")
        if not isinstance(evidence, dict):
            raise TypeError("evidence must be an object.")
        unsupported = set(evidence) - set(self.REQUIRED_GATES)
        if unsupported:
            raise ValueError(
                "Unsupported readiness evidence: "
                + ", ".join(sorted(unsupported))
                + "."
            )
        checks = []
        for name in self.REQUIRED_GATES:
            value = evidence.get(name, False)
            if not isinstance(value, bool):
                raise TypeError(f"{name} must be a boolean.")
            checks.append({"name": name, "passed": value})
        ready_for_activation_decision = all(item["passed"] for item in checks)
        return {
            "partner_name": self.APPROVED_CANDIDATE,
            "partner_kind": "founder_design_partner",
            "account_entitlement": {
                "full_feature_access": True,
                "billing_enabled": False,
                "commercial_tier": "founder_design_partner_free",
            },
            "checks": checks,
            "blockers": [item["name"] for item in checks if not item["passed"]],
            "ready_for_activation_decision": ready_for_activation_decision,
            "real_data_activation_authorized": False,
            "pilot_status": "founder_frozen",
            "market_validation_claimed": False,
        }
