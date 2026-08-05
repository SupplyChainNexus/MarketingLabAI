"""Operator CLI for recovery evidence and the synthetic release gate."""

from __future__ import annotations

import argparse
import json

from app.database.connection import SQLiteDatabase
from app.operations.configuration import PilotConfiguration
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
    arguments = parser.parse_args()
    config = PilotConfiguration.from_environment()
    database = SQLiteDatabase(config.database_path)
    recovery = SQLiteRecoveryService(database, config.backup_directory)
    if arguments.command == "backup":
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
