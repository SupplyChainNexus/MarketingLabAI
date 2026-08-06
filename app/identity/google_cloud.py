"""Google Cloud Identity Platform adapter with strict ID-token validation."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

import jwt
from jwt import PyJWKClient
from jwt.exceptions import PyJWTError

from app.identity.models import AuthenticatedPrincipal
from app.identity.provider import IdentityProviderAdapter


class GoogleCloudAuthenticationError(PermissionError):
    """Raised when a Google credential cannot establish a trusted identity."""


@dataclass(frozen=True, slots=True)
class GoogleCloudIdentitySettings:
    project_id: str

    def __post_init__(self) -> None:
        if not isinstance(self.project_id, str) or not self.project_id.strip():
            raise ValueError("project_id is required.")
        project_id = self.project_id.strip()
        if any(char in project_id for char in "/:?&#"):
            raise ValueError("project_id must be a Google Cloud project identifier.")
        object.__setattr__(self, "project_id", project_id)

    @property
    def issuer(self) -> str:
        return f"https://securetoken.google.com/{self.project_id}"

    @property
    def jwks_uri(self) -> str:
        return (
            "https://www.googleapis.com/service_accounts/v1/jwk/"
            "securetoken@system.gserviceaccount.com"
        )


class GoogleCloudIdentityAdapter(IdentityProviderAdapter):
    """Verify Google signature and mandatory claims before trust is granted."""

    def __init__(
        self,
        settings: GoogleCloudIdentitySettings,
        *,
        jwk_client_factory: Callable[[str], Any] = PyJWKClient,
    ) -> None:
        if not isinstance(settings, GoogleCloudIdentitySettings):
            raise TypeError("settings must be GoogleCloudIdentitySettings.")
        self.settings = settings
        self._jwk_client = jwk_client_factory(settings.jwks_uri)

    def authenticate(self, credential: str) -> AuthenticatedPrincipal:
        if not isinstance(credential, str) or not credential.strip():
            raise GoogleCloudAuthenticationError("Bearer credential is required.")
        token = credential.strip()
        try:
            signing_key = self._jwk_client.get_signing_key_from_jwt(token).key
            claims = jwt.decode(
                token,
                signing_key,
                algorithms=["RS256"],
                audience=self.settings.project_id,
                issuer=self.settings.issuer,
                options={
                    "require": [
                        "exp",
                        "iat",
                        "iss",
                        "aud",
                        "sub",
                        "auth_time",
                    ]
                },
            )
        except (PyJWTError, ValueError, TypeError, KeyError) as error:
            raise GoogleCloudAuthenticationError(
                "Google Cloud identity credential validation failed."
            ) from error
        subject = str(claims.get("sub", "")).strip()
        if not subject or len(subject) > 128:
            raise GoogleCloudAuthenticationError(
                "Google Cloud identity subject is invalid."
            )
        email = str(claims.get("email", "")).strip()
        firebase = claims.get("firebase")
        if (
            not email
            or claims.get("email_verified") is not True
            or not isinstance(firebase, dict)
            or firebase.get("sign_in_provider") != "google.com"
        ):
            raise GoogleCloudAuthenticationError(
                "A verified Google sign-in identity is required."
            )
        display_name = str(claims.get("name") or email).strip()
        return AuthenticatedPrincipal(
            subject_id=subject,
            provider="google-cloud-identity-platform",
            display_name=display_name,
        )


def create_google_cloud_adapter(configuration) -> GoogleCloudIdentityAdapter:
    """Runtime factory used by the provider-neutral composition root."""

    return GoogleCloudIdentityAdapter(
        GoogleCloudIdentitySettings(project_id=configuration.google_cloud_project_id)
    )
