"""Environment-only configuration for the pilot service runtime."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping


def _boolean(value: str, name: str) -> bool:
    normalized = value.strip().lower()
    if normalized not in {"true", "false"}:
        raise ValueError(f"{name} must be true or false.")
    return normalized == "true"


@dataclass(slots=True, frozen=True)
class PilotConfiguration:
    environment: str
    database_path: Path
    backup_directory: Path
    public_origin: str
    trust_proxy_tls: bool
    session_ttl_seconds: int
    rate_limit_requests: int
    rate_limit_window_seconds: int
    identity_provider: str
    identity_adapter_factory: str
    provider_registry_factory: str
    session_secret: str
    founder_invitation_hashes: dict[str, str]
    entra_tenant_id: str = ""
    entra_tenant_subdomain: str = ""
    entra_client_id: str = ""
    google_cloud_project_id: str = ""
    allow_real_customer_data: bool = False

    @classmethod
    def from_environment(
        cls, values: Mapping[str, str] | None = None
    ) -> "PilotConfiguration":
        env = os.environ if values is None else values

        def required(name: str) -> str:
            value = str(env.get(name, "")).strip()
            if not value:
                raise ValueError(f"{name} is required.")
            return value

        origin = required("MLAI_PUBLIC_ORIGIN").rstrip("/")
        trust_proxy_tls = _boolean(
            str(env.get("MLAI_TRUST_PROXY_TLS", "false")),
            "MLAI_TRUST_PROXY_TLS",
        )
        if not origin.startswith("https://") and not trust_proxy_tls:
            raise ValueError("Pilot traffic must use HTTPS or a trusted TLS proxy.")
        secret = required("MLAI_SESSION_SECRET")
        if len(secret) < 32 or secret.lower().startswith("replace"):
            raise ValueError(
                "MLAI_SESSION_SECRET must contain at least 32 secret characters."
            )
        ttl = int(str(env.get("MLAI_SESSION_TTL_SECONDS", "3600")))
        requests = int(str(env.get("MLAI_RATE_LIMIT_REQUESTS", "60")))
        window = int(str(env.get("MLAI_RATE_LIMIT_WINDOW_SECONDS", "60")))
        if ttl < 300 or ttl > 43200:
            raise ValueError("MLAI_SESSION_TTL_SECONDS must be between 300 and 43200.")
        if requests < 1 or window < 1:
            raise ValueError("Rate-limit values must be positive.")
        allow_real = _boolean(
            str(env.get("MLAI_ALLOW_REAL_CUSTOMER_DATA", "false")),
            "MLAI_ALLOW_REAL_CUSTOMER_DATA",
        )
        if allow_real:
            raise ValueError(
                "Real customer data remains founder-frozen; keep "
                "MLAI_ALLOW_REAL_CUSTOMER_DATA=false."
            )
        identity_provider = required("MLAI_IDENTITY_PROVIDER")
        entra_values = {
            "entra_tenant_id": str(env.get("MLAI_ENTRA_TENANT_ID", "")).strip(),
            "entra_tenant_subdomain": str(
                env.get("MLAI_ENTRA_TENANT_SUBDOMAIN", "")
            ).strip(),
            "entra_client_id": str(env.get("MLAI_ENTRA_CLIENT_ID", "")).strip(),
        }
        if identity_provider == "microsoft-entra-external-id" and not all(
            entra_values.values()
        ):
            raise ValueError(
                "MLAI_ENTRA_TENANT_ID, MLAI_ENTRA_TENANT_SUBDOMAIN and "
                "MLAI_ENTRA_CLIENT_ID are required for Microsoft Entra External ID."
            )
        google_cloud_project_id = str(
            env.get("MLAI_GOOGLE_CLOUD_PROJECT_ID", "")
        ).strip()
        if (
            identity_provider == "google-cloud-identity-platform"
            and not google_cloud_project_id
        ):
            raise ValueError(
                "MLAI_GOOGLE_CLOUD_PROJECT_ID is required for Google Cloud "
                "Identity Platform."
            )
        try:
            invitation_hashes = json.loads(
                str(env.get("MLAI_FOUNDER_INVITATION_HASHES_JSON", "{}"))
            )
        except json.JSONDecodeError as error:
            raise ValueError(
                "MLAI_FOUNDER_INVITATION_HASHES_JSON must be valid JSON."
            ) from error
        if not isinstance(invitation_hashes, dict) or any(
            not isinstance(key, str) or not isinstance(value, str) or len(value) != 64
            for key, value in invitation_hashes.items()
        ):
            raise ValueError(
                "Founder invitation hashes must map tenant IDs to SHA-256 hashes."
            )
        return cls(
            environment=required("MLAI_ENVIRONMENT"),
            database_path=Path(required("MLAI_DATABASE_PATH")),
            backup_directory=Path(required("MLAI_BACKUP_DIRECTORY")),
            public_origin=origin,
            trust_proxy_tls=trust_proxy_tls,
            session_ttl_seconds=ttl,
            rate_limit_requests=requests,
            rate_limit_window_seconds=window,
            identity_provider=identity_provider,
            identity_adapter_factory=required("MLAI_IDENTITY_ADAPTER_FACTORY"),
            provider_registry_factory=required("MLAI_PROVIDER_REGISTRY_FACTORY"),
            session_secret=secret,
            founder_invitation_hashes=dict(invitation_hashes),
            **entra_values,
            google_cloud_project_id=google_cloud_project_id,
            allow_real_customer_data=False,
        )

    def public_summary(self) -> dict[str, object]:
        """Return operator-safe configuration without secrets or local paths."""

        return {
            "environment": self.environment,
            "public_origin": self.public_origin,
            "identity_provider": self.identity_provider,
            "session_ttl_seconds": self.session_ttl_seconds,
            "rate_limit_requests": self.rate_limit_requests,
            "rate_limit_window_seconds": self.rate_limit_window_seconds,
            "real_customer_data_allowed": False,
            "founder_invitations_configured": len(self.founder_invitation_hashes),
            "entra_configured": bool(
                self.entra_tenant_id
                and self.entra_tenant_subdomain
                and self.entra_client_id
            ),
            "google_cloud_identity_configured": bool(self.google_cloud_project_id),
        }
