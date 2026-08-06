"""Operator CLI for recovery evidence and the synthetic release gate."""

from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime, timedelta

from app.database.factory import create_database
from app.database.postgresql import PostgreSQLDatabase
from app.operations.configuration import PilotConfiguration
from app.operations.readiness_evidence import (
    ReadinessEvidence,
    ReadinessEvidenceRepository,
)
from app.operations.recovery import SQLiteRecoveryService
from app.operations.release_gate import PilotReleaseGate


def main() -> int:
    parser = argparse.ArgumentParser()
    subcommands = parser.add_subparsers(dest="command", required=True)
    subcommands.add_parser("backup")
    restore = subcommands.add_parser("restore")
    restore.add_argument("backup_path")
    restore.add_argument("destination")
    subcommands.add_parser("release-gate")
    evidence = subcommands.add_parser("record-evidence")
    evidence.add_argument("check_name")
    evidence.add_argument("operator_id")
    evidence.add_argument("result", choices=("pass", "fail"))
    evidence.add_argument("evidence_reference")
    evidence.add_argument("--valid-days", type=int, default=30)
    evidence.add_argument("--failure-classification", default="")
    evidence.add_argument("--remediation", default="")
    arguments = parser.parse_args()
    config = PilotConfiguration.from_environment()
    database = create_database(
        backend=config.persistence_backend,
        database_path=config.database_path,
        database_url=config.database_url,
    )
    if arguments.command == "record-evidence":
        if config.deployment_commit == "unrecorded":
            raise ValueError("MLAI_DEPLOYMENT_COMMIT must be recorded first.")
        if arguments.valid_days < 1 or arguments.valid_days > 90:
            raise ValueError("--valid-days must be between 1 and 90.")
        observed = datetime.now(UTC)
        item = ReadinessEvidence(
            check_name=arguments.check_name,
            environment=config.environment,
            commit_sha=config.deployment_commit,
            operator_id=arguments.operator_id,
            passed=arguments.result == "pass",
            evidence_reference=arguments.evidence_reference,
            observed_at=observed.isoformat(),
            expires_at=(observed + timedelta(days=arguments.valid_days)).isoformat(),
            failure_classification=arguments.failure_classification,
            remediation=arguments.remediation,
        )
        ReadinessEvidenceRepository(database).add(item)
        print(
            json.dumps(
                {
                    "evidence_id": item.evidence_id,
                    "check_name": item.check_name,
                    "passed": item.passed,
                    "environment": item.environment,
                    "commit_sha": item.commit_sha,
                    "expires_at": item.expires_at,
                },
                sort_keys=True,
            )
        )
        return 0
    if arguments.command == "backup":
        if isinstance(database, PostgreSQLDatabase):
            raise RuntimeError(
                "PostgreSQL backup must use the approved managed-database backup runbook."
            )
        recovery = SQLiteRecoveryService(database, config.backup_directory)
        evidence = recovery.create_backup()
        print(
            json.dumps(
                {
                    "path": str(evidence.path),
                    "sha256": evidence.sha256,
                    "integrity": evidence.integrity,
                },
                sort_keys=True,
            )
        )
        return 0
    if arguments.command == "restore":
        if isinstance(database, PostgreSQLDatabase):
            raise RuntimeError(
                "PostgreSQL restore must use an isolated approved managed-database target."
            )
        recovery = SQLiteRecoveryService(database, config.backup_directory)
        restored = recovery.restore_to(arguments.backup_path, arguments.destination)
        print(
            json.dumps({"restored": str(restored), "integrity": "ok"}, sort_keys=True)
        )
        return 0
    report = PilotReleaseGate(config, database).evaluate()
    print(json.dumps(report.to_dict(), sort_keys=True))
    return 0 if report.synthetic_pilot_ready else 1


if __name__ == "__main__":
    raise SystemExit(main())
