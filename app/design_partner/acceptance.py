"""Partner-specific, evidence-bound synthetic acceptance assessment."""

from __future__ import annotations

from app.database.connection import SQLiteDatabase
from app.design_partner.privacy import PilotPrivacyPolicy
from app.design_partner.registry import FounderDesignPartnerRegistry
from app.operations.configuration import PilotConfiguration
from app.operations.readiness_evidence import ReadinessEvidenceRepository
from app.operations.release_gate import PilotReleaseGate


class DesignPartnerAcceptanceEvaluator:
    """Assess controlled acceptance without authorizing real customer activity."""

    REQUIRED_SCENARIOS = (
        "authenticated_signup_and_session",
        "privacy_and_data_boundary",
        "tenant_isolation",
        "governed_strategy_workflow",
        "governed_generation_and_compliance",
        "logout_recovery_and_support",
        "browser_accessibility_and_usability",
    )

    def __init__(self, config: PilotConfiguration, database: SQLiteDatabase) -> None:
        self.config = config
        self.database = database
        self.repository = ReadinessEvidenceRepository(database)

    @classmethod
    def evidence_name(cls, tenant_id: str, scenario: str) -> str:
        if scenario not in cls.REQUIRED_SCENARIOS:
            raise ValueError(f"Unsupported acceptance scenario: {scenario}.")
        return f"design_partner_acceptance:{tenant_id}:{scenario}"

    def evaluate(self, *, partner_name: str, tenant_id: str) -> dict[str, object]:
        partner = FounderDesignPartnerRegistry().get_by_name(partner_name)
        if partner.tenant_id != tenant_id:
            raise PermissionError(
                "The authenticated tenant does not match the partner."
            )

        release = PilotReleaseGate(self.config, self.database).evaluate()
        prerequisite_ready = release.ready_for_founder_activation_assessment
        names = tuple(
            self.evidence_name(tenant_id, scenario)
            for scenario in self.REQUIRED_SCENARIOS
        )
        evidence = (
            self.repository.current_passes(
                names,
                environment=self.config.environment,
                commit_sha=self.config.deployment_commit,
            )
            if self.config.deployment_commit != "unrecorded"
            else {}
        )
        privacy_current = self._privacy_acceptance_current(tenant_id)
        scenarios = tuple(
            {
                "name": scenario,
                "passed": evidence.get(self.evidence_name(tenant_id, scenario), False),
                "evidence": "current immutable synthetic-rehearsal evidence",
            }
            for scenario in self.REQUIRED_SCENARIOS
        )
        blockers = []
        if not prerequisite_ready:
            blockers.append("production_security_and_operational_prerequisites")
        if not privacy_current:
            blockers.append("current_partner_privacy_acceptance")
        blockers.extend(item["name"] for item in scenarios if not item["passed"])
        accepted = not blockers
        return {
            "partner_name": partner.partner_name,
            "tenant_id": partner.tenant_id,
            "prerequisite_readiness_passed": prerequisite_ready,
            "privacy_acceptance_current": privacy_current,
            "scenarios": list(scenarios),
            "blockers": blockers,
            "acceptance_rehearsal_passed": accepted,
            "ready_for_founder_activation_assessment": accepted,
            "synthetic_rehearsal_authorized": prerequisite_ready,
            "real_data_activation_authorized": False,
            "external_invitations_authorized": False,
            "billing_enabled": False,
            "pilot_status": "real_data_activation_frozen",
            "market_validation_claimed": False,
        }

    def _privacy_acceptance_current(self, tenant_id: str) -> bool:
        with self.database.connection() as connection:
            row = connection.execute(
                """
                SELECT 1 FROM pilot_privacy_acceptances
                WHERE tenant_id = ? AND notice_version = ? AND boundary_version = ?
                LIMIT 1
                """,
                (
                    tenant_id,
                    PilotPrivacyPolicy.NOTICE_VERSION,
                    PilotPrivacyPolicy.BOUNDARY_VERSION,
                ),
            ).fetchone()
        return row is not None
