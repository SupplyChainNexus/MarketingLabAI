"""Canonical application composition for MarketingLabAI."""

from app.application.composition import CanonicalApplication
from app.application.authorized import AuthorizedTenantApplication

__all__ = ["AuthorizedTenantApplication", "CanonicalApplication"]
