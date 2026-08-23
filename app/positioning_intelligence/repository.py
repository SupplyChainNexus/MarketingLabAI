"""Tenant-scoped SQLite persistence for Positioning Intelligence."""

from __future__ import annotations

import json
import sqlite3

from app.database.connection import SQLiteDatabase
from app.positioning_intelligence.models import PositioningDecision


def _identifier(value: str, name: str) -> str:
    if not isinstance(value, str):
        raise TypeError(f"{name} must be a string.")
    cleaned = value.strip()
    if not cleaned:
        raise ValueError(f"{name} is required.")
    return cleaned


class PositioningRepository:
    def __init__(self, database: SQLiteDatabase | None = None) -> None:
        self.database = database or SQLiteDatabase()

    def save(self, decision: PositioningDecision) -> None:
        if not isinstance(decision, PositioningDecision):
            raise TypeError("decision must be a PositioningDecision.")
        with self.database.connection() as connection:
            brand = connection.execute(
                "SELECT tenant_id FROM brands WHERE brand_id = ?",
                (decision.brand_id,),
            ).fetchone()
        if brand is None:
            raise ValueError(f"Brand {decision.brand_id!r} does not exist.")
        if str(brand["tenant_id"]) != decision.tenant_id:
            raise ValueError("Positioning tenant and brand differ.")
        payload = json.dumps(decision.to_dict(), ensure_ascii=False, sort_keys=True)
        try:
            with self.database.transaction() as connection:
                connection.execute(
                    """
                    INSERT INTO positioning_decisions (
                        positioning_id, version, tenant_id, brand_id,
                        target_kind, target_id, product_id, status,
                        payload_json, created_at, updated_at, approved_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        decision.positioning_id,
                        decision.version,
                        decision.tenant_id,
                        decision.brand_id,
                        decision.target_kind.value,
                        decision.target_id,
                        decision.product_id,
                        decision.status.value,
                        payload,
                        decision.created_at,
                        decision.updated_at,
                        decision.approved_at or None,
                    ),
                )
        except sqlite3.IntegrityError as error:
            message = "Positioning versions are immutable and must be unique."
            raise ValueError(message) from error

    def get(
        self, *, tenant_id: str, positioning_id: str, version: int
    ) -> PositioningDecision:
        tenant_id = _identifier(tenant_id, "tenant_id")
        positioning_id = _identifier(positioning_id, "positioning_id")
        with self.database.connection() as connection:
            row = connection.execute(
                """SELECT payload_json FROM positioning_decisions
                   WHERE tenant_id = ? AND positioning_id = ? AND version = ?""",
                (tenant_id, positioning_id, version),
            ).fetchone()
        if row is None:
            raise FileNotFoundError("Positioning decision was not found.")
        return PositioningDecision.from_dict(json.loads(row["payload_json"]))

    def latest(self, *, tenant_id: str, positioning_id: str) -> PositioningDecision:
        tenant_id = _identifier(tenant_id, "tenant_id")
        positioning_id = _identifier(positioning_id, "positioning_id")
        with self.database.connection() as connection:
            row = connection.execute(
                """SELECT payload_json FROM positioning_decisions
                   WHERE tenant_id = ? AND positioning_id = ?
                   ORDER BY version DESC LIMIT 1""",
                (tenant_id, positioning_id),
            ).fetchone()
        if row is None:
            raise FileNotFoundError("Positioning decision was not found.")
        return PositioningDecision.from_dict(json.loads(row["payload_json"]))

    def list_latest_for_brand(
        self, *, tenant_id: str, brand_id: str
    ) -> list[PositioningDecision]:
        tenant_id = _identifier(tenant_id, "tenant_id")
        brand_id = _identifier(brand_id, "brand_id")
        with self.database.connection() as connection:
            rows = connection.execute(
                """
                SELECT decision.payload_json
                FROM positioning_decisions AS decision
                JOIN (
                    SELECT positioning_id, MAX(version) AS latest_version
                    FROM positioning_decisions
                    WHERE tenant_id = ? AND brand_id = ?
                    GROUP BY positioning_id
                ) AS latest
                  ON latest.positioning_id = decision.positioning_id
                 AND latest.latest_version = decision.version
                WHERE decision.tenant_id = ? AND decision.brand_id = ?
                ORDER BY decision.positioning_id
                """,
                (tenant_id, brand_id, tenant_id, brand_id),
            ).fetchall()
        return [
            PositioningDecision.from_dict(json.loads(row["payload_json"]))
            for row in rows
        ]
