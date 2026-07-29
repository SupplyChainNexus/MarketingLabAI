"""Relational repositories for MarketingLabAI data."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Any

from app.database.connection import SQLiteDatabase
from app.intelligence.models import BusinessIntelligenceProfile


def current_utc_timestamp() -> str:
    """Return the current UTC timestamp."""

    return datetime.now(UTC).isoformat()


def encode_json(value: Any) -> str:
    """Encode a value as deterministic JSON."""

    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
    )


def decode_json(value: str) -> Any:
    """Decode stored JSON."""

    return json.loads(value)


class BrandRepository:
    """Store and retrieve brand payloads in SQLite."""

    def __init__(self, database: SQLiteDatabase | None = None) -> None:
        self.database = database or SQLiteDatabase()
        self.database.initialise()

    def save(self, payload: dict[str, Any]) -> None:
        """Insert or update a brand record."""

        brand_id = str(payload.get("brand_id", "")).strip()
        name = str(payload.get("name", "")).strip()

        if not brand_id:
            raise ValueError("brand_id is required.")

        if not name:
            raise ValueError("Brand name is required.")

        timestamp = current_utc_timestamp()

        target_audience = payload.get("target_audience", [])
        products = payload.get("products", [])
        values = payload.get("values", [])

        with self.database.transaction() as connection:
            connection.execute(
                """
                INSERT INTO brands (
                    brand_id,
                    name,
                    industry,
                    description,
                    target_audience_json,
                    products_json,
                    values_json,
                    website,
                    payload_json,
                    created_at,
                    updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(brand_id) DO UPDATE SET
                    name = excluded.name,
                    industry = excluded.industry,
                    description = excluded.description,
                    target_audience_json = excluded.target_audience_json,
                    products_json = excluded.products_json,
                    values_json = excluded.values_json,
                    website = excluded.website,
                    payload_json = excluded.payload_json,
                    updated_at = excluded.updated_at
                """,
                (
                    brand_id,
                    name,
                    str(payload.get("industry", "")),
                    str(payload.get("description", "")),
                    encode_json(target_audience),
                    encode_json(products),
                    encode_json(values),
                    str(payload.get("website", "")),
                    encode_json(payload),
                    timestamp,
                    timestamp,
                ),
            )

    def get(self, brand_id: str) -> dict[str, Any]:
        """Return a complete brand payload."""

        with self.database.connection() as connection:
            row = connection.execute(
                """
                SELECT payload_json
                FROM brands
                WHERE brand_id = ?
                """,
                (brand_id,),
            ).fetchone()

        if row is None:
            raise FileNotFoundError(
                f"No brand exists with ID '{brand_id}'."
            )

        payload = decode_json(str(row["payload_json"]))

        if not isinstance(payload, dict):
            raise ValueError(
                f"Invalid stored brand payload for '{brand_id}'."
            )

        return payload

    def exists(self, brand_id: str) -> bool:
        """Return whether a brand exists."""

        with self.database.connection() as connection:
            row = connection.execute(
                """
                SELECT 1
                FROM brands
                WHERE brand_id = ?
                LIMIT 1
                """,
                (brand_id,),
            ).fetchone()

        return row is not None

    def list_ids(self) -> list[str]:
        """Return all brand IDs."""

        with self.database.connection() as connection:
            rows = connection.execute(
                """
                SELECT brand_id
                FROM brands
                ORDER BY brand_id
                """
            ).fetchall()

        return [str(row["brand_id"]) for row in rows]

    def count(self) -> int:
        """Return the number of stored brands."""

        with self.database.connection() as connection:
            row = connection.execute(
                "SELECT COUNT(*) AS total FROM brands"
            ).fetchone()

        return int(row["total"]) if row else 0


class BusinessIntelligenceRepository:
    """Store and retrieve Company Brain profiles in SQLite."""

    def __init__(self, database: SQLiteDatabase | None = None) -> None:
        self.database = database or SQLiteDatabase()
        self.database.initialise()

    def save(self, profile: BusinessIntelligenceProfile) -> None:
        """Insert or update a business intelligence profile."""

        timestamp = current_utc_timestamp()
        payload = profile.to_dict()
        profile.updated_at = timestamp
        payload["updated_at"] = timestamp

        with self.database.transaction() as connection:
            connection.execute(
                """
                INSERT INTO business_intelligence_profiles (
                    brand_id,
                    revenue_model,
                    average_order_value,
                    gross_margin_percent,
                    customer_lifetime_value,
                    customer_acquisition_cost,
                    sales_cycle_days,
                    monthly_marketing_budget,
                    team_size,
                    sales_channels_json,
                    geographic_markets_json,
                    capacity_constraints_json,
                    seasonality_json,
                    competitors_json,
                    business_goals_json,
                    payload_json,
                    created_at,
                    updated_at
                )
                VALUES (
                    ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?
                )
                ON CONFLICT(brand_id) DO UPDATE SET
                    revenue_model = excluded.revenue_model,
                    average_order_value = excluded.average_order_value,
                    gross_margin_percent = excluded.gross_margin_percent,
                    customer_lifetime_value = excluded.customer_lifetime_value,
                    customer_acquisition_cost = excluded.customer_acquisition_cost,
                    sales_cycle_days = excluded.sales_cycle_days,
                    monthly_marketing_budget =
                        excluded.monthly_marketing_budget,
                    team_size = excluded.team_size,
                    sales_channels_json = excluded.sales_channels_json,
                    geographic_markets_json =
                        excluded.geographic_markets_json,
                    capacity_constraints_json =
                        excluded.capacity_constraints_json,
                    seasonality_json = excluded.seasonality_json,
                    competitors_json = excluded.competitors_json,
                    business_goals_json = excluded.business_goals_json,
                    payload_json = excluded.payload_json,
                    updated_at = excluded.updated_at
                """,
                (
                    profile.brand_id,
                    profile.revenue_model,
                    profile.average_order_value,
                    profile.gross_margin_percent,
                    profile.customer_lifetime_value,
                    profile.customer_acquisition_cost,
                    profile.sales_cycle_days,
                    profile.monthly_marketing_budget,
                    profile.team_size,
                    encode_json(profile.sales_channels),
                    encode_json(profile.geographic_markets),
                    encode_json(profile.capacity_constraints),
                    encode_json(profile.seasonality),
                    encode_json(profile.competitors),
                    encode_json(profile.business_goals),
                    encode_json(payload),
                    timestamp,
                    timestamp,
                ),
            )

    def get(self, brand_id: str) -> BusinessIntelligenceProfile:
        """Return the Company Brain profile for a brand."""

        with self.database.connection() as connection:
            row = connection.execute(
                """
                SELECT payload_json
                FROM business_intelligence_profiles
                WHERE brand_id = ?
                """,
                (brand_id,),
            ).fetchone()

        if row is None:
            raise FileNotFoundError(
                f"No business intelligence profile exists for '{brand_id}'."
            )

        payload = decode_json(str(row["payload_json"]))

        if not isinstance(payload, dict):
            raise ValueError(
                f"Invalid business intelligence data for '{brand_id}'."
            )

        return BusinessIntelligenceProfile.from_dict(payload)

    def exists(self, brand_id: str) -> bool:
        """Return whether a Company Brain profile exists."""

        with self.database.connection() as connection:
            row = connection.execute(
                """
                SELECT 1
                FROM business_intelligence_profiles
                WHERE brand_id = ?
                LIMIT 1
                """,
                (brand_id,),
            ).fetchone()

        return row is not None

    def list_brand_ids(self) -> list[str]:
        """Return IDs with Company Brain profiles."""

        with self.database.connection() as connection:
            rows = connection.execute(
                """
                SELECT brand_id
                FROM business_intelligence_profiles
                ORDER BY brand_id
                """
            ).fetchall()

        return [str(row["brand_id"]) for row in rows]

    def count(self) -> int:
        """Return the number of Company Brain profiles."""

        with self.database.connection() as connection:
            row = connection.execute(
                """
                SELECT COUNT(*) AS total
                FROM business_intelligence_profiles
                """
            ).fetchone()

        return int(row["total"]) if row else 0
