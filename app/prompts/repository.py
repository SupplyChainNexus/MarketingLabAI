"""SQLite persistence for versioned Prompt Packs."""

from __future__ import annotations

from typing import Any

from app.database.connection import SQLiteDatabase
from app.database.repositories import decode_json, encode_json
from app.prompts.models import PromptPack


class PromptPackRepository:
    """Store immutable versions of tenant-owned Prompt Packs."""

    def __init__(
        self,
        database: SQLiteDatabase | None = None,
    ) -> None:
        self.database = database or SQLiteDatabase()
        self.database.initialise()

    def save(self, prompt_pack: PromptPack) -> None:
        """Persist a new Prompt Pack version."""

        if not isinstance(prompt_pack, PromptPack):
            raise TypeError("prompt_pack must be a PromptPack.")

        self._validate_ownership(prompt_pack)

        payload = prompt_pack.to_dict()

        try:
            with self.database.transaction() as connection:
                connection.execute(
                    """
                    INSERT INTO prompt_packs (
                        prompt_pack_id,
                        version,
                        tenant_id,
                        brand_id,
                        name,
                        task_type,
                        channel,
                        enabled,
                        payload_json,
                        created_at,
                        updated_at
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        prompt_pack.prompt_pack_id,
                        prompt_pack.version,
                        prompt_pack.tenant_id,
                        prompt_pack.brand_id,
                        prompt_pack.name,
                        prompt_pack.task_type,
                        prompt_pack.channel,
                        int(prompt_pack.enabled),
                        encode_json(payload),
                        prompt_pack.created_at,
                        prompt_pack.updated_at,
                    ),
                )
        except Exception as error:
            if "UNIQUE constraint failed" in str(error):
                raise ValueError(
                    f"Prompt Pack "
                    f"'{prompt_pack.prompt_pack_id}' "
                    f"version {prompt_pack.version} "
                    "already exists."
                ) from error

            raise

    def get(
        self,
        prompt_pack_id: str,
        *,
        tenant_id: str,
        version: int | None = None,
    ) -> PromptPack:
        """Return a specific version or the latest tenant version."""

        prompt_pack_id = self._required_text(
            "prompt_pack_id",
            prompt_pack_id,
        )
        tenant_id = self._required_text(
            "tenant_id",
            tenant_id,
        )

        if version is not None and version < 1:
            raise ValueError("version must be at least 1.")

        if version is None:
            query = """
                SELECT payload_json
                FROM prompt_packs
                WHERE prompt_pack_id = ?
                  AND tenant_id = ?
                ORDER BY version DESC
                LIMIT 1
            """
            parameters: tuple[Any, ...] = (
                prompt_pack_id,
                tenant_id,
            )
        else:
            query = """
                SELECT payload_json
                FROM prompt_packs
                WHERE prompt_pack_id = ?
                  AND tenant_id = ?
                  AND version = ?
            """
            parameters = (
                prompt_pack_id,
                tenant_id,
                version,
            )

        with self.database.connection() as connection:
            row = connection.execute(
                query,
                parameters,
            ).fetchone()

        if row is None:
            if version is None:
                raise FileNotFoundError(
                    f"No Prompt Pack exists with ID "
                    f"'{prompt_pack_id}' for tenant "
                    f"'{tenant_id}'."
                )

            raise FileNotFoundError(
                f"No Prompt Pack exists with ID "
                f"'{prompt_pack_id}', tenant "
                f"'{tenant_id}', and version {version}."
            )

        return self._pack_from_payload(str(row["payload_json"]))

    def list_versions(
        self,
        prompt_pack_id: str,
        *,
        tenant_id: str,
    ) -> list[PromptPack]:
        """Return all tenant versions in ascending order."""

        prompt_pack_id = self._required_text(
            "prompt_pack_id",
            prompt_pack_id,
        )
        tenant_id = self._required_text(
            "tenant_id",
            tenant_id,
        )

        with self.database.connection() as connection:
            rows = connection.execute(
                """
                SELECT payload_json
                FROM prompt_packs
                WHERE prompt_pack_id = ?
                  AND tenant_id = ?
                ORDER BY version
                """,
                (
                    prompt_pack_id,
                    tenant_id,
                ),
            ).fetchall()

        return [self._pack_from_payload(str(row["payload_json"])) for row in rows]

    def list_for_tenant(
        self,
        tenant_id: str,
        *,
        brand_id: str | None = None,
        task_type: str | None = None,
        channel: str | None = None,
        enabled_only: bool = True,
    ) -> list[PromptPack]:
        """Return the latest matching version of each tenant pack."""

        tenant_id = self._required_text(
            "tenant_id",
            tenant_id,
        )
        brand_id = self._optional_filter(
            brand_id,
        )
        task_type = self._optional_filter(
            task_type,
        )
        channel = self._optional_filter(
            channel,
        )

        filters = [
            "current.tenant_id = ?",
        ]
        parameters: list[Any] = [
            tenant_id,
            tenant_id,
        ]

        if brand_id is not None:
            filters.append("current.brand_id = ?")
            parameters.append(brand_id)

        if task_type is not None:
            filters.append("current.task_type = ?")
            parameters.append(task_type)

        if channel is not None:
            filters.append("current.channel = ?")
            parameters.append(channel)

        if enabled_only:
            filters.append("current.enabled = 1")

        where_clause = " AND ".join(filters)

        query = f"""
            SELECT current.payload_json
            FROM prompt_packs AS current
            INNER JOIN (
                SELECT
                    prompt_pack_id,
                    tenant_id,
                    MAX(version) AS latest_version
                FROM prompt_packs
                WHERE tenant_id = ?
                GROUP BY prompt_pack_id, tenant_id
            ) AS latest
                ON current.prompt_pack_id =
                    latest.prompt_pack_id
               AND current.tenant_id =
                    latest.tenant_id
               AND current.version =
                    latest.latest_version
            WHERE {where_clause}
            ORDER BY current.prompt_pack_id
        """

        with self.database.connection() as connection:
            rows = connection.execute(
                query,
                tuple(parameters),
            ).fetchall()

        return [self._pack_from_payload(str(row["payload_json"])) for row in rows]

    def exists(
        self,
        prompt_pack_id: str,
        *,
        tenant_id: str,
        version: int | None = None,
    ) -> bool:
        """Return whether a tenant Prompt Pack version exists."""

        prompt_pack_id = self._required_text(
            "prompt_pack_id",
            prompt_pack_id,
        )
        tenant_id = self._required_text(
            "tenant_id",
            tenant_id,
        )

        if version is not None and version < 1:
            raise ValueError("version must be at least 1.")

        if version is None:
            query = """
                SELECT 1
                FROM prompt_packs
                WHERE prompt_pack_id = ?
                  AND tenant_id = ?
                LIMIT 1
            """
            parameters: tuple[Any, ...] = (
                prompt_pack_id,
                tenant_id,
            )
        else:
            query = """
                SELECT 1
                FROM prompt_packs
                WHERE prompt_pack_id = ?
                  AND tenant_id = ?
                  AND version = ?
                LIMIT 1
            """
            parameters = (
                prompt_pack_id,
                tenant_id,
                version,
            )

        with self.database.connection() as connection:
            row = connection.execute(
                query,
                parameters,
            ).fetchone()

        return row is not None

    def count(
        self,
        *,
        tenant_id: str | None = None,
    ) -> int:
        """Return the number of stored Prompt Pack versions."""

        if tenant_id is None:
            query = "SELECT COUNT(*) AS total " "FROM prompt_packs"
            parameters: tuple[Any, ...] = ()
        else:
            tenant_id = self._required_text(
                "tenant_id",
                tenant_id,
            )
            query = """
                SELECT COUNT(*) AS total
                FROM prompt_packs
                WHERE tenant_id = ?
            """
            parameters = (tenant_id,)

        with self.database.connection() as connection:
            row = connection.execute(
                query,
                parameters,
            ).fetchone()

        return int(row["total"]) if row else 0

    def _validate_ownership(
        self,
        prompt_pack: PromptPack,
    ) -> None:
        """Validate tenant existence and optional brand ownership."""

        with self.database.connection() as connection:
            tenant = connection.execute(
                """
                SELECT 1
                FROM tenants
                WHERE tenant_id = ?
                LIMIT 1
                """,
                (prompt_pack.tenant_id,),
            ).fetchone()

            if tenant is None:
                raise ValueError(f"Tenant '{prompt_pack.tenant_id}' " "does not exist.")

            if prompt_pack.brand_id is None:
                return

            brand = connection.execute(
                """
                SELECT tenant_id
                FROM brands
                WHERE brand_id = ?
                LIMIT 1
                """,
                (prompt_pack.brand_id,),
            ).fetchone()

        if brand is None:
            raise ValueError(f"Brand '{prompt_pack.brand_id}' " "does not exist.")

        if str(brand["tenant_id"]) != prompt_pack.tenant_id:
            raise ValueError(
                f"Brand '{prompt_pack.brand_id}' "
                "does not belong to tenant "
                f"'{prompt_pack.tenant_id}'."
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
    def _optional_filter(
        value: str | None,
    ) -> str | None:
        if value is None:
            return None

        if not isinstance(value, str):
            raise TypeError("filter values must be strings.")

        return value.strip() or None

    @staticmethod
    def _pack_from_payload(
        payload_json: str,
    ) -> PromptPack:
        payload = decode_json(payload_json)

        if not isinstance(payload, dict):
            raise ValueError("Invalid stored Prompt Pack payload.")

        return PromptPack.from_dict(payload)
