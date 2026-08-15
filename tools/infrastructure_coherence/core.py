"""Deterministic repository integrity checks and plan-bound repairs."""

from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import subprocess
import tempfile
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

POLICY_PATH = Path("tools/infrastructure_coherence_policy.json")
TEXT_SUFFIXES = frozenset(
    {
        ".css",
        ".env",
        ".html",
        ".ini",
        ".js",
        ".json",
        ".md",
        ".ps1",
        ".py",
        ".toml",
        ".txt",
        ".yaml",
        ".yml",
    }
)
TEXT_NAMES = frozenset({".editorconfig", ".gitattributes", ".gitignore"})
MOJIBAKE_MARKERS = (
    "\u00c3",
    "\u00c2",
    "\u00e2\u20ac",
    "\u00e2\u201a",
    "\u00e2\u2020",
    "\u00ef\u00bb\u00bf",
    "\ufffd",
)
STORY_ID_PATTERN = re.compile(r"^MLAI-\d{3}(?:\.\d+[A-Z]?)?$")
ADR_FILE_PATTERN = re.compile(r"^ADR-(\d{4})-[a-z0-9-]+\.md$")
ADR_HEADER_PATTERN = re.compile(r"^# (ADR-\d{4}):", re.MULTILINE)
REGISTER_ID_PATTERNS = {
    "governance/registers/risk-register.md": re.compile(r"\| (RISK-\d{3}) \|"),
    "governance/registers/technical-debt-register.md": re.compile(r"\| (TD-\d{3}) \|"),
}


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _content_sha256_bytes(value: bytes) -> str:
    """Hash text content independently of Git's platform EOL materialization."""
    return _sha256_bytes(value.replace(b"\r\n", b"\n"))


def _sha256_file(path: Path) -> str:
    return _sha256_bytes(path.read_bytes())


def _content_sha256_file(path: Path) -> str:
    return _content_sha256_bytes(path.read_bytes())


def _canonical_bytes(value: dict[str, Any]) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")


def _load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(value, dict):
        raise TypeError(f"Expected JSON object: {path}")
    return value


def _declared_paths(root: Path) -> set[Path]:
    policy_path = root / POLICY_PATH
    if not policy_path.is_file():
        return set()
    policy = _load_json(policy_path)
    raw_paths = policy.get("required_repository_paths", [])
    if not isinstance(raw_paths, list) or not all(
        isinstance(item, str) for item in raw_paths
    ):
        raise TypeError("required_repository_paths must be a list of strings.")
    declared: set[Path] = set()
    for item in raw_paths:
        relative = Path(item)
        if relative.is_absolute() or ".." in relative.parts:
            raise ValueError(f"Required repository path is unsafe: {item}")
        declared.add(relative)
    return declared


def _relative_files(root: Path, declared: set[Path]) -> list[Path]:
    try:
        completed = subprocess.run(
            ["git", "ls-files", "--cached", "-z"],
            cwd=root,
            check=True,
            capture_output=True,
            text=True,
        )
    except FileNotFoundError as error:
        raise ValueError("Git is required for repository integrity checks.") from error
    except subprocess.CalledProcessError as error:
        raise ValueError(
            "Repository integrity checks require Git repository metadata."
        ) from error
    tracked = {
        Path(line)
        for line in completed.stdout.split("\0")
        if line and (root / line).is_file()
    }
    return sorted(tracked | {path for path in declared if (root / path).is_file()})


def _finding(code: str, relative: Path, digest: str, message: str) -> dict[str, str]:
    return {
        "code": code,
        "message": message,
        "path": relative.as_posix(),
        "sha256": digest,
    }


def _scan_text(root: Path, relative: Path) -> list[dict[str, str]]:
    path = root / relative
    if relative.suffix.lower() not in TEXT_SUFFIXES and relative.name not in TEXT_NAMES:
        return []
    data = path.read_bytes()
    digest = _content_sha256_bytes(data)
    findings: list[dict[str, str]] = []
    if data.startswith(b"\xef\xbb\xbf"):
        findings.append(
            _finding("UTF8_BOM", relative, digest, "UTF-8 BOM is forbidden.")
        )
    try:
        text = data.decode("utf-8-sig")
    except UnicodeDecodeError:
        return [
            _finding("UTF8_DECODE_ERROR", relative, digest, "File is not valid UTF-8.")
        ]
    if any(marker in text for marker in MOJIBAKE_MARKERS):
        findings.append(
            _finding(
                "MOJIBAKE",
                relative,
                digest,
                "Probable double-decoding corruption detected.",
            )
        )
    canonical_data = data.replace(b"\r\n", b"\n")
    if canonical_data and not canonical_data.endswith(b"\n"):
        findings.append(
            _finding(
                "MISSING_FINAL_NEWLINE", relative, digest, "Final newline required."
            )
        )
    if canonical_data.endswith(b"\n\n"):
        findings.append(
            _finding(
                "EXTRA_EOF_BLANK_LINE",
                relative,
                digest,
                "Only one final newline is allowed.",
            )
        )
    return findings


def _scan_story_packages(root: Path, relative_files: set[Path]) -> list[dict[str, str]]:
    findings: list[dict[str, str]] = []
    identities: dict[str, Path] = {}
    story_paths = sorted(
        relative
        for relative in relative_files
        if relative.parent == Path("story_packages") and relative.suffix == ".json"
    )
    for relative in story_paths:
        path = root / relative
        digest = _content_sha256_file(path)
        try:
            value = _load_json(path)
        except (json.JSONDecodeError, UnicodeDecodeError, TypeError) as error:
            findings.append(
                _finding("INVALID_STORY_JSON", relative, digest, str(error))
            )
            continue
        story_id = value.get("story_id")
        if value.get("schema_version") != 2 or not isinstance(story_id, str):
            findings.append(
                _finding(
                    "LEGACY_STORY_SCHEMA",
                    relative,
                    digest,
                    "Legacy story manifest must be migrated before modification.",
                )
            )
            continue
        required = {"adr", "out_of_scope", "scope", "status", "story_id", "title"}
        if not required.issubset(value) or not STORY_ID_PATTERN.fullmatch(story_id):
            findings.append(
                _finding(
                    "INVALID_STORY_MANIFEST",
                    relative,
                    digest,
                    "Schema v2 fields are invalid.",
                )
            )
            continue
        if path.stem != story_id:
            findings.append(
                _finding(
                    "STORY_FILENAME_MISMATCH",
                    relative,
                    digest,
                    "story_id must match filename.",
                )
            )
        if story_id in identities:
            findings.append(
                _finding(
                    "DUPLICATE_STORY_ID",
                    relative,
                    digest,
                    f"Duplicate story_id: {story_id}",
                )
            )
        identities[story_id] = relative
    return findings


def _scan_governance(root: Path, relative_files: set[Path]) -> list[dict[str, str]]:
    findings: list[dict[str, str]] = []
    adr_ids: dict[str, Path] = {}
    adr_paths = sorted(
        relative
        for relative in relative_files
        if relative.parent == Path("governance/adrs")
        and relative.name.startswith("ADR-")
        and relative.suffix == ".md"
    )
    for relative in adr_paths:
        path = root / relative
        digest = _content_sha256_file(path)
        file_match = ADR_FILE_PATTERN.fullmatch(path.name)
        text = path.read_text(encoding="utf-8-sig")
        header_match = ADR_HEADER_PATTERN.search(text)
        if not file_match or not header_match or header_match.group(1) != path.name[:8]:
            findings.append(
                _finding(
                    "ADR_ID_MISMATCH",
                    relative,
                    digest,
                    "ADR filename and H1 identifier differ.",
                )
            )
            continue
        adr_id = header_match.group(1)
        if adr_id in adr_ids:
            findings.append(
                _finding("DUPLICATE_ADR_ID", relative, digest, f"Duplicate {adr_id}.")
            )
        adr_ids[adr_id] = relative
    for relative_name, pattern in REGISTER_ID_PATTERNS.items():
        relative = Path(relative_name)
        if relative not in relative_files:
            continue
        path = root / relative_name
        if not path.exists():
            continue
        digest = _content_sha256_file(path)
        text = path.read_text(encoding="utf-8-sig")
        seen: set[str] = set()
        for identifier in pattern.findall(text):
            if identifier in seen:
                findings.append(
                    _finding(
                        "DUPLICATE_REGISTER_ID",
                        relative,
                        digest,
                        f"Duplicate {identifier}.",
                    )
                )
            seen.add(identifier)
    return findings


def _scan_contract(root: Path) -> list[dict[str, str]]:
    findings: list[dict[str, str]] = []
    workflow = root / ".github" / "workflows" / "quality.yml"
    if workflow.exists():
        relative = workflow.relative_to(root)
        digest = _content_sha256_file(workflow)
        text = workflow.read_text(encoding="utf-8-sig")
        required = (
            "python -m tools.infrastructure_coherence check --ci",
            "python -m unittest tests.test_infrastructure_coherence",
            "python -m ruff check app deployment tools tests",
            "python -m black --check app deployment tools tests",
            "git diff --check",
        )
        if not all(item in text for item in required):
            findings.append(
                _finding(
                    "CI_COHERENCE_GAP",
                    relative,
                    digest,
                    "CI omits canonical integrity checks.",
                )
            )
    script = root / "scripts" / "repair_local_hygiene.ps1"
    if script.exists():
        relative = script.relative_to(root)
        digest = _content_sha256_file(script)
        text = script.read_text(encoding="utf-8-sig")
        forbidden = ("Get-Content", "WriteAllText", "ruff check . --fix", "black .")
        if any(item in text for item in forbidden):
            findings.append(
                _finding(
                    "UNSAFE_HYGIENE_SCRIPT",
                    relative,
                    digest,
                    "Script can rewrite repository bytes.",
                )
            )
    attributes = root / ".gitattributes"
    if attributes.exists():
        relative = attributes.relative_to(root)
        digest = _content_sha256_file(attributes)
        text = attributes.read_text(encoding="utf-8-sig")
        required = (
            "* text=auto eol=lf",
            "*.ps1 text eol=lf",
            "*.bat text eol=crlf",
            "*.cmd text eol=crlf",
        )
        if not all(item in text for item in required):
            findings.append(
                _finding(
                    "GIT_ATTRIBUTES_CONTRACT_GAP",
                    relative,
                    digest,
                    "Git text normalization contract is incomplete.",
                )
            )
    editor_config = root / ".editorconfig"
    if editor_config.exists():
        relative = editor_config.relative_to(root)
        digest = _content_sha256_file(editor_config)
        text = editor_config.read_text(encoding="utf-8-sig")
        required = (
            "charset = utf-8",
            "end_of_line = lf",
            "[*.ps1]",
            "[*.{bat,cmd}]",
            "end_of_line = crlf",
        )
        if not all(item in text for item in required):
            findings.append(
                _finding(
                    "EDITORCONFIG_CONTRACT_GAP",
                    relative,
                    digest,
                    "Editor encoding and line-ending contract is incomplete.",
                )
            )
    return findings


def scan_repository(root: Path) -> list[dict[str, str]]:
    findings: list[dict[str, str]] = []
    declared = _declared_paths(root)
    relative_files = set(_relative_files(root, declared))
    for relative in sorted(relative_files):
        findings.extend(_scan_text(root, relative))
    for relative in sorted(declared - relative_files):
        findings.append(
            _finding(
                "REQUIRED_PATH_MISSING",
                relative,
                _sha256_bytes(b""),
                "Declared repository contract path is missing.",
            )
        )
    findings.extend(_scan_story_packages(root, relative_files))
    findings.extend(_scan_governance(root, relative_files))
    findings.extend(_scan_contract(root))
    unique = {(item["path"], item["code"], item["sha256"]): item for item in findings}
    return sorted(unique.values(), key=lambda item: (item["path"], item["code"]))


def _baseline(root: Path) -> tuple[dict[str, Any], str]:
    policy = _load_json(root / POLICY_PATH)
    baseline_path = root / str(policy["legacy_baseline"])
    baseline = _load_json(baseline_path)
    return baseline, _sha256_file(baseline_path)


def check_repository(root: Path) -> dict[str, Any]:
    root = root.resolve()
    baseline, baseline_sha256 = _baseline(root)
    findings = scan_repository(root)
    allowed = {
        (item["path"], item["code"], item["sha256"])
        for item in baseline.get("findings", [])
    }
    acknowledged = [
        item
        for item in findings
        if (item["path"], item["code"], item["sha256"]) in allowed
    ]
    blocking = [item for item in findings if item not in acknowledged]
    active = {(item["path"], item["code"], item["sha256"]) for item in findings}
    resolved = [
        item
        for item in baseline.get("findings", [])
        if (item["path"], item["code"], item["sha256"]) not in active
    ]
    valid = not blocking
    return {
        "acknowledged_legacy_finding_count": len(acknowledged),
        "baseline_sha256": baseline_sha256,
        "blocking_findings": blocking,
        "cloud_cli_executed": False,
        "cloud_mutation_performed": False,
        "release_state_modified": False,
        "repository_integrity_valid": valid,
        "resolved_legacy_finding_count": len(resolved),
        "result": (
            "REPOSITORY_INTEGRITY_PASSED_WITH_ACKNOWLEDGED_DEBT"
            if valid and acknowledged
            else (
                "REPOSITORY_INTEGRITY_PASSED"
                if valid
                else "REPOSITORY_INTEGRITY_FAILED"
            )
        ),
        "schema_version": 1,
    }


def _assert_external(root: Path, candidate: Path, label: str) -> None:
    try:
        candidate.resolve().relative_to(root.resolve())
    except ValueError:
        return
    raise ValueError(f"{label} must be outside the repository.")


def _git_head(root: Path) -> str:
    completed = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=root,
        check=False,
        capture_output=True,
        text=True,
    )
    return completed.stdout.strip() if completed.returncode == 0 else "unavailable"


def create_repair_plan(
    root: Path, *, replacement_root: Path, output_root: Path
) -> dict[str, Any]:
    root = root.resolve()
    _assert_external(root, replacement_root, "Replacement root")
    _assert_external(root, output_root, "Output root")
    baseline, baseline_sha256 = _baseline(root)
    repairs: list[dict[str, Any]] = []
    by_path: dict[str, list[dict[str, Any]]] = {}
    for finding in baseline.get("findings", []):
        by_path.setdefault(finding["path"], []).append(finding)
    for relative_name, entries in sorted(by_path.items()):
        replacement = replacement_root / relative_name
        if not replacement.exists():
            continue
        target = root / relative_name
        expected = {entry["sha256"] for entry in entries}
        if not target.exists() or _content_sha256_file(target) not in expected:
            raise ValueError(
                "Current content does not match the acknowledged baseline: "
                f"{relative_name}"
            )
        with tempfile.TemporaryDirectory() as temporary:
            temp_root = Path(temporary)
            temp_target = temp_root / relative_name
            temp_target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(replacement, temp_target)
            replacement_findings = _scan_text(temp_root, Path(relative_name))
        if replacement_findings:
            raise ValueError(f"Replacement remains non-canonical: {relative_name}")
        repairs.append(
            {
                "before_sha256": _sha256_file(target),
                "finding_codes": sorted({entry["code"] for entry in entries}),
                "path": relative_name,
                "replacement_path": str(replacement.resolve()),
                "replacement_sha256": _sha256_file(replacement),
            }
        )
    if not repairs:
        raise ValueError("No baseline-bound replacement files were found.")
    plan: dict[str, Any] = {
        "baseline_sha256": baseline_sha256,
        "created_at": datetime.now(UTC).isoformat(),
        "git_commit": _git_head(root),
        "repairs": repairs,
        "repository": str(root),
        "schema_version": 1,
    }
    plan["plan_digest"] = _sha256_bytes(_canonical_bytes(plan))
    output_root.mkdir(parents=True, exist_ok=True)
    plan_path = output_root / f"repository-repair-{plan['plan_digest']}.json"
    plan_path.write_text(
        json.dumps(plan, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return {
        "cloud_mutation_performed": False,
        "plan_digest": plan["plan_digest"],
        "plan_path": str(plan_path),
        "release_state_modified": False,
        "repair_count": len(repairs),
        "result": "REPOSITORY_REPAIR_PLAN_PREPARED",
        "schema_version": 1,
    }


def apply_repair_plan(root: Path, plan_path: Path) -> dict[str, Any]:
    root = root.resolve()
    _assert_external(root, plan_path, "Repair plan")
    plan = _load_json(plan_path)
    supplied_digest = str(plan.pop("plan_digest", ""))
    if supplied_digest != _sha256_bytes(_canonical_bytes(plan)):
        raise ValueError("Repair plan digest validation failed.")
    if Path(str(plan["repository"])).resolve() != root:
        raise ValueError("Repair plan targets another repository.")
    _, baseline_sha256 = _baseline(root)
    if plan["baseline_sha256"] != baseline_sha256 or plan["git_commit"] != _git_head(
        root
    ):
        raise ValueError("Repository or baseline changed after plan preparation.")
    backups: list[tuple[Path, bytes]] = []
    try:
        for repair in plan["repairs"]:
            target = root / repair["path"]
            replacement = Path(repair["replacement_path"])
            if _sha256_file(target) != repair["before_sha256"]:
                raise ValueError(f"Target changed after planning: {repair['path']}")
            if _sha256_file(replacement) != repair["replacement_sha256"]:
                raise ValueError(
                    f"Replacement changed after planning: {repair['path']}"
                )
            backups.append((target, target.read_bytes()))
            temporary = target.with_name(f".{target.name}.integrity-repair")
            shutil.copyfile(replacement, temporary)
            os.replace(temporary, target)
        report = check_repository(root)
        if not report["repository_integrity_valid"]:
            raise ValueError("Post-repair repository validation failed.")
    except Exception:
        for target, data in backups:
            target.write_bytes(data)
        raise
    return {
        "cloud_mutation_performed": False,
        "plan_digest": supplied_digest,
        "release_state_modified": False,
        "repair_count": len(backups),
        "result": "REPOSITORY_REPAIR_PLAN_APPLIED",
        "schema_version": 1,
    }
