"""Immutable, privacy-safe operational readiness evidence."""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import uuid4

from app.database.connection import SQLiteDatabase


def _required(value: str, name: str, maximum: int = 256) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} is required.")
    selected = value.strip()
    if len(selected) > maximum:
        raise ValueError(f"{name} must be at most {maximum} characters.")
    return selected


def _timestamp(value: str, name: str) -> str:
    selected = _required(value, name, 64)
    try:
        parsed = datetime.fromisoformat(selected.replace("Z", "+00:00"))
    except ValueError as error:
        raise ValueError(f"{name} must be an ISO-8601 timestamp.") from error
    if parsed.tzinfo is None:
        raise ValueError(f"{name} must include a timezone.")
    return parsed.astimezone(UTC).isoformat()


@dataclass(frozen=True, slots=True)
class ReadinessEvidence:
    check_name: str
    environment: str
    commit_sha: str
    operator_id: str
    passed: bool
    evidence_reference: str
    observed_at: str
    expires_at: str
    failure_classification: str = ""
    remediation: str = ""
    evidence_id: str = ""

    def __post_init__(self) -> None:
        object.__setattr__(self, "check_name", _required(self.check_name, "check_name"))
        object.__setattr__(
            self, "environment", _required(self.environment, "environment")
        )
        commit = _required(self.commit_sha, "commit_sha", 64).lower()
        if not re.fullmatch(r"[0-9a-f]{7,40}", commit):
            raise ValueError("commit_sha must be a 7 to 40 character Git SHA.")
        object.__setattr__(self, "commit_sha", commit)
        object.__setattr__(
            self, "operator_id", _required(self.operator_id, "operator_id")
        )
        if not isinstance(self.passed, bool):
            raise TypeError("passed must be a boolean.")
        reference = _required(self.evidence_reference, "evidence_reference", 512)
        if any(
            term in reference.lower() for term in ("token=", "secret=", "password=")
        ):
            raise ValueError("evidence_reference must not contain credentials.")
        object.__setattr__(self, "evidence_reference", reference)
        observed = _timestamp(self.observed_at, "observed_at")
        expires = _timestamp(self.expires_at, "expires_at")
        if datetime.fromisoformat(expires) <= datetime.fromisoformat(observed):
            raise ValueError("expires_at must be later than observed_at.")
        object.__setattr__(self, "observed_at", observed)
        object.__setattr__(self, "expires_at", expires)
        failure = self.failure_classification.strip()
        remediation = self.remediation.strip()
        if not self.passed and (not failure or not remediation):
            raise ValueError("Failed evidence requires classification and remediation.")
        object.__setattr__(self, "failure_classification", failure)
        object.__setattr__(self, "remediation", remediation)
        object.__setattr__(self, "evidence_id", self.evidence_id or str(uuid4()))

    def is_current(self, *, environment: str, commit_sha: str, now: datetime) -> bool:
        return (
            self.passed
            and self.environment == environment
            and self.commit_sha == commit_sha.lower()
            and datetime.fromisoformat(self.expires_at) > now.astimezone(UTC)
        )


class ReadinessEvidenceRepository:
    def __init__(
        self, database: SQLiteDatabase, *, ensure_initialised: bool = True
    ) -> None:
        if not isinstance(database, SQLiteDatabase):
            raise TypeError("database must be a SQLiteDatabase.")
        self.database = database
        if ensure_initialised:
            self.database.ensure_initialised()

    def add(self, evidence: ReadinessEvidence) -> None:
        if not isinstance(evidence, ReadinessEvidence):
            raise TypeError("evidence must be ReadinessEvidence.")
        with self.database.transaction() as connection:
            connection.execute(
                """
                INSERT INTO pilot_readiness_evidence (
                    evidence_id, check_name, environment, commit_sha,
                    operator_id, passed, evidence_reference, observed_at,
                    expires_at, failure_classification, remediation, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    evidence.evidence_id,
                    evidence.check_name,
                    evidence.environment,
                    evidence.commit_sha,
                    evidence.operator_id,
                    int(evidence.passed),
                    evidence.evidence_reference,
                    evidence.observed_at,
                    evidence.expires_at,
                    evidence.failure_classification,
                    evidence.remediation,
                    datetime.now(UTC).isoformat(),
                ),
            )

    def latest(self, check_name: str) -> ReadinessEvidence | None:
        with self.database.connection() as connection:
            row = connection.execute(
                """
                SELECT * FROM pilot_readiness_evidence
                WHERE check_name = ?
                ORDER BY observed_at DESC, created_at DESC LIMIT 1
                """,
                (_required(check_name, "check_name"),),
            ).fetchone()
        if row is None:
            return None
        return ReadinessEvidence(
            evidence_id=str(row["evidence_id"]),
            check_name=str(row["check_name"]),
            environment=str(row["environment"]),
            commit_sha=str(row["commit_sha"]),
            operator_id=str(row["operator_id"]),
            passed=bool(row["passed"]),
            evidence_reference=str(row["evidence_reference"]),
            observed_at=str(row["observed_at"]),
            expires_at=str(row["expires_at"]),
            failure_classification=str(row["failure_classification"]),
            remediation=str(row["remediation"]),
        )

    def current_passes(
        self,
        check_names: tuple[str, ...],
        *,
        environment: str,
        commit_sha: str,
        now: datetime | None = None,
    ) -> dict[str, bool]:
        selected_now = now or datetime.now(UTC)
        return {
            name: bool(
                (item := self.latest(name))
                and item.is_current(
                    environment=environment, commit_sha=commit_sha, now=selected_now
                )
            )
            for name in check_names
        }
