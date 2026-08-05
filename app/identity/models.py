"""Provider-neutral authenticated identity and tenant authorization models."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any


def _required(value: str, name: str) -> str:
    if not isinstance(value, str):
        raise TypeError(f"{name} must be a string.")
    value = value.strip()
    if not value:
        raise ValueError(f"{name} is required.")
    return value


class TenantRole(StrEnum):
    VIEWER = "viewer"
    MARKETER = "marketer"
    APPROVER = "approver"
    ADMIN = "admin"


class Permission(StrEnum):
    VIEW = "view"
    GENERATE = "generate"
    APPROVE = "approve"
    EXPORT = "export"
    MANAGE_MEMBERS = "manage_members"


ROLE_PERMISSIONS: dict[TenantRole, frozenset[Permission]] = {
    TenantRole.VIEWER: frozenset({Permission.VIEW}),
    TenantRole.MARKETER: frozenset(
        {Permission.VIEW, Permission.GENERATE, Permission.EXPORT}
    ),
    TenantRole.APPROVER: frozenset(
        {Permission.VIEW, Permission.GENERATE, Permission.APPROVE, Permission.EXPORT}
    ),
    TenantRole.ADMIN: frozenset(Permission),
}


@dataclass(slots=True, frozen=True)
class AuthenticatedPrincipal:
    """Identity established by a trusted external provider adapter."""

    subject_id: str
    provider: str
    display_name: str = ""
    authenticated_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())

    def __post_init__(self) -> None:
        object.__setattr__(self, "subject_id", _required(self.subject_id, "subject_id"))
        object.__setattr__(self, "provider", _required(self.provider, "provider"))
        if not isinstance(self.display_name, str):
            raise TypeError("display_name must be a string.")
        object.__setattr__(self, "display_name", self.display_name.strip())
        object.__setattr__(
            self,
            "authenticated_at",
            _required(self.authenticated_at, "authenticated_at"),
        )


@dataclass(slots=True, frozen=True)
class TenantMembership:
    subject_id: str
    provider: str
    tenant_id: str
    role: TenantRole
    active: bool = True

    def __post_init__(self) -> None:
        object.__setattr__(self, "subject_id", _required(self.subject_id, "subject_id"))
        object.__setattr__(self, "provider", _required(self.provider, "provider"))
        object.__setattr__(self, "tenant_id", _required(self.tenant_id, "tenant_id"))
        object.__setattr__(self, "role", TenantRole(self.role))
        if not isinstance(self.active, bool):
            raise TypeError("active must be a boolean.")

    def grants(self, permission: Permission) -> bool:
        return self.active and Permission(permission) in ROLE_PERMISSIONS[self.role]


@dataclass(slots=True, frozen=True)
class AuthorizationAuditEvent:
    event_id: str
    tenant_id: str
    subject_id: str
    provider: str
    action: str
    resource_type: str
    resource_id: str
    outcome: str
    occurred_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        for name in (
            "event_id",
            "tenant_id",
            "subject_id",
            "provider",
            "action",
            "resource_type",
            "resource_id",
            "outcome",
            "occurred_at",
        ):
            object.__setattr__(self, name, _required(getattr(self, name), name))
        if self.outcome not in {"allowed", "denied"}:
            raise ValueError("outcome must be allowed or denied.")
        if not isinstance(self.metadata, dict):
            raise TypeError("metadata must be a dictionary.")
        object.__setattr__(self, "metadata", dict(self.metadata))
