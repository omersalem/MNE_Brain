"""Central deterministic broker for workspace, MNE read, and P10 tools."""

from __future__ import annotations

import hashlib
import json
import re
import secrets
import subprocess
import tempfile
import threading
from copy import deepcopy
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import jsonschema
import yaml

from core.evidence.build_evidence_pack import EvidencePackBuilder
from core.entity.build_entity_index import EntityIndexBuilder
from core.execution.p10_engine import OWNER_REFERENCE, P10ExecutionEngine
from core.investigation.planner import InvestigationPlanner
from core.infrastructure.coverage import InfrastructureCoverageService
from core.infrastructure.owner_direct import OwnerDirectService
from core.tools.command_policy import CommandPolicy
from core.tools.permissions import ToolPermissions
from core.tools.registry import ToolRegistry
from core.tools.workspace_boundary import WorkspaceBoundary


class ToolBrokerError(ValueError):
    pass


class ToolBroker:
    _QUERY = re.compile(r"^[^\x00\r\n]{1,500}$")

    def __init__(
        self,
        base_dir: Path,
        *,
        p7_live_enabled: bool = False,
        p7_scoped_available: bool = False,
        p7_runner: Any = None,
        p10_execution_enabled: bool = False,
        owner_direct_adapters: dict[str, Any] | None = None,
        now: Any = None,
    ):
        self.base_dir = base_dir.resolve()
        policy = yaml.safe_load((self.base_dir / "config/p11_tool_policy.yaml").read_text(encoding="utf-8")) or {}
        self.boundary = WorkspaceBoundary(self.base_dir, policy.get("protected_workspace_paths", []))
        self.permissions = ToolPermissions(self.base_dir)
        self.registry = ToolRegistry()
        self.commands = CommandPolicy(self.base_dir)
        self.p10 = P10ExecutionEngine(base_dir=self.base_dir, execution_enabled=p10_execution_enabled)
        self.owner_direct = OwnerDirectService(self.base_dir, adapters=owner_direct_adapters)
        self.p7_live_enabled = p7_live_enabled
        self.p7_scoped_available = p7_scoped_available
        self._p7_runner = p7_runner
        self._now = now or (lambda: datetime.now(timezone.utc))
        self._plans: dict[str, dict[str, Any]] = {}
        self._approvals: dict[str, dict[str, Any]] = {}
        self._rollbacks: dict[str, dict[str, Any]] = {}
        self._post_apply_digests: dict[str, str] = {}
        self._calls: dict[str, dict[str, Any]] = {}
        self._live_read_plans: dict[str, dict[str, Any]] = {}
        self._live_read_approvals: dict[str, dict[str, Any]] = {}
        self._lock = threading.RLock()
        schema_dir = self.base_dir / "00_meta/schemas"
        self._tool_schema = json.loads((schema_dir / "tool-call.schema.json").read_text(encoding="utf-8"))
        self._plan_schema = json.loads((schema_dir / "workspace-change-plan.schema.json").read_text(encoding="utf-8"))
        self._approval_schema = json.loads((schema_dir / "tool-approval.schema.json").read_text(encoding="utf-8"))
        self._rollback_schema = json.loads((schema_dir / "workspace-rollback-plan.schema.json").read_text(encoding="utf-8"))
        self._live_evidence_schema = json.loads((schema_dir / "live-evidence.schema.json").read_text(encoding="utf-8"))
        binding_catalog = yaml.safe_load((self.base_dir / "config/p7_device_bindings.yaml").read_text(encoding="utf-8")) or {}
        p8_catalog = yaml.safe_load((self.base_dir / "config/p8_diagnostic_catalog.yaml").read_text(encoding="utf-8")) or {}
        self._p7_bindings = {item["binding_id"]: item for item in binding_catalog.get("bindings", [])}
        self._p7_reconciliations = {item["binding_id"]: item for item in p8_catalog.get("reconciliations", [])}
        self._p7_entities = {
            item["entity_id"]: item
            for item in EntityIndexBuilder(self.base_dir).build_index(persist=False).get("entities", [])
        }
        self.coverage = InfrastructureCoverageService(self.base_dir)

    @staticmethod
    def _canonical(value: Any) -> str:
        return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)

    @classmethod
    def _digest(cls, value: Any) -> str:
        return hashlib.sha256(cls._canonical(value).encode("utf-8")).hexdigest()

    @staticmethod
    def _id(prefix: str) -> str:
        return prefix + secrets.token_urlsafe(18)

    def propose(self, *, thread_id: str, turn_id: str, tool_name: str, arguments: dict[str, Any], permission_mode: str) -> dict[str, Any]:
        self.registry.get(tool_name)
        self.permissions.require(permission_mode, tool_name)
        self._validate_tool_arguments(tool_name, arguments)
        call = {"tool_call_id": self._id("tcall_"), "thread_id": thread_id, "turn_id": turn_id, "tool_name": tool_name, "arguments": deepcopy(arguments), "argument_digest": self._digest(arguments), "permission_mode": permission_mode, "status": "PROPOSED", "created_at": self._now().isoformat()}
        jsonschema.Draft7Validator(self._tool_schema, format_checker=jsonschema.FormatChecker()).validate(call)
        with self._lock:
            self._calls[call["tool_call_id"]] = call
        return deepcopy(call)

    @staticmethod
    def _validate_tool_arguments(tool_name: str, arguments: Any) -> None:
        if not isinstance(arguments, dict):
            raise ToolBrokerError("Tool arguments must be an object.")
        contracts = {
            "workspace.list": (set(), {"path"}),
            "workspace.search": ({"query"}, {"query", "path"}),
            "workspace.read": ({"path"}, {"path", "max_bytes"}),
            "workspace.status": (set(), set()),
            "workspace.diff": (set(), set()),
            "workspace.prepare_patch": ({"unified_diff"}, {"unified_diff"}),
            "workspace.apply_approved_patch": ({"plan_id", "approval_id"}, {"plan_id", "approval_id"}),
            "workspace.run_validator": ({"validator_id"}, {"validator_id", "extra_args", "timeout_seconds"}),
            "workspace.prepare_rollback": ({"plan_id"}, {"plan_id"}),
            "workspace.apply_approved_rollback": ({"rollback_id", "approval_id"}, {"rollback_id", "approval_id"}),
            "mne.build_evidence": ({"question"}, {"question", "target_entities", "supplemental_evidence"}),
            "mne.plan_investigation": ({"question"}, {"question"}),
            "mne.prepare_live_read": ({"binding_id", "target", "check_id"}, {"binding_id", "target", "check_id"}),
            "mne.execute_approved_live_read": ({"plan_id", "approval_id"}, {"plan_id", "approval_id"}),
            "owner_direct.discover": ({"entity_id", "protocol", "operation"}, {"entity_id", "protocol", "operation", "target", "owner_supplied_target", "trusted_identity"}),
            "owner_direct.prepare_write": ({"entity_id", "protocol", "operations", "intended_change", "expected_impact", "downtime_risk", "blast_radius", "prechecks", "postchecks", "owner_requested"}, {"entity_id", "protocol", "operations", "intended_change", "expected_impact", "downtime_risk", "blast_radius", "prechecks", "postchecks", "rollback_steps", "trusted_identity", "observed_identity", "target", "owner_supplied_target", "owner_requested"}),
            "owner_direct.identity_audit": ({"requests"}, {"requests"}),
            "p10.prepare": ({"operation_id", "binding_id", "target", "identity_pin", "parameters", "evidence"}, {"operation_id", "binding_id", "target", "identity_pin", "parameters", "evidence", "owner_reference"}),
            "p10.prepare_critical": ({"platform", "binding_id", "target", "identity_pin", "commands", "rollback_commands", "evidence", "warning", "irreversible"}, {"platform", "protocol", "binding_id", "target", "identity_pin", "commands", "rollback_commands", "evidence", "warning", "irreversible", "owner_reference"}),
            "p10.approve": ({"plan_id", "phrase"}, {"plan_id", "phrase"}),
            "p10.execute": ({"plan_id"}, {"plan_id"}),
            "p10.rollback_prepare": ({"plan_id"}, {"plan_id"}),
        }
        required, allowed = contracts[tool_name]
        keys = set(arguments)
        if not required.issubset(keys) or keys.difference(allowed):
            raise ToolBrokerError("Tool arguments do not match the exact handler contract.")

    def list_workspace(self, path: str = ".") -> dict[str, Any]:
        target = self.boundary.resolve(path)
        if not target.is_dir():
            raise ToolBrokerError("Workspace list target is not a directory.")
        entries = []
        for item in sorted(target.iterdir(), key=lambda p: p.name.casefold()):
            relative = str(item.relative_to(self.base_dir)).replace("\\", "/")
            if self.boundary.is_protected(relative) or item.is_symlink():
                continue
            entries.append({"name": item.name, "type": "directory" if item.is_dir() else "file"})
            if len(entries) >= 1000:
                break
        return {"path": str(target.relative_to(self.base_dir)).replace("\\", "/"), "entries": entries}

    def search_workspace(self, query: str, path: str = ".") -> dict[str, Any]:
        if not isinstance(query, str) or not self._QUERY.fullmatch(query):
            raise ToolBrokerError("Search query rejected.")
        root = self.boundary.resolve(path)
        matches: list[dict[str, Any]] = []
        for candidate in root.rglob("*"):
            if len(matches) >= 500 or not candidate.is_file() or candidate.is_symlink() or candidate.stat().st_size > 2_000_000:
                continue
            relative = str(candidate.relative_to(self.base_dir)).replace("\\", "/")
            if self.boundary.is_protected(relative):
                continue
            try:
                for line_no, line in enumerate(candidate.read_text(encoding="utf-8", errors="ignore").splitlines(), 1):
                    if query.casefold() in line.casefold():
                        matches.append({"path": str(candidate.relative_to(self.base_dir)).replace("\\", "/"), "line": line_no, "text": line[:500]})
                        if len(matches) >= 500:
                            break
            except OSError:
                continue
        return {"query": query, "matches": matches}

    def read_workspace(self, path: str, *, max_bytes: int = 200000) -> dict[str, Any]:
        target = self.boundary.resolve(path)
        if not target.is_file() or target.is_symlink():
            raise ToolBrokerError("Workspace read target is not a regular file.")
        raw = target.read_bytes()[: max(1, min(max_bytes, 1_000_000))]
        return {"path": path, "content": raw.decode("utf-8", errors="replace"), "truncated": target.stat().st_size > len(raw)}

    def workspace_status(self) -> dict[str, Any]:
        completed = subprocess.run(["git", "status", "--short"], cwd=self.base_dir, shell=False, capture_output=True, text=True, timeout=30, check=False)
        return {"status": "OK" if completed.returncode == 0 else "FAILED", "lines": completed.stdout.splitlines()[:2000]}

    def workspace_diff(self) -> dict[str, Any]:
        completed = subprocess.run(["git", "diff", "--no-ext-diff", "--"], cwd=self.base_dir, shell=False, capture_output=True, text=True, timeout=30, check=False)
        return {"status": "OK" if completed.returncode == 0 else "FAILED", "unified_diff": completed.stdout[:2_000_000], "truncated": len(completed.stdout) > 2_000_000}

    def _baseline_digest(self, paths: list[str]) -> str:
        state = []
        for path in paths:
            target = self.boundary.resolve(path, for_write=True)
            state.append({"path": path, "exists": target.exists(), "sha256": hashlib.sha256(target.read_bytes()).hexdigest() if target.is_file() else None})
        return self._digest(state)

    def prepare_patch(self, unified_diff: str) -> dict[str, Any]:
        if not isinstance(unified_diff, str) or not unified_diff or len(unified_diff) > 2_000_000 or "\x00" in unified_diff:
            raise ToolBrokerError("Unified diff is invalid.")
        if "GIT binary patch" in unified_diff or re.search(r"(?:new|old|deleted) file mode 120000", unified_diff):
            raise ToolBrokerError("Binary and symlink patches are rejected.")
        paths = self.boundary.parse_diff_paths(unified_diff)
        diff_digest = hashlib.sha256(unified_diff.encode("utf-8")).hexdigest()
        plan_id = self._id("wplan_")
        created = self._now()
        plan = {"plan_id": plan_id, "workspace_root": str(self.base_dir), "unified_diff": unified_diff, "diff_digest": diff_digest, "baseline_digest": self._baseline_digest(paths), "paths": paths, "created_at": created.isoformat(), "expires_at": (created + timedelta(seconds=300)).isoformat(), "status": "PREPARED", "approval_phrase": f"APPROVE WORKSPACE {plan_id} {diff_digest}"}
        jsonschema.Draft7Validator(self._plan_schema, format_checker=jsonschema.FormatChecker()).validate(plan)
        with self._lock:
            self._plans[plan_id] = deepcopy(plan)
        return deepcopy(plan)

    def approve_patch(self, plan_id: str, phrase: str, *, owner_session_digest: str) -> dict[str, Any]:
        with self._lock:
            plan = self._plans.get(plan_id)
            if plan is None or plan["status"] != "PREPARED" or self._now() > datetime.fromisoformat(plan["expires_at"]):
                raise ToolBrokerError("Workspace plan is missing, stale, or already consumed.")
            if phrase != plan["approval_phrase"]:
                raise ToolBrokerError("Exact workspace approval phrase required.")
            approval = {"approval_id": self._id("tappr_"), "tool_call_id": self._id("tcall_"), "owner_session_digest": owner_session_digest, "approved_digest": plan["diff_digest"], "approval_phrase": phrase, "created_at": self._now().isoformat(), "expires_at": plan["expires_at"], "used": False}
            jsonschema.Draft7Validator(self._approval_schema, format_checker=jsonschema.FormatChecker()).validate(approval)
            plan["status"] = "APPROVED"
            self._approvals[approval["approval_id"]] = approval
            return deepcopy(approval)

    def apply_approved_patch(self, plan_id: str, approval_id: str, *, owner_session_digest: str) -> dict[str, Any]:
        with self._lock:
            plan = self._plans.get(plan_id)
            approval = self._approvals.get(approval_id)
            if plan is None or approval is None or plan["status"] != "APPROVED" or approval["used"]:
                raise ToolBrokerError("Approved workspace plan is unavailable.")
            if approval["owner_session_digest"] != owner_session_digest or approval["approved_digest"] != plan["diff_digest"]:
                raise ToolBrokerError("Workspace approval binding changed.")
            if self._now() > datetime.fromisoformat(plan["expires_at"]):
                raise ToolBrokerError("Workspace approval expired.")
            if hashlib.sha256(plan["unified_diff"].encode("utf-8")).hexdigest() != plan["diff_digest"] or self._baseline_digest(plan["paths"]) != plan["baseline_digest"]:
                raise ToolBrokerError("Workspace state or diff changed after approval.")
            approval["used"] = True
        temp_name = None
        try:
            with tempfile.NamedTemporaryFile("w", encoding="utf-8", suffix=".diff", delete=False) as handle:
                handle.write(plan["unified_diff"])
                temp_name = handle.name
            check = subprocess.run(["git", "apply", "--check", "--whitespace=nowarn", temp_name], cwd=self.base_dir, shell=False, capture_output=True, text=True, timeout=30, check=False)
            if check.returncode != 0:
                raise ToolBrokerError("Approved patch no longer applies cleanly.")
            result = subprocess.run(["git", "apply", "--whitespace=nowarn", temp_name], cwd=self.base_dir, shell=False, capture_output=True, text=True, timeout=30, check=False)
            with self._lock:
                plan["status"] = "APPLIED" if result.returncode == 0 else "UNCERTAIN"
            if result.returncode != 0:
                return {"status": "UNCERTAIN", "automatic_retry": False}
            verification = subprocess.run(["git", "apply", "--reverse", "--check", "--whitespace=nowarn", temp_name], cwd=self.base_dir, shell=False, capture_output=True, text=True, timeout=30, check=False)
            if verification.returncode != 0:
                with self._lock:
                    plan["status"] = "UNCERTAIN"
                return {"status": "UNCERTAIN", "automatic_retry": False, "verification_passed": False}
            post_digest = self._baseline_digest(plan["paths"])
            with self._lock:
                self._post_apply_digests[plan_id] = post_digest
            return {"status": "APPLIED", "automatic_retry": False, "verification_passed": True, "rollback_available": True, "paths": deepcopy(plan["paths"])}
        finally:
            if temp_name:
                Path(temp_name).unlink(missing_ok=True)

    def prepare_patch_rollback(self, plan_id: str) -> dict[str, Any]:
        with self._lock:
            plan = deepcopy(self._plans.get(plan_id))
            post_digest = self._post_apply_digests.get(plan_id)
        if plan is None or plan["status"] != "APPLIED" or not post_digest or self._baseline_digest(plan["paths"]) != post_digest:
            raise ToolBrokerError("Workspace rollback is unavailable because the applied state changed.")
        temp_name = None
        try:
            with tempfile.NamedTemporaryFile("w", encoding="utf-8", suffix=".diff", delete=False) as handle:
                handle.write(plan["unified_diff"]); temp_name = handle.name
            check = subprocess.run(["git", "apply", "--reverse", "--check", "--whitespace=nowarn", temp_name], cwd=self.base_dir, shell=False, capture_output=True, text=True, timeout=30, check=False)
            if check.returncode != 0:
                raise ToolBrokerError("Reverse patch no longer applies cleanly.")
        finally:
            if temp_name: Path(temp_name).unlink(missing_ok=True)
        created = self._now(); rollback_id = self._id("wrollback_")
        item = {"rollback_id": rollback_id, "source_plan_id": plan_id, "unified_diff": plan["unified_diff"], "apply_direction": "REVERSE", "diff_digest": plan["diff_digest"], "post_apply_digest": post_digest, "paths": plan["paths"], "created_at": created.isoformat(), "expires_at": (created + timedelta(seconds=300)).isoformat(), "status": "PREPARED", "approval_phrase": f"APPROVE WORKSPACE ROLLBACK {rollback_id} {plan['diff_digest']}"}
        jsonschema.Draft7Validator(self._rollback_schema, format_checker=jsonschema.FormatChecker()).validate(item)
        with self._lock: self._rollbacks[rollback_id] = deepcopy(item)
        return deepcopy(item)

    def approve_patch_rollback(self, rollback_id: str, phrase: str, *, owner_session_digest: str) -> dict[str, Any]:
        with self._lock:
            rollback = self._rollbacks.get(rollback_id)
            if rollback is None or rollback["status"] != "PREPARED" or self._now() > datetime.fromisoformat(rollback["expires_at"]):
                raise ToolBrokerError("Workspace rollback is missing, stale, or already consumed.")
            if phrase != rollback["approval_phrase"]: raise ToolBrokerError("Exact workspace rollback approval phrase required.")
            approval = {"approval_id": self._id("tappr_"), "tool_call_id": self._id("tcall_"), "owner_session_digest": owner_session_digest, "approved_digest": rollback["diff_digest"], "approval_phrase": phrase, "created_at": self._now().isoformat(), "expires_at": rollback["expires_at"], "used": False}
            jsonschema.Draft7Validator(self._approval_schema, format_checker=jsonschema.FormatChecker()).validate(approval)
            rollback["status"] = "APPROVED"; self._approvals[approval["approval_id"]] = approval
            return deepcopy(approval)

    def apply_approved_rollback(self, rollback_id: str, approval_id: str, *, owner_session_digest: str) -> dict[str, Any]:
        with self._lock:
            rollback = self._rollbacks.get(rollback_id); approval = self._approvals.get(approval_id)
            if rollback is None or approval is None or rollback["status"] != "APPROVED" or approval["used"]: raise ToolBrokerError("Approved workspace rollback is unavailable.")
            if approval["owner_session_digest"] != owner_session_digest or approval["approved_digest"] != rollback["diff_digest"]: raise ToolBrokerError("Workspace rollback approval binding changed.")
            if self._now() > datetime.fromisoformat(rollback["expires_at"]) or self._baseline_digest(rollback["paths"]) != rollback["post_apply_digest"]: raise ToolBrokerError("Workspace changed after rollback approval.")
            approval["used"] = True
        temp_name = None
        try:
            with tempfile.NamedTemporaryFile("w", encoding="utf-8", suffix=".diff", delete=False) as handle: handle.write(rollback["unified_diff"]); temp_name = handle.name
            result = subprocess.run(["git", "apply", "--reverse", "--whitespace=nowarn", temp_name], cwd=self.base_dir, shell=False, capture_output=True, text=True, timeout=30, check=False)
            original = self._plans[rollback["source_plan_id"]]
            verified = result.returncode == 0 and self._baseline_digest(rollback["paths"]) == original["baseline_digest"]
            with self._lock: rollback["status"] = "ROLLED_BACK" if verified else "UNCERTAIN"
            return {"status": rollback["status"], "automatic_retry": False, "verification_passed": verified, "paths": deepcopy(rollback["paths"])}
        finally:
            if temp_name: Path(temp_name).unlink(missing_ok=True)

    def live_read_arguments_for_entity(self, entity_id: str) -> dict[str, str] | None:
        """Resolve one canonical entity to one exact active P7 binding without connecting."""
        if not self.p7_scoped_available:
            return None
        entity = self._p7_entities.get(entity_id)
        if not entity or entity_id in self.coverage.target_conflicts:
            return None
        candidates = []
        for binding_id, reconciliation in self._p7_reconciliations.items():
            binding = self._p7_bindings.get(binding_id)
            if (
                reconciliation.get("canonical_entity_id") == entity_id
                and binding
                and binding.get("scope_status") == "ACTIVE"
                and binding.get("read_only") is True
            ):
                candidates.append(binding)
        if not candidates:
            return None
        candidates.sort(key=lambda item: (item.get("check_id") != "ip_interface_brief", item["binding_id"]))
        binding = candidates[0]
        target, _source, mismatch = self.coverage.exact_target(binding, entity)
        if not target or mismatch:
            return None
        return {"binding_id": binding["binding_id"], "target": target, "check_id": binding["check_id"]}

    def live_read_options_for_entity(self, entity_id: str) -> list[dict[str, str]]:
        """Return every exact safe binding for an entity; conflicts fail closed."""
        entity = self._p7_entities.get(entity_id)
        if not self.p7_scoped_available or not entity or entity_id in self.coverage.target_conflicts:
            return []
        options = []
        for binding in self.coverage.bindings_for_entity(entity_id):
            if binding.get("scope_status") != "ACTIVE" or binding.get("read_only") is not True:
                continue
            target, _source, mismatch = self.coverage.exact_target(binding, entity)
            if target and not mismatch:
                options.append({"binding_id": binding["binding_id"], "target": target, "check_id": binding["check_id"]})
        return options

    def _validated_live_read_scope(self, arguments: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
        required = {"binding_id", "target", "check_id"}
        if set(arguments) != required or any(not isinstance(arguments[key], str) or not arguments[key] for key in required):
            raise ToolBrokerError("Exact binding, target, and check authorization are required.")
        if not self.p7_scoped_available:
            raise ToolBrokerError("Owner-scoped P7 live reads are unavailable on this server.")
        binding = self._p7_bindings.get(arguments["binding_id"])
        reconciliation = self._p7_reconciliations.get(arguments["binding_id"])
        entity = self._p7_entities.get(str((reconciliation or {}).get("canonical_entity_id") or ""))
        if not binding or binding.get("scope_status") != "ACTIVE" or binding.get("read_only") is not True:
            raise ToolBrokerError("Exact active read-only P7 binding is required.")
        if not entity or entity["entity_id"] in self.coverage.target_conflicts:
            raise ToolBrokerError("Live-read identity conflict requires owner-reviewed proof before execution.")
        expected_target, _source, mismatch = self.coverage.exact_target(binding, entity)
        if mismatch or expected_target != arguments["target"]:
            raise ToolBrokerError("Live-read target does not match the exact canonical entity.")
        if binding.get("check_id") != arguments["check_id"]:
            raise ToolBrokerError("Live-read check does not match the registered P7 binding.")
        return binding, entity

    def prepare_live_read(self, arguments: dict[str, Any], *, tool_call_id: str | None = None) -> dict[str, Any]:
        binding, entity = self._validated_live_read_scope(arguments)
        created = self._now()
        live_read_id = self._id("lread_")
        authorization = {
            "binding_id": binding["binding_id"],
            "entity_id": entity["entity_id"],
            "target": arguments["target"],
            "check_id": binding["check_id"],
            "protocol": binding["protocol"],
            "identity_mode": binding["identity_mode"],
            "operation_fingerprint": hashlib.sha256(binding["operation"].encode("utf-8")).hexdigest(),
        }
        plan_digest = self._digest(authorization)
        plan = {
            "live_read_id": live_read_id,
            "tool_call_id": tool_call_id or self._id("tcall_"),
            **authorization,
            "plan_digest": plan_digest,
            "created_at": created.isoformat(),
            "expires_at": (created + timedelta(seconds=300)).isoformat(),
            "status": "APPROVAL_REQUIRED",
            "approval_phrase": f"PROCEED LIVE READ {live_read_id} {binding['binding_id']} {binding['check_id']} {arguments['target']}",
            "connection_attempted": False,
            "raw_operation_included": False,
            "globally_enabled": self.p7_live_enabled,
            "owner_scoped_activation_available": self.p7_scoped_available,
        }
        with self._lock:
            self._live_read_plans[live_read_id] = deepcopy(plan)
        return deepcopy(plan)

    def approve_live_read(self, live_read_id: str, phrase: str, *, owner_session_digest: str) -> dict[str, Any]:
        with self._lock:
            plan = self._live_read_plans.get(live_read_id)
            if plan is None or plan["status"] != "APPROVAL_REQUIRED" or self._now() > datetime.fromisoformat(plan["expires_at"]):
                raise ToolBrokerError("Live-read plan is missing, stale, or already consumed.")
            if phrase != plan["approval_phrase"]:
                raise ToolBrokerError("Exact live-read approval phrase required.")
            approval = {
                "approval_id": self._id("tappr_"),
                "tool_call_id": plan["tool_call_id"],
                "owner_session_digest": owner_session_digest,
                "approved_digest": plan["plan_digest"],
                "approval_phrase": phrase,
                "created_at": self._now().isoformat(),
                "expires_at": plan["expires_at"],
                "used": False,
            }
            jsonschema.Draft7Validator(self._approval_schema, format_checker=jsonschema.FormatChecker()).validate(approval)
            plan["status"] = "APPROVED"
            self._live_read_approvals[approval["approval_id"]] = approval
            return deepcopy(approval)

    def execute_live_read(self, live_read_id: str, approval_id: str, *, owner_session_digest: str) -> dict[str, Any]:
        with self._lock:
            plan = self._live_read_plans.get(live_read_id)
            approval = self._live_read_approvals.get(approval_id)
            if plan is None or approval is None or plan["status"] != "APPROVED" or approval["used"]:
                raise ToolBrokerError("Approved live-read plan is unavailable.")
            authorization = {key: plan[key] for key in ("binding_id", "entity_id", "target", "check_id", "protocol", "identity_mode", "operation_fingerprint")}
            if self._digest(authorization) != plan["plan_digest"]:
                raise ToolBrokerError("Live-read plan changed after preparation.")
            if approval["owner_session_digest"] != owner_session_digest or approval["approved_digest"] != plan["plan_digest"]:
                raise ToolBrokerError("Live-read approval binding changed.")
            if self._now() > datetime.fromisoformat(plan["expires_at"]):
                raise ToolBrokerError("Live-read approval expired.")
            if not self.p7_scoped_available:
                raise ToolBrokerError("Owner-scoped P7 live reads are unavailable on this server.")
            approval["used"] = True
            plan["status"] = "RUNNING"
        if self._p7_runner is None:
            from scripts.run_p7_authenticated_baseline import AuthenticatedBaselineRunner
            self._p7_runner = AuthenticatedBaselineRunner(base_dir=self.base_dir)
        try:
            run = self._p7_runner.run_exact(
                owner_proceed=True,
                binding_id=plan["binding_id"],
                target=plan["target"],
                check_id=plan["check_id"],
            )
        except Exception:
            run = {"status": "FAILED", "reason": "TRANSPORT_FAILED", "results": []}
        result = (run.get("results") or [{}])[0]
        transport_status = str(result.get("status") or run.get("reason") or "TRANSPORT_FAILED")
        attempted = bool(result.get("connection_attempted"))
        if run.get("status") != "COMPLETE" or transport_status != "SUCCESS":
            with self._lock:
                plan["status"] = "FAILED"
            return {
                "status": transport_status,
                "attempted": attempted,
                "live_verified": False,
                "evidence": None,
                "automatic_retry": False,
                "raw_output_included": False,
                "credentials_returned": False,
            }
        observed = self._now()
        normalized_facts = result.get("normalized_facts") if isinstance(result.get("normalized_facts"), list) else []
        evidence_content = json.dumps(
            {
                "check_id": plan["check_id"],
                "normalized_fact_count": len(normalized_facts),
                "normalized_fact_sample": normalized_facts[:40],
            },
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )[:16000]
        evidence_seed = {"plan_digest": plan["plan_digest"], "observed_at": observed.isoformat(), "transport_status": transport_status}
        evidence_id = "ev-live-" + self._digest(evidence_seed)[:16]
        evidence = {
            "evidence_id": evidence_id,
            "entity_id": plan["entity_id"],
            "profile_name": plan["binding_id"],
            "platform": self._p7_bindings[plan["binding_id"]]["platform"],
            "source_file": f"live-adapter://{plan['binding_id']}/{plan['check_id']}",
            "source": "owner-authorized read-only transport",
            "evidence_status": "live_verified",
            "trust_level": 5,
            "observed_at": observed.isoformat(),
            "expires_at": (observed + timedelta(minutes=15)).isoformat(),
            "evidence_refs": [evidence_id],
            "verification_target": plan["target"],
            "verification_check_id": plan["check_id"],
            "verification_outcome": "success",
            "scope_reference": live_read_id,
            "transport_status": "SUCCESS",
            "content_sha256": hashlib.sha256(evidence_content.encode("utf-8")).hexdigest(),
            "heading": f"Live P7 verification for {plan['entity_id']}",
            "content": evidence_content,
        }
        jsonschema.Draft7Validator(self._live_evidence_schema, format_checker=jsonschema.FormatChecker()).validate(evidence)
        with self._lock:
            plan["status"] = "COMPLETED"
        return {
            "status": "LIVE_VERIFIED",
            "attempted": True,
            "live_verified": True,
            "evidence": evidence,
            "automatic_retry": False,
            "raw_output_included": False,
            "credentials_returned": False,
            "normalized_facts": deepcopy(normalized_facts),
        }

    def run_owner_autonomous_live_read(self, arguments: dict[str, Any], *, owner_session_digest: str, tool_call_id: str | None = None) -> dict[str, Any]:
        """Run one exact read-only binding under an authenticated owner session.

        Login is the standing authorization for reads. The exact immutable P7 plan is
        still prepared and session-bound internally; no write capability is granted.
        """
        if not re.fullmatch(r"[0-9a-f]{64}", owner_session_digest or ""):
            raise ToolBrokerError("Authenticated owner session is required for automatic live reads.")
        plan = self.prepare_live_read(arguments, tool_call_id=tool_call_id)
        approval = self.approve_live_read(plan["live_read_id"], plan["approval_phrase"], owner_session_digest=owner_session_digest)
        return self.execute_live_read(plan["live_read_id"], approval["approval_id"], owner_session_digest=owner_session_digest)

    def invoke(self, tool_call_id: str, *, owner_session_digest: str | None = None) -> dict[str, Any]:
        """Execute one schema-valid proposal; revalidate its immutable argument digest first."""
        with self._lock:
            call = deepcopy(self._calls.get(tool_call_id))
        if call is None:
            raise ToolBrokerError("Tool call not found.")
        jsonschema.Draft7Validator(self._tool_schema, format_checker=jsonschema.FormatChecker()).validate(call)
        if self._digest(call["arguments"]) != call["argument_digest"]:
            raise ToolBrokerError("Tool-call arguments changed after proposal.")
        self.permissions.require(call["permission_mode"], call["tool_name"])
        name, args = call["tool_name"], call["arguments"]
        if name == "workspace.list":
            result = self.list_workspace(args.get("path", "."))
        elif name == "workspace.search":
            result = self.search_workspace(args["query"], args.get("path", "."))
        elif name == "workspace.read":
            result = self.read_workspace(args["path"], max_bytes=args.get("max_bytes", 200000))
        elif name == "workspace.status":
            result = self.workspace_status()
        elif name == "workspace.diff":
            result = self.workspace_diff()
        elif name == "workspace.prepare_patch":
            result = self.prepare_patch(args["unified_diff"])
        elif name == "workspace.apply_approved_patch":
            if not owner_session_digest:
                raise ToolBrokerError("Owner session binding is required.")
            result = self.apply_approved_patch(args["plan_id"], args["approval_id"], owner_session_digest=owner_session_digest)
        elif name == "workspace.run_validator":
            result = self.commands.run(args["validator_id"], args.get("extra_args", []), timeout_seconds=args.get("timeout_seconds", 300))
        elif name == "workspace.prepare_rollback":
            result = self.prepare_patch_rollback(args["plan_id"])
        elif name == "workspace.apply_approved_rollback":
            if not owner_session_digest: raise ToolBrokerError("Owner session binding is required.")
            result = self.apply_approved_rollback(args["rollback_id"], args["approval_id"], owner_session_digest=owner_session_digest)
        elif name == "mne.build_evidence":
            result = EvidencePackBuilder(self.base_dir).build_evidence_pack(args["question"], args.get("target_entities", []), supplemental_evidence=args.get("supplemental_evidence", []), persist=False)
        elif name == "mne.plan_investigation":
            result = InvestigationPlanner(self.base_dir).plan(args["question"])
        elif name == "mne.prepare_live_read":
            result = self.prepare_live_read(args, tool_call_id=tool_call_id)
        elif name == "mne.execute_approved_live_read":
            if not owner_session_digest:
                raise ToolBrokerError("Owner session binding is required.")
            result = self.execute_live_read(args["plan_id"], args["approval_id"], owner_session_digest=owner_session_digest)
        elif name == "owner_direct.discover":
            result = self.owner_direct.discover(**args)
        elif name == "owner_direct.prepare_write":
            result = self.owner_direct.prepare_write(**args)
        elif name == "owner_direct.identity_audit":
            result = self.owner_direct.identity_audit(**args)
        elif name == "p10.prepare":
            args = {**args, "owner_session_digest": owner_session_digest or ""}
            result = self.p10.prepare(**args)
            result["approval_phrase"] = self.p10.expected_approval_phrase(result["plan_id"])
        elif name == "p10.prepare_critical":
            args = {**args, "owner_session_digest": owner_session_digest or ""}
            result = self.p10.prepare_critical_exception(**args)
            result["approval_phrase"] = self.p10.expected_approval_phrase(result["plan_id"])
        elif name == "p10.approve":
            result = self.p10.approve(
                args["plan_id"], args["phrase"], owner_reference=OWNER_REFERENCE,
                source="local", owner_session_digest=owner_session_digest or "",
            )
        elif name == "p10.execute":
            result = self.p10.execute(args["plan_id"], owner_session_digest=owner_session_digest or "")
        elif name == "p10.rollback_prepare":
            result = self.p10.prepare_rollback(args["plan_id"])
        else:
            raise ToolBrokerError("Tool is declared but has no deterministic handler.")
        with self._lock:
            self._calls[tool_call_id]["status"] = "COMPLETED"
        return {"tool_call_id": tool_call_id, "status": "COMPLETED", "result": result}
