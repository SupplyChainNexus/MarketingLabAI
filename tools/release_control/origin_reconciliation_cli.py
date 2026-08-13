"""CLI adapter for ORIGIN_RECONCILED planning."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Mapping

from tools.release_control.config import ControlConfig
from tools.release_control.origin_reconciliation import (
    OriginReconciliationInputs,
    prepare_origin_reconciliation,
    write_origin_reconciliation_plan,
)
from tools.release_control.store import sha256_file


def _read_json(path: Path) -> Mapping[str, object]:
    value = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(value, dict):
        raise ValueError(f"Expected JSON object: {path}")
    return value


def prepare_origin_reconciliation_from_cli(
    *,
    config: ControlConfig,
    state_root: Path,
    startup_origin_inspection: Path,
    revision_created_evidence: Path,
    output_root: Path,
    browser_api_key: str | None = None,
    oauth_client_id: str | None = None,
) -> dict[str, object]:
    """Prepare ORIGIN_RECONCILED without cloud execution or release-state writes."""

    browser = browser_api_key or os.environ.get("MLAI_BROWSER_API_KEY", "")
    oauth = oauth_client_id or os.environ.get("MLAI_GOOGLE_OAUTH_CLIENT_ID", "")
    if not browser:
        raise ValueError("MLAI_BROWSER_API_KEY is required for manifest rendering.")
    if not oauth:
        raise ValueError(
            "MLAI_GOOGLE_OAUTH_CLIENT_ID is required for manifest rendering."
        )

    index = _read_json(state_root / "release-index.json")
    release = index.get("release")
    if not isinstance(release, dict):
        raise ValueError("Release index is missing release identity.")

    plan = prepare_origin_reconciliation(
        configuration=config.payload["revision_creation"],
        release=release,
        revision_created_evidence=_read_json(revision_created_evidence),
        startup_origin_inspection=_read_json(startup_origin_inspection),
        repository_root=config.repository_root,
        output_root=output_root,
        inputs=OriginReconciliationInputs(
            restricted_browser_api_key=browser,
            google_oauth_client_id=oauth,
        ),
    )
    plan["startup_origin_inspection_sha256"] = sha256_file(startup_origin_inspection)
    plan["revision_created_evidence_sha256"] = sha256_file(revision_created_evidence)
    plan_path = (
        state_root / "origin-reconciliation-plans" / f"{plan['manifest_sha256']}.json"
    )
    plan["origin_reconciliation_plan_path"] = str(plan_path.resolve())
    plan_sha256 = write_origin_reconciliation_plan(plan_path, plan)
    plan["origin_reconciliation_plan_sha256"] = plan_sha256
    return plan
