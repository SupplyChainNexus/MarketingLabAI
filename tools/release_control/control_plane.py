"""One-plan, one-approval, one-status release orchestration."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Mapping

from deployment.private_synthetic_manifest import validate_template
from deployment.release_controller import (
    gate_status,
    read_events,
    record_gate,
    release_summary,
    verify_run,
)
from tools.release_control.cloud_preflight import (
    CloudJsonReader,
    GcloudJsonReader,
    run_cloud_preflight,
)
from tools.release_control.config import ControlConfig, validate_repository
from tools.release_control.store import (
    RunLock,
    canonical_json,
    read_json_verified,
    sha256_bytes,
    sha256_file,
    write_json_atomic,
)

INDEX_FILE = "release-index.json"
ZERO_HASH = "0" * 64
INITIAL_PASSED_GATES = ("SOURCE_VERIFIED", "CI_PASSED", "ARTIFACT_VERIFIED")


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _outside_repository(path: Path, repository_root: Path) -> bool:
    try:
        path.resolve().relative_to(repository_root.resolve())
    except ValueError:
        return True
    return False


def _required_string(value: object, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{label} is missing or invalid.")
    return value.strip()


def _first_string(payload: Mapping[str, object], *names: str) -> str:
    for name in names:
        value = payload.get(name)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return ""


class ReleaseControlPlane:
    """Coordinate one release without becoming its admission authority."""

    def __init__(
        self,
        config: ControlConfig,
        state_root: Path,
        *,
        cloud_reader: CloudJsonReader | None = None,
    ):
        self.config = config
        self.state_root = state_root.expanduser().resolve()
        self.cloud_reader = cloud_reader
        if not _outside_repository(self.state_root, config.repository_root):
            raise ValueError(
                "Release-control state must remain outside the repository."
            )

    @property
    def index_path(self) -> Path:
        return self.state_root / INDEX_FILE

    def _relative_record(self, path: Path) -> str:
        return path.resolve().relative_to(self.state_root).as_posix()

    def _record_path(self, relative: str) -> Path:
        path = (self.state_root / relative).resolve()
        try:
            path.relative_to(self.state_root)
        except ValueError as error:
            raise ValueError(
                "Release-control record escapes the state root."
            ) from error
        return path

    def _load_index(self) -> dict[str, object]:
        index = read_json_verified(self.index_path)
        if index.get("schema_version") != 1:
            raise ValueError("Unsupported release index schema.")
        release = index.get("release")
        if not isinstance(release, dict):
            raise ValueError("Release index identity is missing.")
        run_dir = Path(_required_string(index.get("observational_run"), "Run path"))
        metadata = verify_run(run_dir)
        expected = {
            "run_id": metadata["run_id"],
            "commit": metadata["commit"],
            "image_digest": metadata["image_digest"],
            "environment": metadata["environment"],
        }
        for name, value in expected.items():
            if release.get(name) != value:
                raise ValueError(f"Release index has a mismatched {name}.")
        return index

    def adopt(
        self,
        *,
        run_dir: Path,
        build_summary_path: Path,
        post_build_assessment_path: Path,
        operator: str,
    ) -> dict[str, object]:
        """Adopt verified historical observations without granting authority."""

        operator = _required_string(operator, "Operator")
        metadata = verify_run(run_dir)
        summary = release_summary(run_dir)
        status = summary["gate_status"]
        if not isinstance(status, dict):
            raise ValueError("Observational gate status is invalid.")
        for gate in INITIAL_PASSED_GATES:
            if status.get(gate) != "passed":
                raise ValueError(f"Required observed gate has not passed: {gate}")
        if summary["eligible_gates"] != ["CONFIGURATION_VALIDATED"]:
            raise ValueError(
                "Adoption requires CONFIGURATION_VALIDATED as the only eligible gate."
            )

        build = json.loads(build_summary_path.read_text(encoding="utf-8-sig"))
        assessment = json.loads(
            post_build_assessment_path.read_text(encoding="utf-8-sig")
        )
        if not isinstance(build, dict) or not isinstance(assessment, dict):
            raise ValueError("Build evidence must contain JSON objects.")
        build_result = _first_string(build, "result", "status")
        if build_result not in {"CONTROLLED_CLOUD_BUILD_PASSED", "SUCCESS"}:
            raise ValueError("Build summary does not report a controlled success.")
        build_image = _first_string(
            build, "qualified_digest", "image_digest", "image", "qualified_image"
        )
        if build_image != metadata["image_digest"]:
            raise ValueError("Build summary image does not match the release run.")
        build_id = _first_string(build, "build_id", "buildId", "id")
        if not build_id:
            raise ValueError("Build summary does not contain a build ID.")
        assessment_result = _first_string(assessment, "result", "status")
        if assessment_result != "POST_BUILD_EVIDENCE_ASSESSMENT_PASSED_READ_ONLY":
            raise ValueError("Post-build evidence assessment has not passed.")

        evidence = []
        for kind, path in (
            ("controlled_build_summary", build_summary_path),
            ("post_build_assessment", post_build_assessment_path),
        ):
            resolved = path.resolve()
            evidence.append(
                {
                    "kind": kind,
                    "path": str(resolved),
                    "length": resolved.stat().st_size,
                    "sha256": sha256_file(resolved),
                }
            )

        index: dict[str, object] = {
            "schema_version": 1,
            "control_plane_version": self.config.payload["control_plane_version"],
            "created_at": _utc_now(),
            "created_by": operator,
            "release": {
                "run_id": metadata["run_id"],
                "commit": metadata["commit"],
                "image_digest": metadata["image_digest"],
                "environment": metadata["environment"],
                "build_id": build_id,
            },
            "observational_run": str(run_dir.resolve()),
            "evidence": evidence,
            "authorities": dict(self.config.payload["authorities"]),
            "controller_authoritative": False,
            "local_approval_is_admission_authority": False,
            "deployment_authorized": False,
            "public_access_authorized": False,
            "real_customer_data_authorized": False,
        }
        self.state_root.mkdir(parents=True, exist_ok=True)
        with RunLock(self.state_root / "control-plane.lock"):
            if self.index_path.exists():
                existing = self._load_index()
                if existing["release"] != index["release"]:
                    raise ValueError("State root is already bound to another release.")
                return existing
            write_json_atomic(self.index_path, index)
        return index

    def _verify_evidence_index(self, index: Mapping[str, object]) -> None:
        records = index.get("evidence")
        if not isinstance(records, list) or not records:
            raise ValueError("Unified evidence index is empty.")
        for record in records:
            if not isinstance(record, dict):
                raise ValueError("Unified evidence record is invalid.")
            path = Path(_required_string(record.get("path"), "Evidence path"))
            if not path.is_file():
                raise ValueError(f"Indexed evidence is missing: {path}")
            if path.stat().st_size != record.get("length"):
                raise ValueError(f"Indexed evidence length changed: {path}")
            if sha256_file(path) != record.get("sha256"):
                raise ValueError(f"Indexed evidence digest changed: {path}")

        if index.get("control_plane_version") == self.config.payload.get(
            "control_plane_version"
        ):
            indexed_paths = {str(record.get("path")) for record in records}
            run_dir = Path(str(index["observational_run"]))
            for event in read_events(run_dir):
                reference = str(event.get("evidence_reference", ""))
                if not reference.startswith("release-control://"):
                    continue
                relative, marker, _ = reference.removeprefix(
                    "release-control://"
                ).partition("#sha256=")
                if not marker:
                    raise ValueError("Local gate evidence reference is malformed.")
                if str(self._record_path(relative)) not in indexed_paths:
                    raise ValueError("Local gate evidence is absent from the index.")

    def _index_gate_evidence(
        self,
        index: dict[str, object],
        *,
        kind: str,
        path: Path,
        expected_sha256: str,
    ) -> None:
        resolved = path.resolve()
        if not resolved.is_file() or sha256_file(resolved) != expected_sha256:
            raise ValueError(f"Gate evidence failed integrity verification: {resolved}")
        records = index.get("evidence")
        if not isinstance(records, list):
            raise ValueError("Unified evidence index is invalid.")
        matching = [record for record in records if record.get("path") == str(resolved)]
        expected = {
            "kind": kind,
            "path": str(resolved),
            "length": resolved.stat().st_size,
            "sha256": expected_sha256,
        }
        if matching:
            if len(matching) != 1 or matching[0] != expected:
                raise ValueError("Indexed gate evidence conflicts with the record.")
            return
        records.append(expected)

    def _migrate_local_gate_evidence(
        self, index: dict[str, object], run_dir: Path
    ) -> None:
        for event in read_events(run_dir):
            reference = str(event.get("evidence_reference", ""))
            if not reference.startswith("release-control://"):
                continue
            relative, marker, expected = reference.removeprefix(
                "release-control://"
            ).partition("#sha256=")
            if not marker or len(expected) != 64:
                raise ValueError("Local gate evidence reference is malformed.")
            self._index_gate_evidence(
                index,
                kind=f"gate_evidence:{event['gate_id']}",
                path=self._record_path(relative),
                expected_sha256=expected,
            )

    def verify(self) -> dict[str, object]:
        index = self._load_index()
        self._verify_evidence_index(index)
        run_dir = Path(str(index["observational_run"]))
        metadata = verify_run(run_dir)
        return {
            "schema_version": 1,
            "result": "RELEASE_CONTROL_STATE_VERIFIED",
            "run_id": metadata["run_id"],
            "release_index_sha256": sha256_file(self.index_path),
            "observational_chain_valid": True,
            "indexed_evidence_valid": True,
            "controller_authoritative": False,
            "deployment_authorized": False,
            "cloud_mutation_performed": False,
        }

    def status(self, *, audit: bool = False) -> dict[str, object]:
        index = self._load_index()
        self._verify_evidence_index(index)
        summary = release_summary(Path(str(index["observational_run"])))
        eligible = summary["eligible_gates"]
        failed = summary["failed_gates"]
        if failed:
            state = "blocked"
            next_action = "Review the recorded failure and its safe next action."
        elif eligible:
            state = "ready_for_plan"
            next_action = f"Create or inspect the plan for {eligible[0]}."
        else:
            state = "complete" if summary["release_closed"] else "waiting"
            next_action = "No release transition is currently eligible."
        result: dict[str, object] = {
            "schema_version": 1,
            "state": state,
            "run_id": summary["run_id"],
            "next_eligible_gate": eligible[0] if len(eligible) == 1 else None,
            "next_action": next_action,
            "one_plan": True,
            "one_approval": True,
            "controller_authoritative": False,
            "admission_authority": self.config.payload["authorities"]["admission"],
            "deployment_authorized": False,
            "cloud_mutation_performed": False,
        }
        if audit:
            result["audit"] = {
                "release": index["release"],
                "gate_status": summary["gate_status"],
                "failed_gates": failed,
                "evidence_records": index["evidence"],
                "release_index_sha256": sha256_file(self.index_path),
            }
        return result

    def _event_head(self, run_dir: Path) -> str:
        events = read_events(run_dir)
        return str(events[-1]["event_hash"]) if events else ZERO_HASH

    def _build_plan(self) -> dict[str, object]:
        index = self._load_index()
        self._verify_evidence_index(index)
        run_dir = Path(str(index["observational_run"]))
        summary = release_summary(run_dir)
        eligible = summary["eligible_gates"]
        if len(eligible) != 1:
            raise ValueError("Exactly one eligible transition is required for a plan.")
        gate = str(eligible[0])
        if gate not in self.config.supported_apply_gates:
            raise ValueError(
                f"The paved path does not yet implement {gate}; no command was run."
            )
        action = {
            "CONFIGURATION_VALIDATED": "validate_configuration",
            "CLOUD_PREFLIGHT_PASSED": "inspect_cloud_preflight",
        }[gate]
        return {
            "schema_version": 1,
            "kind": "release-transition-plan",
            "release": index["release"],
            "release_index_sha256": sha256_file(self.index_path),
            "observational_event_head": self._event_head(run_dir),
            "gate": gate,
            "action": action,
            "may_mutate_cloud": False,
            "approval_required": True,
            "controller_authoritative": False,
            "admission_authority": self.config.payload["authorities"]["admission"],
        }

    @staticmethod
    def _plan_digest(plan: Mapping[str, object]) -> str:
        unsigned = {key: value for key, value in plan.items() if key != "plan_digest"}
        return sha256_bytes(canonical_json(unsigned))

    def plan(self) -> dict[str, object]:
        plan = self._build_plan()
        digest = self._plan_digest(plan)
        plan["plan_digest"] = digest
        path = self.state_root / "plans" / f"{digest}.json"
        if path.exists():
            existing = read_json_verified(path)
            if existing != plan:
                raise ValueError(
                    "Stored plan conflicts with the current deterministic plan."
                )
            return existing
        write_json_atomic(path, plan)
        return plan

    def _load_plan(
        self, digest: str, *, require_current: bool = True
    ) -> dict[str, object]:
        if len(digest) != 64 or any(
            character not in "0123456789abcdef" for character in digest
        ):
            raise ValueError("Plan digest must be a lowercase SHA-256 value.")
        path = self.state_root / "plans" / f"{digest}.json"
        plan = read_json_verified(path)
        if plan.get("plan_digest") != digest or self._plan_digest(plan) != digest:
            raise ValueError("Plan digest verification failed.")
        if require_current and plan != self.plan():
            raise ValueError("Plan is stale because the release state has changed.")
        return plan

    def approve(
        self, *, plan_digest: str, operator: str, authorization_reference: str
    ) -> dict[str, object]:
        plan = self._load_plan(plan_digest)
        operator = _required_string(operator, "Approver")
        reference = _required_string(authorization_reference, "Authorization reference")
        path = self.state_root / "approvals" / f"{plan_digest}.json"
        if path.exists():
            existing = read_json_verified(path)
            if existing.get("plan_digest") != plan_digest:
                raise ValueError("Stored approval is bound to another plan.")
            return existing
        approval: dict[str, object] = {
            "schema_version": 1,
            "kind": "local-orchestration-approval",
            "approved_at": _utc_now(),
            "approved_by": operator,
            "authorization_reference": reference,
            "plan_digest": plan_digest,
            "release": plan["release"],
            "gate": plan["gate"],
            "may_mutate_cloud": plan["may_mutate_cloud"],
            "admission_authority": False,
            "deployment_authorized": False,
        }
        approval["approval_digest"] = sha256_bytes(canonical_json(approval))
        write_json_atomic(path, approval)
        return approval

    def _load_approval(self, plan: Mapping[str, object]) -> dict[str, object]:
        digest = str(plan["plan_digest"])
        approval = read_json_verified(self.state_root / "approvals" / f"{digest}.json")
        recorded = approval.get("approval_digest")
        unsigned = {
            key: value for key, value in approval.items() if key != "approval_digest"
        }
        if recorded != sha256_bytes(canonical_json(unsigned)):
            raise ValueError("Approval digest verification failed.")
        if approval.get("plan_digest") != digest or approval.get("release") != plan.get(
            "release"
        ):
            raise ValueError("Approval is not bound to this plan and release.")
        if approval.get("admission_authority") is not False:
            raise ValueError("Local approval may not claim admission authority.")
        return approval

    def _configuration_evidence(self, plan: Mapping[str, object]) -> dict[str, object]:
        repository = validate_repository(self.config)
        authorities = (
            "AGENTS.md",
            "governance/product-constitution.md",
            "governance/locked-decision-register.md",
            "governance/definition-of-done.md",
            "governance/adrs/ADR-0033-durable-remediation-directive.md",
            "governance/adrs/ADR-0034-progressive-release-automation.md",
            "governance/adrs/ADR-0035-zero-trust-software-supply-chain.md",
            "governance/adrs/ADR-0039-unified-release-control-plane.md",
        )
        authority_hashes: dict[str, str] = {}
        for relative in authorities:
            path = self.config.repository_root / relative
            text = path.read_text(encoding="utf-8-sig")
            if (
                relative != "AGENTS.md"
                and "release" not in text.lower()
                and "remediation" not in text.lower()
            ):
                raise ValueError(f"Release-control authority is incomplete: {relative}")
            authority_hashes[relative] = sha256_file(path)
        workflow_path = (
            self.config.repository_root / ".github" / "workflows" / "quality.yml"
        )
        workflow = workflow_path.read_text(encoding="utf-8-sig")
        if "python -m tools.release_control validate-repository" not in workflow:
            raise ValueError(
                "CI does not execute the unified release-control validation."
            )
        template_path = (
            self.config.repository_root
            / "deployment"
            / "cloud-run.private-synthetic.yaml.template"
        )
        template = validate_template(template_path.read_text(encoding="utf-8-sig"))
        return {
            "schema_version": 1,
            "result": "CONFIGURATION_VALIDATED",
            "completed_at": _utc_now(),
            "plan_digest": plan["plan_digest"],
            "release": plan["release"],
            "repository_validation": repository,
            "template_validation": template,
            "authority_sha256": authority_hashes,
            "workflow_sha256": sha256_file(workflow_path),
            "secret_values_read": False,
            "cloud_mutation_performed": False,
            "deployment_authorized": False,
        }

    def _cloud_preflight_evidence(
        self, plan: Mapping[str, object]
    ) -> dict[str, object]:
        selected = self.config.payload.get("cloud_preflight")
        if not isinstance(selected, dict):
            raise ValueError("Cloud preflight configuration is missing.")
        release = plan.get("release")
        if not isinstance(release, dict):
            raise ValueError("Cloud preflight plan release identity is missing.")
        reader = self.cloud_reader or GcloudJsonReader.from_environment()
        evidence = run_cloud_preflight(
            selected,
            image_digest=_required_string(
                release.get("image_digest"), "Release image digest"
            ),
            reader=reader,
        )
        return {
            **evidence,
            "completed_at": _utc_now(),
            "plan_digest": plan["plan_digest"],
            "release": release,
        }

    def apply(self, *, plan_digest: str) -> dict[str, object]:
        with RunLock(self.state_root / "control-plane.lock"):
            plan = self._load_plan(plan_digest, require_current=False)
            approval = self._load_approval(plan)
            if plan["may_mutate_cloud"] is not False:
                raise ValueError(
                    "This control-plane version cannot execute cloud mutation."
                )
            operation_path = self.state_root / "operations" / f"{plan_digest}.json"
            if operation_path.exists():
                operation = read_json_verified(operation_path)
                if operation.get("status") == "completed":
                    return operation
            else:
                current = self._build_plan()
                if self._plan_digest(current) != plan_digest:
                    raise ValueError(
                        "Plan is stale because the release state has changed."
                    )
                operation = {
                    "schema_version": 1,
                    "plan_digest": plan_digest,
                    "approval_digest": approval["approval_digest"],
                    "gate": plan["gate"],
                    "status": "running",
                    "started_at": _utc_now(),
                    "cloud_mutation_performed": False,
                }
                write_json_atomic(operation_path, operation)

            gate = str(plan["gate"])
            evidence_folders = {
                "CONFIGURATION_VALIDATED": "configuration",
                "CLOUD_PREFLIGHT_PASSED": "cloud-preflight",
            }
            if gate not in evidence_folders:
                raise ValueError("The selected gate has no paved executor.")
            evidence_path = (
                self.state_root
                / "evidence"
                / evidence_folders[gate]
                / f"{plan_digest}.json"
            )
            index = self._load_index()
            run_dir = Path(str(index["observational_run"]))
            status = gate_status(run_dir)
            if evidence_path.exists():
                read_json_verified(evidence_path)
                evidence_hash = sha256_file(evidence_path)
            else:
                if status[gate] != "pending":
                    raise ValueError(f"{gate} changed before evidence was committed.")
                current = self._build_plan()
                if self._plan_digest(current) != plan_digest:
                    raise ValueError(
                        "Plan is stale because the release state has changed."
                    )
                evidence = (
                    self._configuration_evidence(plan)
                    if gate == "CONFIGURATION_VALIDATED"
                    else self._cloud_preflight_evidence(plan)
                )
                evidence_hash = write_json_atomic(evidence_path, evidence)
            reference = (
                f"release-control://{self._relative_record(evidence_path)}"
                f"#sha256={evidence_hash}"
            )
            self._migrate_local_gate_evidence(index, run_dir)
            self._index_gate_evidence(
                index,
                kind=f"gate_evidence:{gate}",
                path=evidence_path,
                expected_sha256=evidence_hash,
            )
            index["control_plane_version"] = self.config.payload[
                "control_plane_version"
            ]
            write_json_atomic(self.index_path, index)
            if status[gate] == "pending":
                record_gate(
                    run_dir,
                    gate_id=gate,
                    outcome="passed",
                    evidence_reference=reference,
                    operator=str(approval["approved_by"]),
                    authorization_reference=str(approval["authorization_reference"]),
                )
            elif status[gate] == "passed":
                matching = [
                    event
                    for event in read_events(run_dir)
                    if event.get("gate_id") == gate
                ]
                if (
                    len(matching) != 1
                    or matching[0].get("evidence_reference") != reference
                ):
                    raise ValueError(f"{gate} already passed with different evidence.")
            else:
                raise ValueError(f"{gate} is terminal but did not pass.")

            completed = {
                **operation,
                "status": "completed",
                "completed_at": _utc_now(),
                "evidence_reference": reference,
                "evidence_sha256": evidence_hash,
                "next_eligible_gate": release_summary(run_dir)["eligible_gates"][0],
                "controller_authoritative": False,
                "deployment_authorized": False,
                "cloud_mutation_performed": False,
            }
            write_json_atomic(operation_path, completed)
            return completed

    def resume(self) -> dict[str, object]:
        operations = [
            read_json_verified(path)
            for path in (self.state_root / "operations").glob("*.json")
        ]
        latest = (
            max(
                operations,
                key=lambda item: str(
                    item.get("completed_at") or item.get("started_at") or ""
                ),
            )
            if operations
            else None
        )
        if latest is not None and latest.get("status") != "completed":
            return self.apply(plan_digest=str(latest["plan_digest"]))
        try:
            plan = self.plan()
        except ValueError as error:
            if latest is not None and "does not yet implement" in str(error):
                return latest
            raise
        approval_path = self.state_root / "approvals" / f"{plan['plan_digest']}.json"
        if not approval_path.exists():
            return {
                **self.status(),
                "state": "awaiting_approval",
                "plan_digest": plan["plan_digest"],
                "next_action": "Approve the displayed plan through the one approval interface.",
            }
        return self.apply(plan_digest=str(plan["plan_digest"]))
