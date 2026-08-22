"""SQLite persistence for versioned compliance rules."""

from __future__ import annotations

from typing import Any

from app.compliance.models import BrandRule
from app.database.connection import SQLiteDatabase
from app.database.repositories import decode_json, encode_json


class BrandRuleRepository:
    """Store immutable versions of brand compliance rules."""

    def __init__(self, database: SQLiteDatabase | None = None) -> None:
        self.database = database or SQLiteDatabase()
        self.database.ensure_initialised()

    def save(self, rule: BrandRule) -> None:
        """Persist a new rule version without overwriting history."""

        payload = rule.to_dict()

        try:
            with self.database.transaction() as connection:
                connection.execute(
                    """
                    INSERT INTO compliance_rules (
                        rule_id,
                        version,
                        brand_id,
                        name,
                        category,
                        severity,
                        evaluation_method,
                        enabled,
                        evidence_required,
                        payload_json,
                        created_at,
                        updated_at
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        rule.rule_id,
                        rule.version,
                        rule.brand_id,
                        rule.name,
                        rule.category,
                        rule.severity.value,
                        rule.evaluation_method.value,
                        int(rule.enabled),
                        int(rule.evidence_required),
                        encode_json(payload),
                        rule.created_at,
                        rule.updated_at,
                    ),
                )
        except Exception as error:
            if "UNIQUE constraint failed" in str(error):
                raise ValueError(
                    f"Rule '{rule.rule_id}' version {rule.version} already exists."
                ) from error
            raise

    def get(
        self,
        rule_id: str,
        version: int | None = None,
    ) -> BrandRule:
        """Return a specific version or the latest available version."""

        if version is None:
            query = """
                SELECT payload_json
                FROM compliance_rules
                WHERE rule_id = ?
                ORDER BY version DESC
                LIMIT 1
            """
            parameters: tuple[Any, ...] = (rule_id,)
        else:
            query = """
                SELECT payload_json
                FROM compliance_rules
                WHERE rule_id = ?
                  AND version = ?
            """
            parameters = (rule_id, version)

        with self.database.connection() as connection:
            row = connection.execute(query, parameters).fetchone()

        if row is None:
            if version is None:
                raise FileNotFoundError(
                    f"No compliance rule exists with ID '{rule_id}'."
                )

            raise FileNotFoundError(
                f"No compliance rule exists with ID '{rule_id}' "
                f"and version {version}."
            )

        return self._rule_from_payload(str(row["payload_json"]))

    def list_versions(self, rule_id: str) -> list[BrandRule]:
        """Return every stored version of a rule in ascending order."""

        with self.database.connection() as connection:
            rows = connection.execute(
                """
                SELECT payload_json
                FROM compliance_rules
                WHERE rule_id = ?
                ORDER BY version
                """,
                (rule_id,),
            ).fetchall()

        return [self._rule_from_payload(str(row["payload_json"])) for row in rows]

    def list_for_brand(
        self,
        brand_id: str,
        *,
        enabled_only: bool = True,
    ) -> list[BrandRule]:
        """Return the latest version of each rule belonging to a brand."""

        enabled_clause = "AND current.enabled = 1" if enabled_only else ""

        query = f"""
            SELECT current.payload_json
            FROM compliance_rules AS current
            INNER JOIN (
                SELECT rule_id, MAX(version) AS latest_version
                FROM compliance_rules
                WHERE brand_id = ?
                GROUP BY rule_id
            ) AS latest
                ON current.rule_id = latest.rule_id
               AND current.version = latest.latest_version
            WHERE current.brand_id = ?
              {enabled_clause}
            ORDER BY current.rule_id
        """

        with self.database.connection() as connection:
            rows = connection.execute(
                query,
                (brand_id, brand_id),
            ).fetchall()

        return [self._rule_from_payload(str(row["payload_json"])) for row in rows]

    def exists(
        self,
        rule_id: str,
        version: int | None = None,
    ) -> bool:
        """Return whether a rule or specific version exists."""

        if version is None:
            query = """
                SELECT 1
                FROM compliance_rules
                WHERE rule_id = ?
                LIMIT 1
            """
            parameters: tuple[Any, ...] = (rule_id,)
        else:
            query = """
                SELECT 1
                FROM compliance_rules
                WHERE rule_id = ?
                  AND version = ?
                LIMIT 1
            """
            parameters = (rule_id, version)

        with self.database.connection() as connection:
            row = connection.execute(query, parameters).fetchone()

        return row is not None

    def count(self) -> int:
        """Return the total number of stored rule versions."""

        with self.database.connection() as connection:
            row = connection.execute(
                "SELECT COUNT(*) AS total FROM compliance_rules"
            ).fetchone()

        return int(row["total"]) if row else 0

    @staticmethod
    def _rule_from_payload(payload_json: str) -> BrandRule:
        payload = decode_json(payload_json)

        if not isinstance(payload, dict):
            raise ValueError("Invalid stored compliance rule payload.")

        return BrandRule.from_dict(payload)
