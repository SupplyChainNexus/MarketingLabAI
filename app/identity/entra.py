"""Microsoft Entra External ID adapter with strict OIDC token validation."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

import jwt
from jwt import PyJWKClient
from jwt.exceptions import PyJWTError

from app.identity.models import AuthenticatedPrincipal
from app.identity.provider import IdentityProviderAdapter


class EntraAuthenticationError(PermissionError):
    """Raised when an Entra credential cannot establish a trusted identity."""


@dataclass(frozen=True, slots=True)
class EntraExternalIdSettings:
    tenant_id: str
    tenant_subdomain: str
    client_id: str

    def __post_init__(self) -> None:
        for name in ("tenant_id", "tenant_subdomain", "client_id"):
            value = getattr(self, name)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{name} is required.")
            object.__setattr__(self, name, value.strip())
        if any(char in self.tenant_subdomain for char in "/:?&#"):
            raise ValueError("tenant_subdomain must be a DNS label.")

    @property
    def issuer(self) -> str:
        return (
            f"https://{self.tenant_subdomain}.ciamlogin.com/" f"{self.tenant_id}/v2.0"
        )

    @property
    def jwks_uri(self) -> str:
        return f"{self.issuer}/discovery/v2.0/keys"


class EntraExternalIdAdapter(IdentityProviderAdapter):
    """Verify signature and mandatory claims before returning a principal."""

    def __init__(
        self,
        settings: EntraExternalIdSettings,
        *,
        jwk_client_factory: Callable[[str], Any] = PyJWKClient,
    ) -> None:
        if not isinstance(settings, EntraExternalIdSettings):
            raise TypeError("settings must be EntraExternalIdSettings.")
        self.settings = settings
        self._jwk_client = jwk_client_factory(settings.jwks_uri)

    def authenticate(self, credential: str) -> AuthenticatedPrincipal:
        if not isinstance(credential, str) or not credential.strip():
            raise EntraAuthenticationError("Bearer credential is required.")
        token = credential.strip()
        try:
            signing_key = self._jwk_client.get_signing_key_from_jwt(token).key
            claims = jwt.decode(
                token,
                signing_key,
                algorithms=["RS256"],
                audience=self.settings.client_id,
                issuer=self.settings.issuer,
                options={"require": ["exp", "iat", "iss", "aud", "sub"]},
            )
        except (PyJWTError, ValueError, TypeError, KeyError) as error:
            raise EntraAuthenticationError(
                "Microsoft Entra credential validation failed."
            ) from error
        subject = str(claims.get("sub", "")).strip()
        if not subject:
            raise EntraAuthenticationError("Microsoft Entra subject is missing.")
        display_name = str(
            claims.get("name") or claims.get("preferred_username") or ""
        ).strip()
        return AuthenticatedPrincipal(
            subject_id=subject,
            provider="microsoft-entra-external-id",
            display_name=display_name,
        )


def create_entra_adapter(configuration) -> EntraExternalIdAdapter:
    """Runtime factory used by the provider-neutral composition root."""

    return EntraExternalIdAdapter(
        EntraExternalIdSettings(
            tenant_id=configuration.entra_tenant_id,
            tenant_subdomain=configuration.entra_tenant_subdomain,
            client_id=configuration.entra_client_id,
        )
    )
