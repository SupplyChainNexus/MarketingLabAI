"""File persistence for Customer Intelligence profiles."""

from __future__ import annotations

import json
from pathlib import Path
from tempfile import NamedTemporaryFile

from app.customer_intelligence.models import (
    CustomerIntelligenceProfile,
    current_utc_timestamp,
)


class CustomerIntelligenceService:
    """Store and retrieve Customer Intelligence profiles."""

    def __init__(
        self,
        storage_directory: str | Path = "database/customer_intelligence",
    ) -> None:
        self.storage_directory = Path(storage_directory)
        self.storage_directory.mkdir(parents=True, exist_ok=True)

    def save_profile(self, profile: CustomerIntelligenceProfile) -> Path:
        """Save a profile using atomic file replacement."""

        if not isinstance(profile, CustomerIntelligenceProfile):
            raise TypeError("profile must be a CustomerIntelligenceProfile.")

        profile.updated_at = current_utc_timestamp()
        destination = self._profile_path(profile.brand_id)

        with NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=self.storage_directory,
            prefix=f"{profile.brand_id}-",
            suffix=".tmp",
            delete=False,
        ) as temporary_file:
            json.dump(
                profile.to_dict(),
                temporary_file,
                indent=2,
                ensure_ascii=False,
                sort_keys=True,
            )
            temporary_file.write("\n")
            temporary_path = Path(temporary_file.name)

        temporary_path.replace(destination)
        return destination

    def get_profile(self, brand_id: str) -> CustomerIntelligenceProfile:
        """Load the Customer Intelligence profile for a brand."""

        profile_path = self._profile_path(brand_id)

        if not profile_path.exists():
            raise FileNotFoundError(
                f"No customer intelligence profile exists for {brand_id!r}."
            )

        with profile_path.open("r", encoding="utf-8") as profile_file:
            stored_data = json.load(profile_file)

        if not isinstance(stored_data, dict):
            raise ValueError(f"Invalid customer intelligence data for {brand_id!r}.")

        return CustomerIntelligenceProfile.from_dict(stored_data)

    def profile_exists(self, brand_id: str) -> bool:
        """Return whether a profile exists."""

        return self._profile_path(brand_id).exists()

    def list_brand_ids(self) -> list[str]:
        """Return sorted brand IDs with stored profiles."""

        return sorted(
            path.stem
            for path in self.storage_directory.glob("*.json")
            if path.is_file()
        )

    def delete_profile(self, brand_id: str) -> bool:
        """Delete a profile and report whether one existed."""

        profile_path = self._profile_path(brand_id)

        if not profile_path.exists():
            return False

        profile_path.unlink()
        return True

    def _profile_path(self, brand_id: str) -> Path:
        if not isinstance(brand_id, str):
            raise TypeError("brand_id must be a string.")

        cleaned_brand_id = brand_id.strip()

        if not cleaned_brand_id:
            raise ValueError("brand_id is required.")

        invalid_characters = {"\\", "/", ":", "*", "?", '"', "<", ">", "|"}

        if any(character in invalid_characters for character in cleaned_brand_id):
            raise ValueError("brand_id contains invalid path characters.")

        return self.storage_directory / f"{cleaned_brand_id}.json"
