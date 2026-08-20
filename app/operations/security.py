"""Deterministic production identity and security readiness evidence."""

from __future__ import annotations

from dataclasses import asdict, dataclass

from app.database.connection import SQLiteDatabase
from app.operations.configuration import PilotConfiguration


@dataclass(frozen=True, slots=True)
class SecurityCheck:
    name: str
    passed: bool
    evidence: str


@dataclass(frozen=True, slots=True)
class ProductionSecurityReport:
    checks: tuple[SecurityCheck, ...]

    @property
    def production_identity_security_ready(self) -> bool:
        return all(check.passed for check in self.checks)

    def to_dict(self) -> dict:
        return {
            "checks": [asdict(check) for check in self.checks],
            "blockers": [check.name for check in self.checks if not check.passed],
            "production_identity_security_ready": (
                self.production_identity_security_ready
            ),
            "ready_for_founder_activation_assessment": (
                self.production_identity_security_ready
            ),
            "synthetic_rehearsal_authorized": True,
            "real_data_activation_authorized": False,
            "pilot_status": "real_data_activation_frozen",
        }


class ProductionSecurityEvaluator:
    """Evaluate deployable controls without activating customers or real data."""

    EXTERNAL_EVIDENCE = (
        "api_key_restricted",
        "oauth_testing_audience",
        "authorized_domains_reviewed",
        "identity_audit_logging_enabled",
        "invalid_token_rehearsed",
        "session_revocation_rehearsed",
        "tenant_isolation_rehearsed",
    )

    def __init__(
        self,
        config: PilotConfiguration,
        database: SQLiteDatabase,
        *,
        external_evidence: dict[str, bool] | None = None,
    ) -> None:
        if not isinstance(config, PilotConfiguration):
            raise TypeError("config must be a PilotConfiguration.")
        if not isinstance(database, SQLiteDatabase):
            raise TypeError("database must be a SQLiteDatabase.")
        self.config = config
        self.database = database
        evidence = dict(external_evidence or {})
        unsupported = set(evidence) - set(self.EXTERNAL_EVIDENCE)
        if unsupported:
            raise ValueError(
                "Unsupported security evidence: " + ", ".join(sorted(unsupported))
            )
        if any(not isinstance(value, bool) for value in evidence.values()):
            raise TypeError("External security evidence values must be booleans.")
        self.external_evidence = evidence

    def evaluate(self) -> ProductionSecurityReport:
        self.database.initialise()
        tables = set(self.database.table_names())
        approved_tenants = {
            "strand-auto-parts-pilot",
            "velani-wholesale-pilot",
        }
        checks = (
            SecurityCheck(
                "google_identity_selected",
                self.config.identity_provider == "google-cloud-identity-platform",
                "selected provider must remain Google Cloud Identity Platform",
            ),
            SecurityCheck(
                "production_tls",
                self.config.public_origin.startswith("https://")
                or self.config.trust_proxy_tls,
                "HTTPS origin or explicitly trusted TLS proxy",
            ),
            SecurityCheck(
                "recent_authentication",
                300 <= self.config.google_max_auth_age_seconds <= 3600,
                "Google auth_time maximum age is bounded to one hour",
            ),
            SecurityCheck(
                "bounded_session_idle_expiry",
                self.config.session_idle_ttl_seconds == 900,
                "server session idle expiry is exactly 15 minutes",
            ),
            SecurityCheck(
                "bounded_session_absolute_expiry",
                self.config.session_absolute_ttl_seconds == 3600,
                "server session absolute expiry is exactly 60 minutes",
            ),
            SecurityCheck(
                "bounded_requests",
                1024 <= self.config.max_request_bytes <= 10485760,
                "request bodies have a configured upper bound",
            ),
            SecurityCheck(
                "approved_invitations",
                approved_tenants.issubset(self.config.founder_invitation_hashes),
                "both approved tenant invitation hashes are configured",
            ),
            SecurityCheck(
                "revocable_sessions",
                "pilot_sessions" in tables,
                "hashed tenant-bound server sessions are persisted",
            ),
            SecurityCheck(
                "authorization_audit",
                "authorization_audit_events" in tables,
                "allowed and denied tenant decisions are auditable",
            ),
            SecurityCheck(
                "privacy_acceptance",
                "pilot_privacy_acceptances" in tables,
                "versioned tenant privacy acceptance evidence is available",
            ),
            SecurityCheck(
                "real_data_freeze",
                not self.config.allow_real_customer_data,
                "real-data activation remains false",
            ),
            *tuple(
                SecurityCheck(
                    name,
                    self.external_evidence.get(name, False),
                    "explicit controlled-environment rehearsal evidence",
                )
                for name in self.EXTERNAL_EVIDENCE
            ),
        )
        return ProductionSecurityReport(checks)
