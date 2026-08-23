"""Tenant-scoped SQLite persistence for Marketing Strategy Intelligence."""

from __future__ import annotations

import json
import sqlite3

from app.database.connection import SQLiteDatabase
from app.strategy_intelligence.models import StrategyDecision


def _identifier(value: str, name: str) -> str:
    if not isinstance(value, str):
        raise TypeError(f"{name} must be a string.")
    cleaned = value.strip()
    if not cleaned:
        raise ValueError(f"{name} is required.")
    return cleaned


class StrategyRepository:
    def __init__(self, database: SQLiteDatabase | None = None) -> None:
        self.database = database or SQLiteDatabase()

    def save(self, decision: StrategyDecision) -> None:
        if not isinstance(decision, StrategyDecision):
            raise TypeError("decision must be a StrategyDecision.")
        with self.database.connection() as connection:
            brand = connection.execute(
                "SELECT tenant_id FROM brands WHERE brand_id = ?",
                (decision.brand_id,),
            ).fetchone()
        if brand is None:
            raise ValueError(f"Brand {decision.brand_id!r} does not exist.")
        if str(brand["tenant_id"]) != decision.tenant_id:
            raise ValueError("Strategy tenant and brand differ.")
        payload = json.dumps(decision.to_dict(), ensure_ascii=False, sort_keys=True)
        try:
            with self.database.transaction() as connection:
                connection.execute(
                    """
                    INSERT INTO strategy_decisions (
                        strategy_id, version, tenant_id, brand_id,
                        positioning_id, positioning_version, status,
                        payload_json, created_at, updated_at, approved_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        decision.strategy_id,
                        decision.version,
                        decision.tenant_id,
                        decision.brand_id,
                        decision.positioning_id,
                        decision.positioning_version,
                        decision.status.value,
                        payload,
                        decision.created_at,
                        decision.updated_at,
                        decision.approved_at or None,
                    ),
                )
        except sqlite3.IntegrityError as error:
            raise ValueError(
                "Strategy versions are immutable and must be unique."
            ) from error

    def get(
        self, *, tenant_id: str, strategy_id: str, version: int
    ) -> StrategyDecision:
        tenant_id = _identifier(tenant_id, "tenant_id")
        strategy_id = _identifier(strategy_id, "strategy_id")
        with self.database.connection() as connection:
            row = connection.execute(
                """SELECT payload_json FROM strategy_decisions
                   WHERE tenant_id = ? AND strategy_id = ? AND version = ?""",
                (tenant_id, strategy_id, version),
            ).fetchone()
        if row is None:
            raise FileNotFoundError("Strategy decision was not found.")
        return StrategyDecision.from_dict(json.loads(row["payload_json"]))

    def latest(self, *, tenant_id: str, strategy_id: str) -> StrategyDecision:
        tenant_id = _identifier(tenant_id, "tenant_id")
        strategy_id = _identifier(strategy_id, "strategy_id")
        with self.database.connection() as connection:
            row = connection.execute(
                """SELECT payload_json FROM strategy_decisions
                   WHERE tenant_id = ? AND strategy_id = ?
                   ORDER BY version DESC LIMIT 1""",
                (tenant_id, strategy_id),
            ).fetchone()
        if row is None:
            raise FileNotFoundError("Strategy decision was not found.")
        return StrategyDecision.from_dict(json.loads(row["payload_json"]))

    def list_latest_for_brand(
        self, *, tenant_id: str, brand_id: str
    ) -> list[StrategyDecision]:
        tenant_id = _identifier(tenant_id, "tenant_id")
        brand_id = _identifier(brand_id, "brand_id")
        with self.database.connection() as connection:
            rows = connection.execute(
                """
                SELECT decision.payload_json
                FROM strategy_decisions AS decision
                JOIN (
                    SELECT strategy_id, MAX(version) AS latest_version
                    FROM strategy_decisions
                    WHERE tenant_id = ? AND brand_id = ?
                    GROUP BY strategy_id
                ) AS latest
                  ON latest.strategy_id = decision.strategy_id
                 AND latest.latest_version = decision.version
                WHERE decision.tenant_id = ? AND decision.brand_id = ?
                ORDER BY decision.strategy_id
                """,
                (tenant_id, brand_id, tenant_id, brand_id),
            ).fetchall()
        return [
            StrategyDecision.from_dict(json.loads(row["payload_json"])) for row in rows
        ]
