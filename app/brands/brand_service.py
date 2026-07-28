"""Brand profile management."""

from app.config import Settings, load_settings
from app.models import BrandProfile
from app.services.json_storage import JsonStorage


class BrandService:
    """Create, retrieve, and list brand profiles."""

    def __init__(self, settings: Settings | None = None):
        self.settings = settings or load_settings()
        self.storage = JsonStorage(self.settings.database_folder / "brands")

    def save_brand(self, brand: BrandProfile) -> BrandProfile:
        self.storage.save(brand.brand_id, brand.to_dict())
        return brand

    def get_brand(self, brand_id: str) -> BrandProfile:
        data = self.storage.load(brand_id)
        return BrandProfile(**data)

    def brand_exists(self, brand_id: str) -> bool:
        return self.storage.exists(brand_id)

    def list_brand_ids(self) -> list[str]:
        return self.storage.list_records()
