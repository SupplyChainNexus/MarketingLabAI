"""Trusted identity and tenant authorization boundaries."""

from app.identity.entra import (
    EntraAuthenticationError,
    EntraExternalIdAdapter,
    EntraExternalIdSettings,
    create_entra_adapter,
)
from app.identity.models import (
    AuthenticatedPrincipal,
    AuthorizationAuditEvent,
    Permission,
    TenantMembership,
    TenantRole,
)
from app.identity.provider import IdentityProviderAdapter
from app.identity.repository import IdentityRepository
from app.identity.service import AuthorizationDeniedError, TenantAuthorizationService

__all__ = [
    "AuthenticatedPrincipal",
    "AuthorizationAuditEvent",
    "AuthorizationDeniedError",
    "EntraAuthenticationError",
    "EntraExternalIdAdapter",
    "EntraExternalIdSettings",
    "IdentityProviderAdapter",
    "IdentityRepository",
    "Permission",
    "TenantAuthorizationService",
    "TenantMembership",
    "TenantRole",
    "create_entra_adapter",
]
