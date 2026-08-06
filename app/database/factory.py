"""Environment-selected database construction with safe defaults."""

from __future__ import annotations

from app.database.connection import SQLiteDatabase
from app.database.postgresql import PostgreSQLDatabase


def create_database(*, backend: str, database_path, database_url: str):
    selected = str(backend).strip().lower()
    if selected == "sqlite":
        return SQLiteDatabase(database_path)
    if selected == "postgresql":
        return PostgreSQLDatabase(database_url)
    raise ValueError("MLAI_PERSISTENCE_BACKEND must be sqlite or postgresql.")
