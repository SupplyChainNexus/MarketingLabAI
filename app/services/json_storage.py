"""Simple JSON persistence service."""

import json
from pathlib import Path
from typing import Any


class JsonStorage:
    """Read and write structured JSON records safely."""

    def __init__(self, folder: Path):
        self.folder = Path(folder)
        self.folder.mkdir(parents=True, exist_ok=True)

    def _get_path(self, record_id: str) -> Path:
        safe_id = record_id.strip()

        if not safe_id:
            raise ValueError("Record ID cannot be empty.")

        if any(character in safe_id for character in ('/', '\\', ':', '*', '?', '"', '<', '>', '|')):
            raise ValueError("Record ID contains invalid filename characters.")

        return self.folder / f"{safe_id}.json"

    def save(self, record_id: str, data: dict[str, Any]) -> Path:
        path = self._get_path(record_id)
        temporary_path = path.with_suffix(".tmp")

        temporary_path.write_text(
            json.dumps(data, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

        temporary_path.replace(path)
        return path

    def load(self, record_id: str) -> dict[str, Any]:
        path = self._get_path(record_id)

        if not path.exists():
            raise FileNotFoundError(f"Record not found: {record_id}")

        return json.loads(path.read_text(encoding="utf-8"))

    def exists(self, record_id: str) -> bool:
        return self._get_path(record_id).exists()

    def delete(self, record_id: str) -> bool:
        path = self._get_path(record_id)

        if not path.exists():
            return False

        path.unlink()
        return True

    def list_records(self) -> list[str]:
        return sorted(path.stem for path in self.folder.glob("*.json"))
