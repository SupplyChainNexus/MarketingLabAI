"""Load Product Intelligence for AI context assembly."""

from app.product_intelligence.context import ProductContextBuilder
from app.product_intelligence.repository import ProductIntelligenceRepository


class ProductContextProvider:
    def __init__(self, repository: ProductIntelligenceRepository) -> None:
        self.repository = repository
        self.builder = ProductContextBuilder()

    def build(self, *, tenant_id: str, brand_id: str) -> str:
        if not isinstance(tenant_id, str) or not isinstance(brand_id, str):
            raise TypeError("tenant_id and brand_id must be strings.")
        tenant_id = tenant_id.strip()
        brand_id = brand_id.strip()
        if not tenant_id or not brand_id:
            raise ValueError("tenant_id and brand_id are required.")
        if not self.repository.exists(tenant_id=tenant_id, brand_id=brand_id):
            return ""
        return self.builder.build(
            self.repository.get(tenant_id=tenant_id, brand_id=brand_id)
        )
