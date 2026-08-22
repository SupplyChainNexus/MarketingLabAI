"""Recovery, monitoring, and support readiness without customer activation."""

from __future__ import annotations

from dataclasses import asdict, dataclass

from app.database.connection import SQLiteDatabase
from app.operations.configuration import PilotConfiguration
from app.operations.readiness_evidence import ReadinessEvidenceRepository


@dataclass(frozen=True, slots=True)
class OperationalCheck:
    name: str
    passed: bool
    evidence: str


@dataclass(frozen=True, slots=True)
class OperationalReadinessReport:
    checks: tuple[OperationalCheck, ...]

    @property
    def recovery_monitoring_support_ready(self) -> bool:
        return all(item.passed for item in self.checks)

    def to_dict(self) -> dict:
        return {
            "checks": [asdict(item) for item in self.checks],
            "blockers": [item.name for item in self.checks if not item.passed],
            "recovery_monitoring_support_ready": (
                self.recovery_monitoring_support_ready
            ),
            "ready_for_founder_activation_assessment": (
                self.recovery_monitoring_support_ready
            ),
            "synthetic_rehearsal_authorized": True,
            "real_data_activation_authorized": False,
            "pilot_status": "real_data_activation_frozen",
        }


class OperationalReadinessEvaluator:
    REQUIRED_EVIDENCE = (
        "backup_created_and_verified",
        "restore_rehearsed",
        "rollback_rehearsed",
        "readiness_alert_rehearsed",
        "authentication_alert_rehearsed",
        "rate_limit_alert_rehearsed",
        "database_alert_rehearsed",
        "incident_response_rehearsed",
        "support_owner_assigned",
        "support_response_targets_approved",
    )

    def __init__(
        self,
        config: PilotConfiguration,
        database: SQLiteDatabase,
        repository: ReadinessEvidenceRepository | None = None,
    ) -> None:
        self.config = config
        self.database = database
        self.repository = repository

    def evaluate(self) -> OperationalReadinessReport:
        schema_ready = self.database.schema_is_ready()
        repository = self.repository
        if schema_ready and repository is None:
            repository = ReadinessEvidenceRepository(
                self.database, ensure_initialised=False
            )
        evidence = (
            repository.current_passes(
                self.REQUIRED_EVIDENCE,
                environment=self.config.environment,
                commit_sha=self.config.deployment_commit,
            )
            if schema_ready
            and repository is not None
            and self.config.deployment_commit != "unrecorded"
            else {}
        )
        checks = (
            OperationalCheck(
                "deployment_commit_recorded",
                self.config.deployment_commit != "unrecorded",
                "readiness evidence is bound to the deployed Git commit",
            ),
            OperationalCheck(
                "readiness_evidence_schema",
                schema_ready,
                "immutable readiness evidence is persisted under migration 17",
            ),
            *tuple(
                OperationalCheck(
                    name,
                    evidence.get(name, False),
                    "current passed evidence for this environment and commit",
                )
                for name in self.REQUIRED_EVIDENCE
            ),
            OperationalCheck(
                "real_data_freeze",
                not self.config.allow_real_customer_data,
                "real-data activation remains false",
            ),
        )
        return OperationalReadinessReport(checks)
