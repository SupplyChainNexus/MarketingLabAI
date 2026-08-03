"""Customer Intelligence context provider."""

from __future__ import annotations

from app.customer_intelligence.context import CustomerContextBuilder
from app.database.repositories import CustomerIntelligenceRepository


class CustomerContextProvider:
    """Load and render Customer Intelligence for AI context assembly."""

    def __init__(
        self,
        *,
        repository: CustomerIntelligenceRepository,
        context_builder: CustomerContextBuilder | None = None,
    ) -> None:
        if not isinstance(repository, CustomerIntelligenceRepository):
            raise TypeError("repository must be a CustomerIntelligenceRepository.")

        if context_builder is not None and not isinstance(
            context_builder,
            CustomerContextBuilder,
        ):
            raise TypeError("context_builder must be a CustomerContextBuilder.")

        self.repository = repository
        self.context_builder = context_builder or CustomerContextBuilder()

    def build(self, brand_id: str) -> str:
        """Return Customer Intelligence context when a profile exists."""

        if not isinstance(brand_id, str):
            raise TypeError("brand_id must be a string.")

        cleaned_brand_id = brand_id.strip()

        if not cleaned_brand_id:
            raise ValueError("brand_id is required.")

        if not self.repository.exists(cleaned_brand_id):
            return ""

        profile = self.repository.get(cleaned_brand_id)

        return self.context_builder.build(profile)
