"SQLite persistence for versioned Marketing Briefs."

from __future__ import annotations

from typing import Any

from app.database.connection import SQLiteDatabase
from app.database.repositories import decode_json, encode_json
from app.marketing_brief.models import MarketingBrief


class MarketingBriefRepository:
    "Store immutable versions of tenant-owned Marketing Briefs."

    def __init__(
        self,
        database: SQLiteDatabase | None = None,
    ) -> None:
        self.database = database or SQLiteDatabase()
        self.database.ensure_initialised()

    def save(self, brief: MarketingBrief) -> None:
        "Persist a new Marketing Brief version."

        if not isinstance(brief, MarketingBrief):
            raise TypeError("brief must be a MarketingBrief.")

        self._validate_ownership(brief)

        try:
            with self.database.transaction() as connection:
                connection.execute(
                    """
                    INSERT INTO marketing_briefs (
                        brief_id,
                        version,
                        tenant_id,
                        brand_id,
                        name,
                        status,
                        payload_json,
                        created_at,
                        updated_at
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        brief.brief_id,
                        brief.version,
                        brief.tenant_id,
                        brief.brand_id,
                        brief.name,
                        brief.status.value,
                        encode_json(brief.to_dict()),
                        brief.created_at,
                        brief.updated_at,
                    ),
                )
        except Exception as error:
            if "UNIQUE constraint failed" in str(error):
                raise ValueError(
                    f"Marketing Brief '{brief.brief_id}' "
                    f"version {brief.version} already exists."
                ) from error

            raise

    def get(
        self,
        brief_id: str,
        *,
        tenant_id: str,
        version: int | None = None,
    ) -> MarketingBrief:
        "Return a specific version or the latest tenant version."

        brief_id = self._required_text("brief_id", brief_id)
        tenant_id = self._required_text("tenant_id", tenant_id)
        self._validate_version(version)

        if version is None:
            query = """
                SELECT payload_json
                FROM marketing_briefs
                WHERE brief_id = ?
                  AND tenant_id = ?
                ORDER BY version DESC
                LIMIT 1
            """
            parameters: tuple[Any, ...] = (brief_id, tenant_id)
        else:
            query = """
                SELECT payload_json
                FROM marketing_briefs
                WHERE brief_id = ?
                  AND tenant_id = ?
                  AND version = ?
            """
            parameters = (brief_id, tenant_id, version)

        with self.database.connection() as connection:
            row = connection.execute(query, parameters).fetchone()

        if row is None:
            version_text = "" if version is None else f" version {version}"
            raise FileNotFoundError(
                f"No Marketing Brief '{brief_id}'{version_text} "
                f"exists for tenant '{tenant_id}'."
            )

        return self._brief_from_payload(str(row["payload_json"]))

    def list_versions(
        self,
        brief_id: str,
        *,
        tenant_id: str,
    ) -> list[MarketingBrief]:
        "Return all stored versions in ascending order."

        brief_id = self._required_text("brief_id", brief_id)
        tenant_id = self._required_text("tenant_id", tenant_id)

        with self.database.connection() as connection:
            rows = connection.execute(
                """
                SELECT payload_json
                FROM marketing_briefs
                WHERE brief_id = ?
                  AND tenant_id = ?
                ORDER BY version
                """,
                (brief_id, tenant_id),
            ).fetchall()

        return [self._brief_from_payload(str(row["payload_json"])) for row in rows]

    def list_latest_for_brand(
        self,
        *,
        tenant_id: str,
        brand_id: str,
        status: str | None = None,
    ) -> list[MarketingBrief]:
        "Return the latest version of every brief for a brand."

        tenant_id = self._required_text("tenant_id", tenant_id)
        brand_id = self._required_text("brand_id", brand_id)
        status_filter = self._optional_text(status)

        filters = [
            "current.tenant_id = ?",
            "current.brand_id = ?",
        ]
        parameters: list[Any] = [
            tenant_id,
            brand_id,
            tenant_id,
            brand_id,
        ]

        if status_filter is not None:
            filters.append("current.status = ?")
            parameters.append(status_filter)

        where_clause = " AND ".join(filters)

        query = f"""
            SELECT current.payload_json
            FROM marketing_briefs AS current
            INNER JOIN (
                SELECT
                    brief_id,
                    tenant_id,
                    MAX(version) AS latest_version
                FROM marketing_briefs
                WHERE tenant_id = ?
                  AND brand_id = ?
                GROUP BY brief_id, tenant_id
            ) AS latest
                ON current.brief_id = latest.brief_id
               AND current.tenant_id = latest.tenant_id
               AND current.version = latest.latest_version
            WHERE {where_clause}
            ORDER BY current.brief_id
        """

        with self.database.connection() as connection:
            rows = connection.execute(
                query,
                tuple(parameters),
            ).fetchall()

        return [self._brief_from_payload(str(row["payload_json"])) for row in rows]

    def exists(
        self,
        brief_id: str,
        *,
        tenant_id: str,
        version: int | None = None,
    ) -> bool:
        "Return whether a tenant Marketing Brief exists."

        brief_id = self._required_text("brief_id", brief_id)
        tenant_id = self._required_text("tenant_id", tenant_id)
        self._validate_version(version)

        if version is None:
            query = """
                SELECT 1
                FROM marketing_briefs
                WHERE brief_id = ?
                  AND tenant_id = ?
                LIMIT 1
            """
            parameters: tuple[Any, ...] = (brief_id, tenant_id)
        else:
            query = """
                SELECT 1
                FROM marketing_briefs
                WHERE brief_id = ?
                  AND tenant_id = ?
                  AND version = ?
                LIMIT 1
            """
            parameters = (brief_id, tenant_id, version)

        with self.database.connection() as connection:
            row = connection.execute(query, parameters).fetchone()

        return row is not None

    def count(
        self,
        *,
        tenant_id: str | None = None,
    ) -> int:
        "Return the number of stored Marketing Brief versions."

        if tenant_id is None:
            query = "SELECT COUNT(*) AS total FROM marketing_briefs"
            parameters: tuple[Any, ...] = ()
        else:
            tenant_id = self._required_text("tenant_id", tenant_id)
            query = """
                SELECT COUNT(*) AS total
                FROM marketing_briefs
                WHERE tenant_id = ?
            """
            parameters = (tenant_id,)

        with self.database.connection() as connection:
            row = connection.execute(query, parameters).fetchone()

        return int(row["total"]) if row else 0

    def _validate_ownership(
        self,
        brief: MarketingBrief,
    ) -> None:
        "Validate tenant existence and brand ownership."

        with self.database.connection() as connection:
            tenant = connection.execute(
                """
                SELECT 1
                FROM tenants
                WHERE tenant_id = ?
                LIMIT 1
                """,
                (brief.tenant_id,),
            ).fetchone()

            if tenant is None:
                raise ValueError(f"Tenant '{brief.tenant_id}' does not exist.")

            brand = connection.execute(
                """
                SELECT tenant_id
                FROM brands
                WHERE brand_id = ?
                LIMIT 1
                """,
                (brief.brand_id,),
            ).fetchone()

        if brand is None:
            raise ValueError(f"Brand '{brief.brand_id}' does not exist.")

        if str(brand["tenant_id"]) != brief.tenant_id:
            raise ValueError(
                f"Brand '{brief.brand_id}' does not belong "
                f"to tenant '{brief.tenant_id}'."
            )

    @staticmethod
    def _required_text(
        field_name: str,
        value: str,
    ) -> str:
        if not isinstance(value, str):
            raise TypeError(f"{field_name} must be a string.")

        cleaned_value = value.strip()

        if not cleaned_value:
            raise ValueError(f"{field_name} is required.")

        return cleaned_value

    @staticmethod
    def _optional_text(
        value: str | None,
    ) -> str | None:
        if value is None:
            return None

        if not isinstance(value, str):
            raise TypeError("filter values must be strings.")

        return value.strip() or None

    @staticmethod
    def _validate_version(
        version: int | None,
    ) -> None:
        if version is None:
            return

        if isinstance(version, bool) or not isinstance(version, int):
            raise TypeError("version must be an integer.")

        if version < 1:
            raise ValueError("version must be at least 1.")

    @staticmethod
    def _brief_from_payload(
        payload_json: str,
    ) -> MarketingBrief:
        payload = decode_json(payload_json)

        if not isinstance(payload, dict):
            raise ValueError("Invalid stored Marketing Brief payload.")

        return MarketingBrief.from_dict(payload)
