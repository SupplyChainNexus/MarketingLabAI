"""Raw Git-object export, corrective planning, and local policy diagnostics."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import zipfile
from datetime import UTC, datetime
from pathlib import Path, PurePosixPath
from typing import Any


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _sha256_file(path: Path) -> str:
    return _sha256_bytes(path.read_bytes())


def _canonical_bytes(value: dict[str, Any]) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")


def _load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(value, dict):
        raise TypeError(f"Expected JSON object: {path}")
    return value


def _assert_external(root: Path, candidate: Path, label: str) -> None:
    try:
        candidate.resolve().relative_to(root.resolve())
    except ValueError:
        return
    raise ValueError(f"{label} must be outside the repository.")


def _contains(parent: Path, candidate: Path) -> bool:
    try:
        candidate.resolve().relative_to(parent.resolve())
    except ValueError:
        return False
    return True


def _export_destinations(root: Path, output_root: Path) -> tuple[Path, Path]:
    """Return disjoint, unoccupied export destinations without rewriting suffixes."""
    root = root.resolve()
    output_root = output_root.resolve()
    name = output_root.name
    if (
        not name
        or name in {".", ".."}
        or name.rstrip(" .") != name
        or name.lower().endswith(".zip")
    ):
        raise ValueError("Output root name is ambiguous for ZIP derivation.")

    zip_path = Path(f"{output_root}.zip")
    for destination, label in (
        (output_root, "Output root"),
        (zip_path, "ZIP destination"),
    ):
        if _contains(root, destination) or _contains(destination, root):
            raise ValueError(f"{label} overlaps the repository source.")
    if output_root.exists():
        raise ValueError("Output root already exists.")
    if zip_path.exists():
        raise ValueError("ZIP destination already exists.")
    return output_root, zip_path


def _git(
    root: Path,
    arguments: list[str],
    *,
    check: bool = True,
    text: bool = True,
) -> subprocess.CompletedProcess[str] | subprocess.CompletedProcess[bytes]:
    completed = subprocess.run(
        ["git", *arguments],
        cwd=root,
        check=False,
        capture_output=True,
        text=text,
    )
    if check and completed.returncode != 0:
        stderr = (
            completed.stderr.strip()
            if isinstance(completed.stderr, str)
            else completed.stderr.decode("utf-8", errors="replace").strip()
        )
        raise ValueError(f"Git command failed: {' '.join(arguments)}: {stderr}")
    return completed


def _git_head(root: Path) -> str:
    return str(_git(root, ["rev-parse", "HEAD"]).stdout).strip()


def _safe_relative(value: str) -> Path:
    pure = PurePosixPath(value)
    if pure.is_absolute() or ".." in pure.parts or not pure.parts:
        raise ValueError(f"Unsafe repository path: {value}")
    return Path(*pure.parts)


def _tree(root: Path, commit: str) -> dict[str, dict[str, str]]:
    completed = _git(root, ["ls-tree", "-r", "-z", commit], text=False)
    raw = bytes(completed.stdout)
    entries: dict[str, dict[str, str]] = {}
    for record in raw.split(b"\0"):
        if not record:
            continue
        metadata, raw_path = record.split(b"\t", 1)
        mode, kind, object_id = metadata.decode("ascii").split(" ")
        path = raw_path.decode("utf-8")
        if kind == "blob":
            entries[path] = {"git_blob_id": object_id, "git_mode": mode}
    return entries


def _blob(root: Path, object_id: str) -> bytes:
    completed = _git(root, ["cat-file", "blob", object_id], text=False)
    return bytes(completed.stdout)


def _manifest_paths(path: Path) -> list[str]:
    manifest = _load_json(path)
    if manifest.get("schema_version") != 1:
        raise ValueError("Path manifest schema_version must be 1.")
    raw_paths = manifest.get("paths")
    if not isinstance(raw_paths, list) or not raw_paths:
        raise TypeError("Path manifest paths must be a non-empty list.")
    if not all(isinstance(item, str) for item in raw_paths):
        raise TypeError("Every path manifest entry must be a string.")
    paths = [PurePosixPath(item).as_posix() for item in raw_paths]
    for item in paths:
        _safe_relative(item)
    if len(paths) != len(set(paths)):
        raise ValueError("Path manifest contains duplicate paths.")
    return sorted(paths)


def _forbidden_evidence_path(path: str) -> bool:
    pure = PurePosixPath(path)
    lowered = pure.name.lower()
    return (
        lowered == ".env"
        or lowered.startswith(".env.")
        or pure.suffix.lower() in {".key", ".p12", ".pem", ".pfx"}
        or ("credential" in lowered and pure.suffix.lower() == ".json")
        or ("service-account" in lowered and pure.suffix.lower() == ".json")
    )


def export_commit_intake(
    root: Path,
    *,
    commit: str,
    path_manifest: Path,
    output_root: Path,
) -> dict[str, Any]:
    """Export explicit paths from raw Git blobs and verify the completed ZIP."""
    root = root.resolve()
    path_manifest = path_manifest.resolve()
    output_root, zip_path = _export_destinations(root, output_root)
    commit_type = str(_git(root, ["cat-file", "-t", commit]).stdout).strip()
    if commit_type != "commit":
        raise ValueError("Export source must be a Git commit.")
    paths = _manifest_paths(path_manifest)
    forbidden = [path for path in paths if _forbidden_evidence_path(path)]
    if forbidden:
        raise ValueError(f"Forbidden evidence path: {forbidden[0]}")
    tree = _tree(root, commit)
    missing = [path for path in paths if path not in tree]
    if missing:
        raise ValueError(f"Path is not a tracked blob at the commit: {missing[0]}")

    source_root = output_root / "source"
    output_root.mkdir(parents=True)
    source_root.mkdir()
    records: list[dict[str, Any]] = []
    for relative_name in paths:
        entry = tree[relative_name]
        data = _blob(root, entry["git_blob_id"])
        destination = source_root / _safe_relative(relative_name)
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(data)
        if _sha256_file(destination) != _sha256_bytes(data):
            raise ValueError(f"Exported bytes changed while writing: {relative_name}")
        records.append(
            {
                "git_blob_id": entry["git_blob_id"],
                "git_mode": entry["git_mode"],
                "path": relative_name,
                "sha256": _sha256_bytes(data),
                "size_bytes": len(data),
            }
        )

    manifest: dict[str, Any] = {
        "file_count": len(records),
        "files": records,
        "source_commit": commit,
        "source_path_manifest_sha256": _sha256_file(path_manifest),
        "schema_version": 1,
    }
    manifest_path = output_root / "intake-manifest.json"
    manifest_path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    manifest_sha256 = _sha256_file(manifest_path)
    zip_created = False
    try:
        with zipfile.ZipFile(
            zip_path, "x", compression=zipfile.ZIP_DEFLATED
        ) as archive:
            zip_created = True
            archive.write(manifest_path, "intake-manifest.json")
            for record in records:
                archive.write(source_root / record["path"], f"source/{record['path']}")

        expected_names = {"intake-manifest.json"} | {
            f"source/{record['path']}" for record in records
        }
        with zipfile.ZipFile(zip_path) as archive:
            names = set(archive.namelist())
            if names != expected_names:
                raise ValueError("Completed ZIP path set differs from the manifest.")
            for record in records:
                archived = archive.read(f"source/{record['path']}")
                if _sha256_bytes(archived) != record["sha256"]:
                    raise ValueError(
                        f"Completed ZIP verification failed: {record['path']}"
                    )
    except Exception:
        if zip_created and zip_path.exists():
            zip_path.unlink()
        raise

    return {
        "cloud_cli_executed": False,
        "file_count": len(records),
        "intake_manifest_sha256": manifest_sha256,
        "intake_zip": str(zip_path),
        "intake_zip_sha256": _sha256_file(zip_path),
        "release_state_modified": False,
        "repository_modified": False,
        "result": "CANONICAL_GIT_OBJECT_INTAKE_EXPORTED",
        "schema_version": 1,
        "source_commit": commit,
        "working_tree_bytes_used": False,
    }


def inspect_git_configuration(root: Path) -> dict[str, Any]:
    """Report effective Git text settings without changing configuration."""
    root = root.resolve()
    names = ("core.autocrlf", "core.eol", "core.safecrlf", "core.attributesfile")
    settings: dict[str, list[dict[str, str]]] = {name: [] for name in names}
    for name in names:
        observed = _git(
            root,
            ["config", "--show-origin", "--show-scope", "--get-all", name],
            check=False,
        )
        for line in str(observed.stdout).splitlines():
            parts = line.split("\t")
            if len(parts) >= 3:
                settings[name].append(
                    {"scope": parts[0], "origin": parts[1], "value": parts[2]}
                )
    effective: dict[str, str | None] = {}
    for name in names:
        selected = _git(root, ["config", "--get", name], check=False)
        effective[name] = (
            str(selected.stdout).strip() if selected.returncode == 0 else None
        )
    autocrlf = (effective["core.autocrlf"] or "false").lower()
    safecrlf = (effective["core.safecrlf"] or "true").lower()
    compatible = autocrlf in {"false", "input"} and safecrlf != "false"
    return {
        "configuration_modified": False,
        "effective": effective,
        "git_configuration_compatible": compatible,
        "observations": (
            []
            if compatible
            else [
                "Local Git text settings differ from the canonical LF working-tree recommendation; committed attributes and raw Git objects remain authoritative."
            ]
        ),
        "recommended_repository_local": {
            "core.autocrlf": "false",
            "core.eol": "lf",
            "core.safecrlf": "true",
        },
        "result": "GIT_CONFIGURATION_INSPECTED_READ_ONLY",
        "schema_version": 1,
        "settings_with_origins": settings,
    }


def create_corrective_plan(
    root: Path,
    *,
    replacement_root: Path,
    path_manifest: Path,
    output_root: Path,
) -> dict[str, Any]:
    """Plan non-baseline additions/replacements without changing the repository."""
    root = root.resolve()
    replacement_root = replacement_root.resolve()
    path_manifest = path_manifest.resolve()
    output_root = output_root.resolve()
    _assert_external(root, replacement_root, "Replacement root")
    _assert_external(root, path_manifest, "Path manifest")
    _assert_external(root, output_root, "Output root")
    paths = _manifest_paths(path_manifest)
    repairs: list[dict[str, Any]] = []
    for relative_name in paths:
        relative = _safe_relative(relative_name)
        replacement = replacement_root / relative
        if not replacement.is_file():
            raise ValueError(f"Replacement is missing: {relative_name}")
        target = root / relative
        repairs.append(
            {
                "before_exists": target.is_file(),
                "before_sha256": _sha256_file(target) if target.is_file() else None,
                "path": relative_name,
                "replacement_path": str(replacement),
                "replacement_sha256": _sha256_file(replacement),
            }
        )
    plan: dict[str, Any] = {
        "created_at": datetime.now(UTC).isoformat(),
        "git_commit": _git_head(root),
        "path_manifest_sha256": _sha256_file(path_manifest),
        "repairs": repairs,
        "repository": str(root),
        "schema_version": 1,
    }
    plan["plan_digest"] = _sha256_bytes(_canonical_bytes(plan))
    output_root.mkdir(parents=True, exist_ok=True)
    plan_path = output_root / f"corrective-plan-{plan['plan_digest']}.json"
    plan_path.write_text(
        json.dumps(plan, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return {
        "cloud_mutation_performed": False,
        "plan_digest": plan["plan_digest"],
        "plan_path": str(plan_path),
        "release_state_modified": False,
        "repair_count": len(repairs),
        "repository_modified": False,
        "result": "CORRECTIVE_REPAIR_PLAN_PREPARED",
        "schema_version": 1,
    }


def apply_corrective_plan(root: Path, plan_path: Path) -> dict[str, Any]:
    """Apply an approved corrective plan atomically and validate exact bytes."""
    root = root.resolve()
    plan_path = plan_path.resolve()
    _assert_external(root, plan_path, "Corrective plan")
    plan = _load_json(plan_path)
    supplied_digest = str(plan.pop("plan_digest", ""))
    if supplied_digest != _sha256_bytes(_canonical_bytes(plan)):
        raise ValueError("Corrective plan digest validation failed.")
    if Path(str(plan["repository"])).resolve() != root:
        raise ValueError("Corrective plan targets another repository.")
    if plan["git_commit"] != _git_head(root):
        raise ValueError("Repository commit changed after corrective planning.")

    backups: list[tuple[Path, bytes | None]] = []
    try:
        for repair in plan["repairs"]:
            target = root / _safe_relative(str(repair["path"]))
            replacement = Path(str(repair["replacement_path"]))
            before_exists = bool(repair["before_exists"])
            if target.is_file() != before_exists:
                raise ValueError(f"Target existence changed: {repair['path']}")
            if before_exists and _sha256_file(target) != repair["before_sha256"]:
                raise ValueError(f"Target bytes changed: {repair['path']}")
            if _sha256_file(replacement) != repair["replacement_sha256"]:
                raise ValueError(f"Replacement bytes changed: {repair['path']}")
            backups.append((target, target.read_bytes() if target.is_file() else None))
            target.parent.mkdir(parents=True, exist_ok=True)
            temporary = target.with_name(f".{target.name}.corrective-repair")
            shutil.copyfile(replacement, temporary)
            os.replace(temporary, target)
            if _sha256_file(target) != repair["replacement_sha256"]:
                raise ValueError(f"Applied bytes differ: {repair['path']}")
    except Exception:
        for target, data in reversed(backups):
            if data is None:
                target.unlink(missing_ok=True)
            else:
                target.write_bytes(data)
        raise
    from tools.infrastructure_coherence.core import check_repository

    report = check_repository(root)
    if not report["repository_integrity_valid"]:
        for target, data in reversed(backups):
            if data is None:
                target.unlink(missing_ok=True)
            else:
                target.write_bytes(data)
        raise ValueError(
            "Corrective application failed repository integrity validation."
        )
    return {
        "cloud_mutation_performed": False,
        "plan_digest": supplied_digest,
        "release_state_modified": False,
        "repair_count": len(backups),
        "repository_modified": True,
        "result": "CORRECTIVE_REPAIR_PLAN_APPLIED",
        "schema_version": 1,
    }
