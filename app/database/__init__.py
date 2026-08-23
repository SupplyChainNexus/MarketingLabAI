"""SQLite persistence components for MarketingLabAI."""

from __future__ import annotations

from typing import Any

from app.database.connection import (
    DatabaseLifecycleError,
    DatabaseMigrationLockTimeoutError,
    DatabaseSchemaNotReadyError,
    SQLiteDatabase,
)
from app.database.factory import (
    bootstrap_database,
    create_database,
    require_database_ready,
)
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
    "bootstrap_database",
    "require_database_ready",
    "DatabaseLifecycleError",
    "DatabaseMigrationLockTimeoutError",
    "DatabaseSchemaNotReadyError",
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
