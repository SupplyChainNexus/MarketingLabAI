"""External identity-provider adapter boundary."""

from abc import ABC, abstractmethod

from app.identity.models import AuthenticatedPrincipal


class IdentityProviderAdapter(ABC):
    """Validate provider credentials and return a trusted principal."""

    @abstractmethod
    def authenticate(self, credential: str) -> AuthenticatedPrincipal:
        """Authenticate one opaque external credential."""
