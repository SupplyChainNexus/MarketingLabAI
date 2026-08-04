"""SQLite persistence for immutable, versioned Campaign Plans."""

from __future__ import annotations

import json
from typing import Any

from app.campaign_planner.models import CampaignPlan
from app.database.connection import SQLiteDatabase


class CampaignPlanRepository:
    """Store immutable versions of tenant-owned Campaign Plans."""

    def __init__(self, database: SQLiteDatabase | None = None) -> None:
        self.database = database or SQLiteDatabase()
        self.database.initialise()

    def save(self, plan: CampaignPlan) -> None:
        if not isinstance(plan, CampaignPlan):
            raise TypeError("plan must be a CampaignPlan.")
        self._validate_ownership(plan)
        try:
            with self.database.transaction() as connection:
                connection.execute(
                    """
                    INSERT INTO campaign_plans (
                        campaign_id, version, tenant_id, brand_id, name,
                        status, payload_json, created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        plan.campaign_id, plan.version, plan.tenant_id,
                        plan.brand_id, plan.name, plan.status.value,
                        json.dumps(plan.to_dict(), ensure_ascii=False, sort_keys=True),
                        plan.created_at.isoformat(), plan.updated_at.isoformat(),
                    ),
                )
        except Exception as error:
            if "UNIQUE constraint failed" in str(error):
                raise ValueError(
                    f"Campaign Plan '{plan.campaign_id}' version "
                    f"{plan.version} already exists."
                ) from error
            raise

    def get(
        self,
        campaign_id: str,
        *,
        tenant_id: str,
        version: int | None = None,
    ) -> CampaignPlan:
        campaign_id = self._required_text("campaign_id", campaign_id)
        tenant_id = self._required_text("tenant_id", tenant_id)
        self._validate_version(version)
        if version is None:
            query = """
                SELECT payload_json FROM campaign_plans
                WHERE campaign_id = ? AND tenant_id = ?
                ORDER BY version DESC LIMIT 1
            """
            parameters: tuple[Any, ...] = (campaign_id, tenant_id)
        else:
            query = """
                SELECT payload_json FROM campaign_plans
                WHERE campaign_id = ? AND tenant_id = ? AND version = ?
            """
            parameters = (campaign_id, tenant_id, version)
        with self.database.connection() as connection:
            row = connection.execute(query, parameters).fetchone()
        if row is None:
            version_text = "" if version is None else f" version {version}"
            raise FileNotFoundError(
                f"No Campaign Plan '{campaign_id}'{version_text} "
                f"exists for tenant '{tenant_id}'."
            )
        return self._plan_from_payload(str(row["payload_json"]))

    def list_versions(self, campaign_id: str, *, tenant_id: str) -> list[CampaignPlan]:
        campaign_id = self._required_text("campaign_id", campaign_id)
        tenant_id = self._required_text("tenant_id", tenant_id)
        with self.database.connection() as connection:
            rows = connection.execute(
                """
                SELECT payload_json FROM campaign_plans
                WHERE campaign_id = ? AND tenant_id = ? ORDER BY version
                """,
                (campaign_id, tenant_id),
            ).fetchall()
        return [self._plan_from_payload(str(row["payload_json"])) for row in rows]

    def list_latest_for_brand(
        self,
        *,
        tenant_id: str,
        brand_id: str,
        status: str | None = None,
    ) -> list[CampaignPlan]:
        tenant_id = self._required_text("tenant_id", tenant_id)
        brand_id = self._required_text("brand_id", brand_id)
        if status is not None and not isinstance(status, str):
            raise TypeError("filter values must be strings.")
        status = status.strip() if status else None
        filters = ["current.tenant_id = ?", "current.brand_id = ?"]
        parameters: list[Any] = [tenant_id, brand_id, tenant_id, brand_id]
        if status:
            filters.append("current.status = ?")
            parameters.append(status)
        query = f"""
            SELECT current.payload_json
            FROM campaign_plans AS current
            INNER JOIN (
                SELECT campaign_id, tenant_id, MAX(version) AS latest_version
                FROM campaign_plans
                WHERE tenant_id = ? AND brand_id = ?
                GROUP BY campaign_id, tenant_id
            ) AS latest
              ON current.campaign_id = latest.campaign_id
             AND current.tenant_id = latest.tenant_id
             AND current.version = latest.latest_version
            WHERE {' AND '.join(filters)}
            ORDER BY current.campaign_id
        """
        with self.database.connection() as connection:
            rows = connection.execute(query, tuple(parameters)).fetchall()
        return [self._plan_from_payload(str(row["payload_json"])) for row in rows]

    def exists(
        self,
        campaign_id: str,
        *,
        tenant_id: str,
        version: int | None = None,
    ) -> bool:
        campaign_id = self._required_text("campaign_id", campaign_id)
        tenant_id = self._required_text("tenant_id", tenant_id)
        self._validate_version(version)
        query = "SELECT 1 FROM campaign_plans WHERE campaign_id = ? AND tenant_id = ?"
        parameters: tuple[Any, ...] = (campaign_id, tenant_id)
        if version is not None:
            query += " AND version = ?"
            parameters += (version,)
        query += " LIMIT 1"
        with self.database.connection() as connection:
            return connection.execute(query, parameters).fetchone() is not None

    def count(self, *, tenant_id: str | None = None) -> int:
        query = "SELECT COUNT(*) AS total FROM campaign_plans"
        parameters: tuple[Any, ...] = ()
        if tenant_id is not None:
            tenant_id = self._required_text("tenant_id", tenant_id)
            query += " WHERE tenant_id = ?"
            parameters = (tenant_id,)
        with self.database.connection() as connection:
            row = connection.execute(query, parameters).fetchone()
        return int(row["total"]) if row else 0

    def _validate_ownership(self, plan: CampaignPlan) -> None:
        with self.database.connection() as connection:
            tenant = connection.execute(
                "SELECT 1 FROM tenants WHERE tenant_id = ? LIMIT 1",
                (plan.tenant_id,),
            ).fetchone()
            if tenant is None:
                raise ValueError(f"Tenant '{plan.tenant_id}' does not exist.")
            brand = connection.execute(
                "SELECT tenant_id FROM brands WHERE brand_id = ? LIMIT 1",
                (plan.brand_id,),
            ).fetchone()
        if brand is None:
            raise ValueError(f"Brand '{plan.brand_id}' does not exist.")
        if str(brand["tenant_id"]) != plan.tenant_id:
            raise ValueError(
                f"Brand '{plan.brand_id}' does not belong to tenant '{plan.tenant_id}'."
            )

    @staticmethod
    def _required_text(field_name: str, value: str) -> str:
        if not isinstance(value, str):
            raise TypeError(f"{field_name} must be a string.")
        cleaned = value.strip()
        if not cleaned:
            raise ValueError(f"{field_name} is required.")
        return cleaned

    @staticmethod
    def _validate_version(version: int | None) -> None:
        if version is None:
            return
        if isinstance(version, bool) or not isinstance(version, int):
            raise TypeError("version must be an integer.")
        if version < 1:
            raise ValueError("version must be at least 1.")

    @staticmethod
    def _plan_from_payload(payload_json: str) -> CampaignPlan:
        payload = json.loads(payload_json)
        if not isinstance(payload, dict):
            raise ValueError("Invalid stored Campaign Plan payload.")
        return CampaignPlan.from_dict(payload)
