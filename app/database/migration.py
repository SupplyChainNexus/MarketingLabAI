"""Import existing MarketingLabAI JSON records into SQLite."""

from __future__ import annotations

import argparse
import json
import shutil
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from app.database.connection import SQLiteDatabase
from app.database.repositories import (
    BrandRepository,
    BusinessIntelligenceRepository,
)
from app.intelligence.models import BusinessIntelligenceProfile


def current_utc_timestamp() -> str:
    """Return the current UTC timestamp."""

    return datetime.now(UTC).isoformat()


@dataclass(slots=True)
class MigrationResult:
    """Summary of one migration run."""

    brands_imported: int = 0
    intelligence_profiles_imported: int = 0
    records_skipped: int = 0
    records_failed: int = 0
    backup_directory: Path | None = None


class JsonToSQLiteMigrator:
    """Migrate existing JSON data without deleting source records."""

    def __init__(
        self,
        *,
        database: SQLiteDatabase | None = None,
        brands_directory: str | Path = "database/brands",
        intelligence_directory: str | Path = (
            "database/business_intelligence"
        ),
        backup_root: str | Path = "database/backups",
    ) -> None:
        self.database = database or SQLiteDatabase()
        self.brands_directory = Path(brands_directory)
        self.intelligence_directory = Path(intelligence_directory)
        self.backup_root = Path(backup_root)

        self.database.initialise()
        self.brand_repository = BrandRepository(self.database)
        self.intelligence_repository = BusinessIntelligenceRepository(
            self.database
        )

    def migrate(self) -> MigrationResult:
        """Back up and import all supported JSON records."""

        result = MigrationResult()
        result.backup_directory = self._create_backup()

        for path in self._json_files(self.brands_directory):
            try:
                payload = self._load_json_object(path)
                brand_id = self._extract_brand_id(payload, path)
                payload["brand_id"] = brand_id

                if self.brand_repository.exists(brand_id):
                    result.records_skipped += 1
                    self._log(
                        "brand",
                        path,
                        brand_id,
                        "skipped",
                        "Brand already exists in SQLite.",
                    )
                    continue

                self.brand_repository.save(payload)
                result.brands_imported += 1

                self._log(
                    "brand",
                    path,
                    brand_id,
                    "imported",
                    "",
                )
            except Exception as error:
                result.records_failed += 1
                self._log(
                    "brand",
                    path,
                    path.stem,
                    "failed",
                    str(error),
                )

        for path in self._json_files(self.intelligence_directory):
            try:
                payload = self._load_json_object(path)
                brand_id = self._extract_brand_id(payload, path)
                payload["brand_id"] = brand_id

                if not self.brand_repository.exists(brand_id):
                    result.records_failed += 1
                    self._log(
                        "business_intelligence",
                        path,
                        brand_id,
                        "failed",
                        "The linked brand does not exist in SQLite.",
                    )
                    continue

                if self.intelligence_repository.exists(brand_id):
                    result.records_skipped += 1
                    self._log(
                        "business_intelligence",
                        path,
                        brand_id,
                        "skipped",
                        "Profile already exists in SQLite.",
                    )
                    continue

                profile = BusinessIntelligenceProfile.from_dict(payload)
                self.intelligence_repository.save(profile)
                result.intelligence_profiles_imported += 1

                self._log(
                    "business_intelligence",
                    path,
                    brand_id,
                    "imported",
                    "",
                )
            except Exception as error:
                result.records_failed += 1
                self._log(
                    "business_intelligence",
                    path,
                    path.stem,
                    "failed",
                    str(error),
                )

        return result

    def _create_backup(self) -> Path:
        timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%S%fZ")
        backup_directory = self.backup_root / f"json-before-sqlite-{timestamp}"
        backup_directory.mkdir(parents=True, exist_ok=False)

        self._copy_directory(
            self.brands_directory,
            backup_directory / "brands",
        )
        self._copy_directory(
            self.intelligence_directory,
            backup_directory / "business_intelligence",
        )

        return backup_directory

    @staticmethod
    def _copy_directory(source: Path, destination: Path) -> None:
        if source.exists():
            shutil.copytree(source, destination)
        else:
            destination.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def _json_files(directory: Path) -> list[Path]:
        if not directory.exists():
            return []

        return sorted(
            path
            for path in directory.glob("*.json")
            if path.is_file()
        )

    @staticmethod
    def _load_json_object(path: Path) -> dict[str, Any]:
        with path.open("r", encoding="utf-8") as source_file:
            payload = json.load(source_file)

        if not isinstance(payload, dict):
            raise ValueError("The JSON root must be an object.")

        return payload

    @staticmethod
    def _extract_brand_id(
        payload: dict[str, Any],
        path: Path,
    ) -> str:
        brand_id = str(payload.get("brand_id", path.stem)).strip()

        if not brand_id:
            raise ValueError("The record does not contain a valid brand ID.")

        return brand_id

    def _log(
        self,
        source_type: str,
        source_path: Path,
        record_id: str,
        status: str,
        message: str,
    ) -> None:
        with self.database.transaction() as connection:
            connection.execute(
                """
                INSERT INTO data_migration_log (
                    source_type,
                    source_path,
                    record_id,
                    status,
                    message,
                    migrated_at
                )
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    source_type,
                    str(source_path),
                    record_id,
                    status,
                    message,
                    current_utc_timestamp(),
                ),
            )


def build_parser() -> argparse.ArgumentParser:
    """Create the migration command parser."""

    parser = argparse.ArgumentParser(
        description=(
            "Import existing MarketingLabAI JSON records into SQLite."
        )
    )
    parser.add_argument(
        "--database",
        default="database/marketinglabai.db",
        help="SQLite database path.",
    )
    parser.add_argument(
        "--brands-directory",
        default="database/brands",
        help="Existing brand JSON directory.",
    )
    parser.add_argument(
        "--intelligence-directory",
        default="database/business_intelligence",
        help="Existing Company Brain JSON directory.",
    )
    parser.add_argument(
        "--backup-root",
        default="database/backups",
        help="Directory for pre-migration backups.",
    )

    return parser


def main() -> int:
    """Run the JSON-to-SQLite migration."""

    arguments = build_parser().parse_args()

    database = SQLiteDatabase(arguments.database)
    migrator = JsonToSQLiteMigrator(
        database=database,
        brands_directory=arguments.brands_directory,
        intelligence_directory=arguments.intelligence_directory,
        backup_root=arguments.backup_root,
    )

    result = migrator.migrate()

    print("")
    print("MarketingLabAI SQLite Migration")
    print("-------------------------------")
    print(f"Brands imported: {result.brands_imported}")
    print(
        "Company Brain profiles imported: "
        f"{result.intelligence_profiles_imported}"
    )
    print(f"Records skipped: {result.records_skipped}")
    print(f"Records failed: {result.records_failed}")
    print(f"Backup directory: {result.backup_directory}")
    print(f"Database integrity: {database.integrity_check()}")
    print(f"Database path: {database.database_path}")

    return 1 if result.records_failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
