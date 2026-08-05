"""Canonical application composition for MarketingLabAI."""

from app.application.composition import CanonicalApplication
from app.application.authorized import (
    AuthorizedTenantApplication,
    LifecycleConflictError,
)

__all__ = [
    "AuthorizedTenantApplication",
    "CanonicalApplication",
    "LifecycleConflictError",
]
