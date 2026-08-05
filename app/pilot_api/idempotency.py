"""SQLite idempotency records for retry-safe pilot operations."""

from __future__ import annotations

import json
from dataclasses import dataclass

from app.database.connection import SQLiteDatabase


class IdempotencyConflictError(RuntimeError):
    """Raised when a key is reused for a different request."""


@dataclass(slots=True, frozen=True)
class StoredApiResponse:
    request_hash: str
    status: int
    data: dict


class IdempotencyRepository:
    def __init__(self, database: SQLiteDatabase) -> None:
        self.database = database
        self.database.initialise()

    def get(
        self,
        *,
        tenant_id: str,
        provider: str,
        subject_id: str,
        operation: str,
        idempotency_key: str,
    ) -> StoredApiResponse | None:
        with self.database.connection() as connection:
            row = connection.execute(
                """
                SELECT request_hash, response_status, response_json
                FROM api_idempotency_records
                WHERE tenant_id = ? AND provider = ? AND subject_id = ?
                  AND operation = ? AND idempotency_key = ?
                """,
                (tenant_id, provider, subject_id, operation, idempotency_key),
            ).fetchone()
        if row is None:
            return None
        return StoredApiResponse(
            request_hash=str(row["request_hash"]),
            status=int(row["response_status"]),
            data=json.loads(str(row["response_json"])),
        )

    def save(
        self,
        *,
        tenant_id: str,
        provider: str,
        subject_id: str,
        operation: str,
        idempotency_key: str,
        request_hash: str,
        status: int,
        data: dict,
    ) -> None:
        with self.database.transaction() as connection:
            connection.execute(
                """
                INSERT INTO api_idempotency_records
                    (tenant_id, provider, subject_id, operation, idempotency_key,
                     request_hash, response_status, response_json, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?,
                        strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
                """,
                (
                    tenant_id,
                    provider,
                    subject_id,
                    operation,
                    idempotency_key,
                    request_hash,
                    status,
                    json.dumps(data, ensure_ascii=False, sort_keys=True),
                ),
            )
