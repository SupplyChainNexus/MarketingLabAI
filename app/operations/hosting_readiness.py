"""Default-deny readiness checks for controlled external hosting."""

from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass
from typing import Mapping


class HostingConfigurationError(ValueError):
    """Raised when a hosting value is malformed or unbounded."""


@dataclass(slots=True, frozen=True)
class HostingCheck:
    name: str
    passed: bool
    evidence: str


@dataclass(slots=True, frozen=True)
class ControlledHostingReport:
    checks: tuple[HostingCheck, ...]
    cloud_build_authorized: bool = False
    cloud_deployment_authorized: bool = False
    external_invitation_authorized: bool = False
    real_data_activation_authorized: bool = False

    @property
    def engineering_ready(self) -> bool:
        return all(check.passed for check in self.checks)

    def to_dict(self) -> dict[str, object]:
        return {
            "checks": [asdict(check) for check in self.checks],
            "engineering_ready": self.engineering_ready,
            "cloud_build_authorized": self.cloud_build_authorized,
            "cloud_deployment_authorized": self.cloud_deployment_authorized,
            "external_invitation_authorized": self.external_invitation_authorized,
            "real_data_activation_authorized": self.real_data_activation_authorized,
            "status": "founder_deployment_decision_required",
        }


@dataclass(slots=True, frozen=True)
class ControlledHostingConfiguration:
    project_id: str
    region: str
    service_name: str
    deployment_commit: str
    persistence_backend: str
    database_secret_reference: str
    cloud_sql_instance: str
    max_instances: int
    min_instances: int
    concurrency: int
    cpu: int
    memory_mib: int
    monthly_budget_zar: int
    secret_bindings: dict[str, str]
    durable_adapter_verified: bool
    durable_adapter_evidence_reference: str

    REQUIRED_SECRETS = frozenset(
        {
            "MLAI_DATABASE_URL",
            "MLAI_SESSION_SECRET",
            "MLAI_FOUNDER_INVITATION_HASHES_JSON",
        }
    )

    @classmethod
    def from_environment(
        cls, values: Mapping[str, str]
    ) -> "ControlledHostingConfiguration":
        def required(name: str) -> str:
            value = str(values.get(name, "")).strip()
            if not value:
                raise HostingConfigurationError(f"{name} is required.")
            return value

        def bounded_integer(name: str, minimum: int, maximum: int) -> int:
            try:
                value = int(required(name))
            except ValueError as error:
                raise HostingConfigurationError(
                    f"{name} must be an integer."
                ) from error
            if not minimum <= value <= maximum:
                raise HostingConfigurationError(
                    f"{name} must be between {minimum} and {maximum}."
                )
            return value

        raw_bindings = required("MLAI_SECRET_BINDINGS_JSON")
        try:
            secret_bindings = json.loads(raw_bindings)
        except json.JSONDecodeError as error:
            raise HostingConfigurationError(
                "MLAI_SECRET_BINDINGS_JSON must be valid JSON."
            ) from error
        if not isinstance(secret_bindings, dict) or any(
            not isinstance(key, str)
            or not isinstance(value, str)
            or not value.startswith("projects/")
            or "/secrets/" not in value
            for key, value in secret_bindings.items()
        ):
            raise HostingConfigurationError(
                "Secret bindings must map environment names to Secret Manager resources."
            )

        verified = required("MLAI_DURABLE_ADAPTER_VERIFIED").lower()
        if verified not in {"true", "false"}:
            raise HostingConfigurationError(
                "MLAI_DURABLE_ADAPTER_VERIFIED must be true or false."
            )

        return cls(
            project_id=required("MLAI_CLOUD_PROJECT_ID"),
            region=required("MLAI_CLOUD_REGION"),
            service_name=required("MLAI_CLOUD_RUN_SERVICE"),
            deployment_commit=required("MLAI_DEPLOYMENT_COMMIT").lower(),
            persistence_backend=required("MLAI_PERSISTENCE_BACKEND").lower(),
            database_secret_reference=required("MLAI_DATABASE_SECRET_REFERENCE"),
            cloud_sql_instance=required("MLAI_CLOUD_SQL_INSTANCE"),
            max_instances=bounded_integer("MLAI_CLOUD_RUN_MAX_INSTANCES", 1, 3),
            min_instances=bounded_integer("MLAI_CLOUD_RUN_MIN_INSTANCES", 0, 1),
            concurrency=bounded_integer("MLAI_CLOUD_RUN_CONCURRENCY", 1, 20),
            cpu=bounded_integer("MLAI_CLOUD_RUN_CPU", 1, 2),
            memory_mib=bounded_integer("MLAI_CLOUD_RUN_MEMORY_MIB", 256, 1024),
            monthly_budget_zar=bounded_integer("MLAI_MONTHLY_BUDGET_ZAR", 1, 1000),
            secret_bindings=secret_bindings,
            durable_adapter_verified=verified == "true",
            durable_adapter_evidence_reference=str(
                values.get("MLAI_DURABLE_ADAPTER_EVIDENCE_REFERENCE", "")
            ).strip(),
        )

    def evaluate(self) -> ControlledHostingReport:
        expected_instance_prefix = f"{self.project_id}:{self.region}:"
        missing_secrets = sorted(self.REQUIRED_SECRETS - self.secret_bindings.keys())
        checks = (
            HostingCheck(
                "project",
                self.project_id == "marketinglabai-identity-dev",
                "controlled Google project only",
            ),
            HostingCheck(
                "region",
                bool(re.fullmatch(r"[a-z]+-[a-z]+[0-9]", self.region)),
                "explicit Google Cloud region",
            ),
            HostingCheck(
                "service",
                self.service_name == "marketinglabai-velani-pilot",
                "single controlled pilot service",
            ),
            HostingCheck(
                "commit",
                bool(re.fullmatch(r"[0-9a-f]{40}", self.deployment_commit)),
                "full immutable Git commit",
            ),
            HostingCheck(
                "durable_backend",
                self.persistence_backend == "postgresql",
                "PostgreSQL required; Cloud Run SQLite is refused",
            ),
            HostingCheck(
                "durable_adapter",
                self.durable_adapter_verified
                and bool(self.durable_adapter_evidence_reference)
                and not re.search(
                    r"(?:password|secret|token|postgresql://)",
                    self.durable_adapter_evidence_reference,
                    re.I,
                ),
                "traceable live compatibility, migration and restore evidence required",
            ),
            HostingCheck(
                "cloud_sql_instance",
                self.cloud_sql_instance.startswith(expected_instance_prefix),
                "project- and region-bound Cloud SQL instance",
            ),
            HostingCheck(
                "database_secret",
                self.database_secret_reference.startswith("projects/")
                and "/secrets/" in self.database_secret_reference,
                "database URL supplied through Secret Manager",
            ),
            HostingCheck(
                "required_secrets",
                not missing_secrets,
                (
                    "missing: " + ", ".join(missing_secrets)
                    if missing_secrets
                    else "all required secret bindings declared"
                ),
            ),
            HostingCheck(
                "scale_bounds",
                self.min_instances == 0 and self.max_instances == 1,
                "scale-to-zero and one-instance pilot ceiling",
            ),
            HostingCheck(
                "resource_bounds",
                self.cpu == 1 and self.memory_mib <= 512 and self.concurrency <= 8,
                "one CPU, no more than 512 MiB and concurrency no more than eight",
            ),
            HostingCheck(
                "budget_bound",
                self.monthly_budget_zar <= 500,
                "founder-approved pilot ceiling no greater than R500",
            ),
        )
        return ControlledHostingReport(checks)


def require_cloud_deployment_authorization(
    report: ControlledHostingReport, *, founder_decision_recorded: bool
) -> None:
    """Refuse cloud mutation unless engineering and founder authority both exist."""

    if not report.engineering_ready:
        failed = ", ".join(check.name for check in report.checks if not check.passed)
        raise PermissionError(f"Controlled hosting is not engineering-ready: {failed}")
    if not founder_decision_recorded:
        raise PermissionError(
            "An explicit founder cloud-deployment decision is required."
        )
