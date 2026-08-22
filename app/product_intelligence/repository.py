"""SQLite persistence for Product Intelligence."""

from __future__ import annotations

import json

from app.database.connection import SQLiteDatabase
from app.product_intelligence.models import ProductIntelligenceProfile


def _identifier(value: str, name: str) -> str:
    if not isinstance(value, str):
        raise TypeError(f"{name} must be a string.")
    value = value.strip()
    if not value:
        raise ValueError(f"{name} is required.")
    return value


class ProductIntelligenceRepository:
    def __init__(self, database: SQLiteDatabase | None = None) -> None:
        self.database = database or SQLiteDatabase()
        self.database.ensure_initialised()

    def save(self, profile: ProductIntelligenceProfile) -> None:
        if not isinstance(profile, ProductIntelligenceProfile):
            raise TypeError("profile must be a ProductIntelligenceProfile.")
        with self.database.connection() as connection:
            brand = connection.execute(
                "SELECT tenant_id FROM brands WHERE brand_id = ?",
                (profile.brand_id,),
            ).fetchone()
        if brand is None:
            raise ValueError(f"Brand {profile.brand_id!r} does not exist.")
        if str(brand["tenant_id"]) != profile.tenant_id:
            raise ValueError("Product Intelligence tenant and brand differ.")
        payload = json.dumps(profile.to_dict(), ensure_ascii=False, sort_keys=True)
        with self.database.transaction() as connection:
            connection.execute(
                """
                INSERT INTO product_intelligence_profiles
                    (tenant_id, brand_id, payload_json, updated_at)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(tenant_id, brand_id) DO UPDATE SET
                    payload_json = excluded.payload_json,
                    updated_at = excluded.updated_at
                """,
                (profile.tenant_id, profile.brand_id, payload, profile.updated_at),
            )

    def get(self, *, tenant_id: str, brand_id: str) -> ProductIntelligenceProfile:
        tenant_id = _identifier(tenant_id, "tenant_id")
        brand_id = _identifier(brand_id, "brand_id")
        with self.database.connection() as connection:
            row = connection.execute(
                """SELECT payload_json FROM product_intelligence_profiles
                   WHERE tenant_id = ? AND brand_id = ?""",
                (tenant_id, brand_id),
            ).fetchone()
        if row is None:
            raise FileNotFoundError("Product Intelligence profile was not found.")
        return ProductIntelligenceProfile.from_dict(json.loads(row["payload_json"]))

    def exists(self, *, tenant_id: str, brand_id: str) -> bool:
        tenant_id = _identifier(tenant_id, "tenant_id")
        brand_id = _identifier(brand_id, "brand_id")
        with self.database.connection() as connection:
            row = connection.execute(
                """SELECT 1 FROM product_intelligence_profiles
                   WHERE tenant_id = ? AND brand_id = ? LIMIT 1""",
                (tenant_id, brand_id),
            ).fetchone()
        return row is not None
