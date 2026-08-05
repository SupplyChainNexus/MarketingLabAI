"""Verified online SQLite backup and guarded restore operations."""

from __future__ import annotations

import hashlib
import sqlite3
from contextlib import closing
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from app.database.connection import SQLiteDatabase


@dataclass(slots=True, frozen=True)
class BackupEvidence:
    path: Path
    sha256: str
    created_at: str
    integrity: str


class SQLiteRecoveryService:
    def __init__(self, database: SQLiteDatabase, backup_directory: str | Path) -> None:
        self.database = database
        self.backup_directory = Path(backup_directory)

    def create_backup(self, name: str | None = None) -> BackupEvidence:
        self.database.initialise()
        self.backup_directory.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
        filename = name or f"marketinglabai-{stamp}.sqlite3"
        if Path(filename).name != filename or not filename.endswith(".sqlite3"):
            raise ValueError("Backup name must be a .sqlite3 filename.")
        target = self.backup_directory / filename
        if target.exists():
            raise FileExistsError(target)
        with self.database.connection() as source:
            with closing(sqlite3.connect(target)) as backup:
                source.backup(backup)
        integrity = self.verify(target)
        return BackupEvidence(
            target,
            hashlib.sha256(target.read_bytes()).hexdigest(),
            datetime.now(UTC).isoformat(),
            integrity,
        )

    @staticmethod
    def verify(path: str | Path) -> str:
        selected = Path(path)
        if not selected.is_file():
            raise FileNotFoundError(selected)
        with closing(
            sqlite3.connect(f"file:{selected}?mode=ro", uri=True)
        ) as connection:
            row = connection.execute("PRAGMA integrity_check").fetchone()
        result = "" if row is None else str(row[0])
        if result != "ok":
            raise RuntimeError(f"Backup integrity check failed: {result}")
        return result

    def restore_to(self, backup_path: str | Path, destination: str | Path) -> Path:
        source = Path(backup_path)
        self.verify(source)
        target = Path(destination)
        target.parent.mkdir(parents=True, exist_ok=True)
        if target.exists():
            raise FileExistsError("Restore destination must not already exist.")
        with closing(sqlite3.connect(f"file:{source}?mode=ro", uri=True)) as backup:
            with closing(sqlite3.connect(target)) as restored:
                backup.backup(restored)
        self.verify(target)
        return target
