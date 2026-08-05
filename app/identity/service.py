"""Default-deny tenant authorization service."""

from __future__ import annotations

from uuid import uuid4

from app.identity.models import (
    AuthenticatedPrincipal,
    AuthorizationAuditEvent,
    Permission,
    TenantMembership,
)
from app.identity.repository import IdentityRepository


class AuthorizationDeniedError(PermissionError):
    """Raised when a principal lacks a tenant permission."""


class TenantAuthorizationService:
    def __init__(self, repository: IdentityRepository) -> None:
        if not isinstance(repository, IdentityRepository):
            raise TypeError("repository must be an IdentityRepository.")
        self.repository = repository

    def authorize(
        self,
        principal: AuthenticatedPrincipal,
        *,
        tenant_id: str,
        permission: Permission,
        resource_type: str,
        resource_id: str,
        metadata: dict | None = None,
        resource_tenant_id: str | None = None,
        audit_action: str | None = None,
    ) -> TenantMembership:
        if not isinstance(principal, AuthenticatedPrincipal):
            raise TypeError("principal must be an AuthenticatedPrincipal.")
        permission = Permission(permission)
        membership = self.repository.get_membership(
            provider=principal.provider,
            subject_id=principal.subject_id,
            tenant_id=tenant_id,
        )
        ownership_matches = (
            resource_tenant_id is None or resource_tenant_id == tenant_id
        )
        allowed = (
            membership is not None
            and membership.grants(permission)
            and ownership_matches
        )
        self.repository.save_audit_event(
            AuthorizationAuditEvent(
                event_id=str(uuid4()),
                tenant_id=tenant_id,
                subject_id=principal.subject_id,
                provider=principal.provider,
                action=audit_action or permission.value,
                resource_type=resource_type,
                resource_id=resource_id,
                outcome="allowed" if allowed else "denied",
                metadata=dict(metadata or {}),
            )
        )
        if not allowed:
            raise AuthorizationDeniedError(
                "Authenticated principal is not authorized for this tenant action."
            )
        return membership
