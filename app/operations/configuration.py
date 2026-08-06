"""Environment-only configuration for the pilot service runtime."""

from __future__ import annotations

import json
import os
import re
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
    max_request_bytes: int = 1048576
    google_max_auth_age_seconds: int = 3600
    security_evidence: dict[str, bool] | None = None
    entra_tenant_id: str = ""
    entra_tenant_subdomain: str = ""
    entra_client_id: str = ""
    google_cloud_project_id: str = ""
    google_web_api_key: str = ""
    google_oauth_client_id: str = ""
    google_auth_domain: str = ""
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
        environment = required("MLAI_ENVIRONMENT")
        loopback_origin = bool(
            re.fullmatch(r"http://127\.0\.0\.1(?::\d{1,5})?", origin)
        )
        if (
            not origin.startswith("https://")
            and not trust_proxy_tls
            and not (environment == "synthetic-pilot" and loopback_origin)
        ):
            raise ValueError("Pilot traffic must use HTTPS or a trusted TLS proxy.")
        secret = required("MLAI_SESSION_SECRET")
        if len(secret) < 32 or secret.lower().startswith("replace"):
            raise ValueError(
                "MLAI_SESSION_SECRET must contain at least 32 secret characters."
            )
        ttl = int(str(env.get("MLAI_SESSION_TTL_SECONDS", "3600")))
        requests = int(str(env.get("MLAI_RATE_LIMIT_REQUESTS", "60")))
        window = int(str(env.get("MLAI_RATE_LIMIT_WINDOW_SECONDS", "60")))
        max_request_bytes = int(str(env.get("MLAI_MAX_REQUEST_BYTES", "1048576")))
        if ttl < 300 or ttl > 43200:
            raise ValueError("MLAI_SESSION_TTL_SECONDS must be between 300 and 43200.")
        if requests < 1 or window < 1:
            raise ValueError("Rate-limit values must be positive.")
        if not 1024 <= max_request_bytes <= 10485760:
            raise ValueError(
                "MLAI_MAX_REQUEST_BYTES must be between 1024 and 10485760."
            )
        allow_real = _boolean(
            str(env.get("MLAI_ALLOW_REAL_CUSTOMER_DATA", "false")),
            "MLAI_ALLOW_REAL_CUSTOMER_DATA",
        )
        if allow_real:
            raise ValueError(
                "Real customer-data activation remains frozen; keep "
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
        google_web_api_key = str(env.get("MLAI_GOOGLE_WEB_API_KEY", "")).strip()
        google_oauth_client_id = str(env.get("MLAI_GOOGLE_OAUTH_CLIENT_ID", "")).strip()
        google_auth_domain = str(env.get("MLAI_GOOGLE_AUTH_DOMAIN", "")).strip()
        google_max_auth_age_seconds = int(
            str(env.get("MLAI_GOOGLE_MAX_AUTH_AGE_SECONDS", "3600"))
        )
        if identity_provider == "google-cloud-identity-platform":
            if not google_web_api_key or not google_oauth_client_id:
                raise ValueError(
                    "MLAI_GOOGLE_WEB_API_KEY and MLAI_GOOGLE_OAUTH_CLIENT_ID are "
                    "required for the Google browser sign-in flow."
                )
            if not 300 <= google_max_auth_age_seconds <= 3600:
                raise ValueError(
                    "MLAI_GOOGLE_MAX_AUTH_AGE_SECONDS must be between 300 and 3600."
                )
            expected_domain = f"{google_cloud_project_id}.firebaseapp.com"
            if google_auth_domain != expected_domain:
                raise ValueError(
                    "MLAI_GOOGLE_AUTH_DOMAIN must match the project's standard "
                    "Firebase authentication domain."
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
        try:
            security_evidence = json.loads(
                str(env.get("MLAI_SECURITY_EVIDENCE_JSON", "{}"))
            )
        except json.JSONDecodeError as error:
            raise ValueError(
                "MLAI_SECURITY_EVIDENCE_JSON must be valid JSON."
            ) from error
        if not isinstance(security_evidence, dict) or any(
            not isinstance(key, str) or not isinstance(value, bool)
            for key, value in security_evidence.items()
        ):
            raise ValueError(
                "MLAI_SECURITY_EVIDENCE_JSON must map evidence names to booleans."
            )
        return cls(
            environment=environment,
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
            max_request_bytes=max_request_bytes,
            google_max_auth_age_seconds=google_max_auth_age_seconds,
            security_evidence=dict(security_evidence),
            **entra_values,
            google_cloud_project_id=google_cloud_project_id,
            google_web_api_key=google_web_api_key,
            google_oauth_client_id=google_oauth_client_id,
            google_auth_domain=google_auth_domain,
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
            "max_request_bytes": self.max_request_bytes,
            "google_max_auth_age_seconds": self.google_max_auth_age_seconds,
            "security_evidence_items": len(self.security_evidence or {}),
            "real_customer_data_allowed": False,
            "engineering_development_authorized": True,
            "synthetic_rehearsal_authorized": True,
            "real_data_activation_status": "frozen",
            "founder_invitations_configured": len(self.founder_invitation_hashes),
            "entra_configured": bool(
                self.entra_tenant_id
                and self.entra_tenant_subdomain
                and self.entra_client_id
            ),
            "google_cloud_identity_configured": bool(self.google_cloud_project_id),
            "google_browser_sign_in_configured": bool(
                self.google_web_api_key
                and self.google_oauth_client_id
                and self.google_auth_domain
            ),
        }

    @property
    def secure_cookies(self) -> bool:
        """Require Secure cookies except for the exact synthetic loopback origin."""

        return not self.public_origin.startswith("http://127.0.0.1")

    def public_identity_configuration(self) -> dict[str, str]:
        """Return only browser-safe Google Identity Platform identifiers."""

        if self.identity_provider != "google-cloud-identity-platform":
            raise ValueError("Google browser identity is not configured.")
        return {
            "provider": self.identity_provider,
            "project_id": self.google_cloud_project_id,
            "api_key": self.google_web_api_key,
            "oauth_client_id": self.google_oauth_client_id,
            "auth_domain": self.google_auth_domain,
        }
