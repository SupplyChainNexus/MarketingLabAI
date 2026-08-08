"""Default-deny specification checks for the private synthetic deployment."""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass
from typing import Mapping


@dataclass(frozen=True, slots=True)
class DeploymentCheck:
    name: str
    passed: bool
    evidence: str


@dataclass(frozen=True, slots=True)
class PrivateSyntheticDeploymentReport:
    checks: tuple[DeploymentCheck, ...]

    @property
    def engineering_ready(self) -> bool:
        return all(check.passed for check in self.checks)

    def to_dict(self) -> dict[str, object]:
        return {
            "checks": [asdict(check) for check in self.checks],
            "engineering_ready": self.engineering_ready,
            "private_synthetic_deployment_authorized": False,
            "public_access_authorized": False,
            "external_invitation_authorized": False,
            "real_customer_data_authorized": False,
            "billing_authorized": False,
            "publishing_authorized": False,
            "real_data_learning_authorized": False,
            "status": "external_evidence_and_founder_decision_required",
        }


@dataclass(frozen=True, slots=True)
class PrivateSyntheticDeploymentSpecification:
    project_id: str
    region: str
    service_name: str
    runtime_service_account: str
    cloud_sql_instance: str
    artifact_image: str
    minimum_instances: int
    maximum_instances: int
    cpu: int
    memory_mib: int
    concurrency: int
    ingress: str
    allow_unauthenticated: bool
    real_customer_data: bool
    secret_bindings: Mapping[str, str]

    REQUIRED_SECRETS = frozenset(
        {
            "GEMINI_API_KEY",
            "MLAI_DATABASE_URL",
            "MLAI_SESSION_SECRET",
            "MLAI_FOUNDER_INVITATION_HASHES_JSON",
        }
    )

    def evaluate(self) -> PrivateSyntheticDeploymentReport:
        expected_project = "marketinglabai-identity-dev"
        expected_region = "africa-south1"
        expected_service = "marketinglabai-velani-pilot"
        expected_account = (
            "mlai-synthetic-runtime@marketinglabai-identity-dev.iam.gserviceaccount.com"
        )
        expected_instance = (
            "marketinglabai-identity-dev:africa-south1:mlai-synthetic-pg18-jhb"
        )
        missing_secrets = sorted(self.REQUIRED_SECRETS - set(self.secret_bindings))
        safe_secret_references = all(
            re.fullmatch(
                r"projects/marketinglabai-identity-dev/secrets/[a-z0-9-]+",
                value,
            )
            for value in self.secret_bindings.values()
        )
        checks = (
            DeploymentCheck(
                "project", self.project_id == expected_project, expected_project
            ),
            DeploymentCheck("region", self.region == expected_region, expected_region),
            DeploymentCheck(
                "service", self.service_name == expected_service, expected_service
            ),
            DeploymentCheck(
                "runtime_identity",
                self.runtime_service_account == expected_account,
                "dedicated least-privilege runtime service account",
            ),
            DeploymentCheck(
                "cloud_sql_instance",
                self.cloud_sql_instance == expected_instance,
                "retained controlled synthetic PostgreSQL instance",
            ),
            DeploymentCheck(
                "immutable_image",
                bool(
                    re.fullmatch(
                        r"africa-south1-docker\.pkg\.dev/marketinglabai-identity-dev/"
                        r"mlai-synthetic/marketinglabai-pilot@sha256:[0-9a-f]{64}",
                        self.artifact_image,
                    )
                ),
                "Artifact Registry image pinned by SHA-256 digest",
            ),
            DeploymentCheck(
                "scale_to_zero",
                self.minimum_instances == 0 and self.maximum_instances == 1,
                "minimum zero and maximum one instance",
            ),
            DeploymentCheck(
                "bounded_resources",
                self.cpu == 1 and self.memory_mib == 512 and self.concurrency <= 8,
                "one CPU, 512 MiB and concurrency no greater than eight",
            ),
            DeploymentCheck(
                "authenticated_access",
                not self.allow_unauthenticated,
                "no allUsers or allAuthenticatedUsers invoker",
            ),
            DeploymentCheck(
                "ingress",
                self.ingress == "all",
                "Cloud Run ingress with IAM authentication enforced",
            ),
            DeploymentCheck(
                "secret_bindings",
                not missing_secrets and safe_secret_references,
                "external Secret Manager references only",
            ),
            DeploymentCheck(
                "real_data_freeze",
                not self.real_customer_data,
                "real-customer data remains frozen",
            ),
        )
        return PrivateSyntheticDeploymentReport(checks)
