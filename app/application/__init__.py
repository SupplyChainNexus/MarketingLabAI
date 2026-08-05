"""Canonical application composition for MarketingLabAI."""

from app.application.authorized import (
    AuthorizedTenantApplication,
    LifecycleConflictError,
)
from app.application.composition import CanonicalApplication

__all__ = [
    "AuthorizedTenantApplication",
    "CanonicalApplication",
    "LifecycleConflictError",
]
