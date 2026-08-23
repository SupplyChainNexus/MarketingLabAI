"""Relational repositories for MarketingLabAI data."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Any

from app.customer_intelligence.models import CustomerIntelligenceProfile
from app.database.connection import SQLiteDatabase
from app.intelligence.models import BusinessIntelligenceProfile
from app.memory.models import MemoryEvent
from app.tenants.models import DEFAULT_TENANT_ID


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

    def __init__(
        self,
        database: SQLiteDatabase | None = None,
    ) -> None:
        self.database = database or SQLiteDatabase()

    def save(self, payload: dict[str, Any]) -> None:
        """Insert or update a tenant-owned brand record."""

        brand_id = str(payload.get("brand_id", "")).strip()
        name = str(payload.get("name", "")).strip()
        tenant_id = str(payload.get("tenant_id", DEFAULT_TENANT_ID)).strip()

        if not brand_id:
            raise ValueError("brand_id is required.")

        if not name:
            raise ValueError("Brand name is required.")

        if not tenant_id:
            tenant_id = DEFAULT_TENANT_ID

        timestamp = current_utc_timestamp()

        target_audience = payload.get("target_audience", [])
        products = payload.get("products", [])
        values = payload.get("values", [])

        with self.database.transaction() as connection:
            connection.execute(
                """
                INSERT INTO brands (
                    brand_id,
                    tenant_id,
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
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(brand_id) DO UPDATE SET
                    tenant_id = excluded.tenant_id,
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
                    tenant_id,
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
            raise FileNotFoundError(f"No brand exists with ID '{brand_id}'.")

        payload = decode_json(str(row["payload_json"]))

        if not isinstance(payload, dict):
            raise ValueError(f"Invalid stored brand payload for '{brand_id}'.")

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

    def tenant_id_for(self, brand_id: str) -> str:
        """Return the tenant that owns a brand."""

        with self.database.connection() as connection:
            row = connection.execute(
                """
                SELECT tenant_id
                FROM brands
                WHERE brand_id = ?
                """,
                (brand_id,),
            ).fetchone()

        if row is None:
            raise FileNotFoundError(f"No brand exists with ID '{brand_id}'.")

        return str(row["tenant_id"])

    def list_ids(
        self,
        tenant_id: str | None = None,
    ) -> list[str]:
        """Return brand IDs, optionally filtered by tenant."""

        query = "SELECT brand_id FROM brands"
        parameters: tuple[str, ...] = ()

        if tenant_id is not None:
            query += " WHERE tenant_id = ?"
            parameters = (tenant_id,)

        query += " ORDER BY brand_id"

        with self.database.connection() as connection:
            rows = connection.execute(
                query,
                parameters,
            ).fetchall()

        return [str(row["brand_id"]) for row in rows]

    def count(
        self,
        tenant_id: str | None = None,
    ) -> int:
        """Return the number of stored brands."""

        query = "SELECT COUNT(*) AS total FROM brands"
        parameters: tuple[str, ...] = ()

        if tenant_id is not None:
            query += " WHERE tenant_id = ?"
            parameters = (tenant_id,)

        with self.database.connection() as connection:
            row = connection.execute(
                query,
                parameters,
            ).fetchone()

        return int(row["total"]) if row else 0


class BusinessIntelligenceRepository:
    """Store and retrieve Company Brain profiles in SQLite."""

    def __init__(self, database: SQLiteDatabase | None = None) -> None:
        self.database = database or SQLiteDatabase()

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
            raise ValueError(f"Invalid business intelligence data for '{brand_id}'.")

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
            rows = connection.execute("""
                SELECT brand_id
                FROM business_intelligence_profiles
                ORDER BY brand_id
                """).fetchall()

        return [str(row["brand_id"]) for row in rows]

    def count(self) -> int:
        """Return the number of Company Brain profiles."""

        with self.database.connection() as connection:
            row = connection.execute("""
                SELECT COUNT(*) AS total
                FROM business_intelligence_profiles
                """).fetchone()

        return int(row["total"]) if row else 0


class CustomerIntelligenceRepository:
    """Store and retrieve Customer Intelligence profiles in SQLite."""

    def __init__(self, database: SQLiteDatabase | None = None) -> None:
        self.database = database or SQLiteDatabase()

    def save(self, profile: CustomerIntelligenceProfile) -> None:
        """Insert or update a Customer Intelligence profile."""

        if not isinstance(profile, CustomerIntelligenceProfile):
            raise TypeError("profile must be a CustomerIntelligenceProfile.")

        timestamp = current_utc_timestamp()
        profile.updated_at = timestamp
        payload = profile.to_dict()
        payload["updated_at"] = timestamp

        with self.database.transaction() as connection:
            connection.execute(
                """
                INSERT INTO customer_intelligence_profiles (
                    brand_id,
                    summary,
                    primary_segment_id,
                    segments_json,
                    ideal_customer_profiles_json,
                    personas_json,
                    payload_json,
                    created_at,
                    updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(brand_id) DO UPDATE SET
                    summary = excluded.summary,
                    primary_segment_id = excluded.primary_segment_id,
                    segments_json = excluded.segments_json,
                    ideal_customer_profiles_json =
                        excluded.ideal_customer_profiles_json,
                    personas_json = excluded.personas_json,
                    payload_json = excluded.payload_json,
                    updated_at = excluded.updated_at
                """,
                (
                    profile.brand_id,
                    profile.summary,
                    profile.primary_segment_id,
                    encode_json(
                        [segment.to_dict() for segment in profile.segments]
                    ),
                    encode_json(
                        [
                            item.to_dict()
                            for item in profile.ideal_customer_profiles
                        ]
                    ),
                    encode_json(
                        [persona.to_dict() for persona in profile.personas]
                    ),
                    encode_json(payload),
                    timestamp,
                    timestamp,
                ),
            )

    def get(self, brand_id: str) -> CustomerIntelligenceProfile:
        """Return the Customer Intelligence profile for a brand."""

        with self.database.connection() as connection:
            row = connection.execute(
                """
                SELECT payload_json
                FROM customer_intelligence_profiles
                WHERE brand_id = ?
                """,
                (brand_id,),
            ).fetchone()

        if row is None:
            raise FileNotFoundError(
                f"No customer intelligence profile exists for {brand_id!r}."
            )

        payload = decode_json(str(row["payload_json"]))

        if not isinstance(payload, dict):
            raise ValueError(
                f"Invalid customer intelligence data for {brand_id!r}."
            )

        return CustomerIntelligenceProfile.from_dict(payload)

    def exists(self, brand_id: str) -> bool:
        """Return whether a Customer Intelligence profile exists."""

        with self.database.connection() as connection:
            row = connection.execute(
                """
                SELECT 1
                FROM customer_intelligence_profiles
                WHERE brand_id = ?
                LIMIT 1
                """,
                (brand_id,),
            ).fetchone()

        return row is not None

    def list_brand_ids(self) -> list[str]:
        """Return brand IDs with Customer Intelligence profiles."""

        with self.database.connection() as connection:
            rows = connection.execute(
                """
                SELECT brand_id
                FROM customer_intelligence_profiles
                ORDER BY brand_id
                """
            ).fetchall()

        return [str(row["brand_id"]) for row in rows]

    def count(self) -> int:
        """Return the number of Customer Intelligence profiles."""

        with self.database.connection() as connection:
            row = connection.execute(
                """
                SELECT COUNT(*) AS total
                FROM customer_intelligence_profiles
                """
            ).fetchone()

        return int(row["total"]) if row else 0


class MemoryRepository:
    """Store and retrieve institutional memory events in SQLite."""

    def __init__(self, database: SQLiteDatabase | None = None) -> None:
        self.database = database or SQLiteDatabase()

    def save(self, event: MemoryEvent) -> None:
        """Store a new memory event.

        Memory records are append-only. Existing IDs cannot be overwritten.
        """

        if not isinstance(event, MemoryEvent):
            raise TypeError("event must be a MemoryEvent.")

        timestamp = event.created_at or current_utc_timestamp()
        payload = event.to_dict()
        payload["created_at"] = timestamp

        with self.database.transaction() as connection:
            try:
                connection.execute(
                    """
                    INSERT INTO memory_events (
                        memory_id,
                        brand_id,
                        event_type,
                        source,
                        summary,
                        payload_json,
                        created_at
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        event.memory_id,
                        event.brand_id,
                        event.event_type,
                        event.source,
                        event.summary,
                        encode_json(payload),
                        timestamp,
                    ),
                )
            except Exception as error:
                if "UNIQUE constraint failed" in str(error):
                    raise ValueError(
                        f"A memory event with ID "
                        f"'{event.memory_id}' already exists."
                    ) from error

                raise

        event.created_at = timestamp

    def get(self, memory_id: str) -> MemoryEvent:
        """Return one memory event by ID."""

        with self.database.connection() as connection:
            row = connection.execute(
                """
                SELECT payload_json
                FROM memory_events
                WHERE memory_id = ?
                """,
                (memory_id,),
            ).fetchone()

        if row is None:
            raise FileNotFoundError(f"No memory event exists with ID '{memory_id}'.")

        payload = decode_json(str(row["payload_json"]))

        if not isinstance(payload, dict):
            raise ValueError(f"Invalid stored memory payload for '{memory_id}'.")

        return MemoryEvent.from_dict(payload)

    def list(
        self,
        brand_id: str,
        *,
        event_type: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[MemoryEvent]:
        """Return memory events for a brand, newest first."""

        if limit < 1:
            raise ValueError("limit must be at least 1.")

        if offset < 0:
            raise ValueError("offset cannot be negative.")

        query = """
            SELECT payload_json
            FROM memory_events
            WHERE brand_id = ?
        """
        parameters: list[Any] = [brand_id]

        if event_type is not None:
            query += " AND event_type = ?"
            parameters.append(event_type)

        query += """
            ORDER BY created_at DESC, memory_id DESC
            LIMIT ? OFFSET ?
        """
        parameters.extend([limit, offset])

        with self.database.connection() as connection:
            rows = connection.execute(
                query,
                tuple(parameters),
            ).fetchall()

        return [
            MemoryEvent.from_dict(decode_json(str(row["payload_json"]))) for row in rows
        ]

    def search(
        self,
        brand_id: str,
        search_text: str,
        *,
        limit: int = 50,
    ) -> list[MemoryEvent]:
        """Search summaries, sources, event types, and JSON payloads."""

        search_text = search_text.strip()

        if not search_text:
            return []

        if limit < 1:
            raise ValueError("limit must be at least 1.")

        pattern = f"%{search_text}%"

        with self.database.connection() as connection:
            rows = connection.execute(
                """
                SELECT payload_json
                FROM memory_events
                WHERE brand_id = ?
                  AND (
                      summary LIKE ?
                      OR source LIKE ?
                      OR event_type LIKE ?
                      OR payload_json LIKE ?
                  )
                ORDER BY created_at DESC, memory_id DESC
                LIMIT ?
                """,
                (
                    brand_id,
                    pattern,
                    pattern,
                    pattern,
                    pattern,
                    limit,
                ),
            ).fetchall()

        return [
            MemoryEvent.from_dict(decode_json(str(row["payload_json"]))) for row in rows
        ]

    def count(
        self,
        brand_id: str | None = None,
        *,
        event_type: str | None = None,
    ) -> int:
        """Return the number of matching memory events."""

        query = "SELECT COUNT(*) AS total FROM memory_events"
        conditions: list[str] = []
        parameters: list[Any] = []

        if brand_id is not None:
            conditions.append("brand_id = ?")
            parameters.append(brand_id)

        if event_type is not None:
            conditions.append("event_type = ?")
            parameters.append(event_type)

        if conditions:
            query += " WHERE " + " AND ".join(conditions)

        with self.database.connection() as connection:
            row = connection.execute(
                query,
                tuple(parameters),
            ).fetchone()

        return int(row["total"]) if row else 0
