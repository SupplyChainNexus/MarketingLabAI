"""Environment-selected database construction with safe defaults."""

from __future__ import annotations

from app.database.connection import DatabaseSchemaNotReadyError, SQLiteDatabase
from app.database.postgresql import PostgreSQLDatabase


def create_database(*, backend: str, database_path, database_url: str):
    selected = str(backend).strip().lower()
    if selected == "sqlite":
        return SQLiteDatabase(database_path)
    if selected == "postgresql":
        return PostgreSQLDatabase(database_url)
    raise ValueError("MLAI_PERSISTENCE_BACKEND must be sqlite or postgresql.")


def bootstrap_database(database: SQLiteDatabase) -> SQLiteDatabase:
    """Explicitly initialise a standalone or migration-owned database instance."""

    if not isinstance(database, SQLiteDatabase):
        raise TypeError("database must be a SQLiteDatabase.")
    database.ensure_initialised()
    return database


def require_database_ready(database: SQLiteDatabase) -> SQLiteDatabase:
    """Fail closed when a runtime-owned database has not been migrated."""

    if not isinstance(database, SQLiteDatabase):
        raise TypeError("database must be a SQLiteDatabase.")
    if not database.schema_is_ready():
        raise DatabaseSchemaNotReadyError(
            "The database schema is not ready; the dedicated migrator must run first."
        )
    return database
