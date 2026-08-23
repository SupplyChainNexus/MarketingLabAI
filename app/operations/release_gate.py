"""Evidence-based synthetic and private-pilot release decision."""

from __future__ import annotations

from dataclasses import dataclass

from app.database.connection import SQLiteDatabase
from app.operations.configuration import PilotConfiguration
from app.operations.operational_readiness import OperationalReadinessEvaluator
from app.operations.readiness_evidence import ReadinessEvidenceRepository
from app.operations.security import ProductionSecurityEvaluator


@dataclass(slots=True, frozen=True)
class GateCheck:
    name: str
    passed: bool
    evidence: str


@dataclass(slots=True, frozen=True)
class ReleaseGateReport:
    checks: tuple[GateCheck, ...]
    synthetic_pilot_ready: bool
    private_customer_pilot_authorized: bool
    security: dict
    operations: dict

    @property
    def ready_for_founder_activation_assessment(self) -> bool:
        return (
            self.synthetic_pilot_ready
            and bool(self.security.get("production_identity_security_ready"))
            and bool(self.operations.get("recovery_monitoring_support_ready"))
        )

    def to_dict(self) -> dict[str, object]:
        return {
            "checks": [
                {"name": item.name, "passed": item.passed, "evidence": item.evidence}
                for item in self.checks
            ],
            "synthetic_pilot_ready": self.synthetic_pilot_ready,
            "engineering_development_authorized": True,
            "synthetic_rehearsal_authorized": True,
            "private_customer_pilot_authorized": False,
            "ready_for_founder_activation_assessment": (
                self.ready_for_founder_activation_assessment
            ),
            "real_data_activation_authorized": False,
            "customer_pilot_status": "real_data_activation_frozen",
            "production_security": self.security,
            "operational_readiness": self.operations,
        }


class PilotReleaseGate:
    def __init__(self, config: PilotConfiguration, database: SQLiteDatabase) -> None:
        self.config = config
        self.database = database

    def evaluate(self) -> ReleaseGateReport:
        schema_ready = self.database.schema_is_ready()
        migration_versions = self._migration_versions() if schema_ready else set()
        checks = (
            GateCheck(
                "database_schema_ready",
                schema_ready,
                "canonical schema and migrations must exist before readiness",
            ),
            GateCheck(
                "database_integrity",
                schema_ready and self.database.integrity_check() == "ok",
                f"{self.config.persistence_backend} integrity check",
            ),
            GateCheck(
                "session_schema", 13 in migration_versions, "schema migration 13"
            ),
            GateCheck(
                "tls",
                self.config.public_origin.startswith("https://")
                or self.config.trust_proxy_tls,
                "HTTPS or trusted proxy",
            ),
            GateCheck(
                "external_identity",
                self.config.identity_provider != "synthetic",
                "configured external identity adapter",
            ),
            GateCheck(
                "founder_invitations",
                {
                    "strand-auto-parts-pilot",
                    "velani-wholesale-pilot",
                }.issubset(self.config.founder_invitation_hashes),
                "both approved invitation hashes configured",
            ),
            GateCheck(
                "secrets",
                len(self.config.session_secret) >= 32,
                "environment-managed session secret",
            ),
            GateCheck(
                "rate_limit",
                self.config.rate_limit_requests > 0,
                "positive request limit",
            ),
            GateCheck(
                "customer_data_freeze",
                not self.config.allow_real_customer_data,
                "real-data activation freeze retained",
            ),
        )
        repository = (
            ReadinessEvidenceRepository(self.database) if schema_ready else None
        )
        security_evidence = (
            repository.current_passes(
                ProductionSecurityEvaluator.EXTERNAL_EVIDENCE,
                environment=self.config.environment,
                commit_sha=self.config.deployment_commit,
            )
            if repository is not None and self.config.deployment_commit != "unrecorded"
            else {}
        )
        security = (
            ProductionSecurityEvaluator(
                self.config,
                self.database,
                external_evidence=security_evidence,
            )
            .evaluate()
            .to_dict()
        )
        report = ReleaseGateReport(
            checks=checks,
            synthetic_pilot_ready=all(item.passed for item in checks),
            private_customer_pilot_authorized=False,
            security=security,
            operations=OperationalReadinessEvaluator(
                self.config, self.database, repository
            )
            .evaluate()
            .to_dict(),
        )
        return report

    def security_evidence(self) -> dict:
        """Return production-security evidence without changing activation."""

        schema_ready = self.database.schema_is_ready()
        repository = (
            ReadinessEvidenceRepository(self.database) if schema_ready else None
        )
        return (
            ProductionSecurityEvaluator(
                self.config,
                self.database,
                external_evidence=(
                    repository.current_passes(
                        ProductionSecurityEvaluator.EXTERNAL_EVIDENCE,
                        environment=self.config.environment,
                        commit_sha=self.config.deployment_commit,
                    )
                    if repository is not None
                    and self.config.deployment_commit != "unrecorded"
                    else {}
                ),
            )
            .evaluate()
            .to_dict()
        )

    def _migration_versions(self) -> set[int]:
        with self.database.connection() as connection:
            rows = connection.execute(
                "SELECT version FROM schema_migrations"
            ).fetchall()
        return {int(row[0]) for row in rows}
