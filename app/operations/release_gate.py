"""Evidence-based synthetic and private-pilot release decision."""

from __future__ import annotations

from dataclasses import dataclass

from app.database.connection import SQLiteDatabase
from app.operations.configuration import PilotConfiguration


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
            "real_data_activation_authorized": False,
            "customer_pilot_status": "real_data_activation_frozen",
        }


class PilotReleaseGate:
    def __init__(self, config: PilotConfiguration, database: SQLiteDatabase) -> None:
        self.config = config
        self.database = database

    def evaluate(self) -> ReleaseGateReport:
        self.database.initialise()
        migration_versions = self._migration_versions()
        checks = (
            GateCheck(
                "database_integrity",
                self.database.integrity_check() == "ok",
                "PRAGMA integrity_check",
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
        return ReleaseGateReport(
            checks=checks,
            synthetic_pilot_ready=all(item.passed for item in checks),
            private_customer_pilot_authorized=False,
        )

    def _migration_versions(self) -> set[int]:
        with self.database.connection() as connection:
            rows = connection.execute(
                "SELECT version FROM schema_migrations"
            ).fetchall()
        return {int(row[0]) for row in rows}
