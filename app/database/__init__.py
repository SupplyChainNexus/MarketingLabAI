"""SQLite persistence components for MarketingLabAI."""

from __future__ import annotations

from typing import Any

from app.database.connection import SQLiteDatabase
from app.database.factory import create_database
from app.database.postgresql import PostgreSQLDatabase
from app.database.repositories import (
    BrandRepository,
    BusinessIntelligenceRepository,
    CustomerIntelligenceRepository,
)

__all__ = [
    "SQLiteDatabase",
    "PostgreSQLDatabase",
    "create_database",
    "JsonToSQLiteMigrator",
    "BrandRepository",
    "BusinessIntelligenceRepository",
    "CustomerIntelligenceRepository",
]


def __getattr__(name: str) -> Any:
    """Load migration components only when explicitly requested."""

    if name == "JsonToSQLiteMigrator":
        from app.database.migration import JsonToSQLiteMigrator

        return JsonToSQLiteMigrator

    raise AttributeError(f"module 'app.database' has no attribute {name!r}")
