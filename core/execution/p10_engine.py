"""P10 owner-controlled prepare, approve, execute, and rollback workflow."""

from __future__ import annotations

import hashlib
import json
import re
import threading
import uuid
from copy import deepcopy
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Callable

import jsonschema
import yaml

from core.execution.p10_catalog import P10CatalogError, P10OperationCatalog
from core.tools.drivers.p10_write import P10PlatformDriverRegistry


OWNER_REFERENCE = "MNE-BRAIN-OWNER"
PLAN_TTL_SECONDS = 300
OFFLINE_SESSION_DIGEST = hashlib.sha256(b"MNE_BRAIN_P10_OFFLINE_TEST_SESSION").hexdigest()


class P10SafetyError(ValueError):
    """A fail-closed P10 safety boundary rejected the request."""


class P10ExecutionEngine:
    """Keep all P10 state in memory and execute only exact, one-time approvals."""

    _global_execution_lock = threading.Lock()
    _manual_verification_hold = threading.Event()
    _TARGET = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:-]{0,252}$")
    _HASH = re.compile(r"^[a-f0-9]{64}$")
    _FORBIDDEN_RAW = re.compile(
        r"(?:[;&|`]\s*[^\s]|\r|\n|\x00|\$\(|<\(|>\(|\b(?:curl|wget|invoke-webrequest|"
        r"invoke-expression|iex|cmd\.exe|-encodedcommand|frombase64string)\b)",
        re.IGNORECASE,
    )
    _SECRET = re.compile(
        r"(?i)(?:password|passwd|token|secret|authorization|api[_-]?key|private[_-]?key|community)"
        r"\s*[:=]\s*\S+"
    )
    _IRREVERSIBLE = re.compile(r"\b(?:format|erase|destroy|purge|drop|factory[- ]?reset|wipe)\b", re.IGNORECASE)

    def __init__(
        self,
        base_dir: Path | None = None,
        *,
        execution_enabled: bool = False,
        driver: Any | None = None,
        now: Callable[[], datetime] | None = None,
    ):
        self.base_dir = base_dir or Path(__file__).resolve().parent.parent.parent
        self.catalog = P10OperationCatalog(self.base_dir)
        self.policy = yaml.safe_load((self.base_dir / "config/p10_action_policy.yaml").read_text(encoding="utf-8")) or {}
        self.platform_registry = (yaml.safe_load((self.base_dir / "config/p10_platform_registry.yaml").read_text(encoding="utf-8")) or {}).get("platforms", {})
        self._validate_policy()
        bindings = yaml.safe_load((self.base_dir / "config/p7_device_bindings.yaml").read_text(encoding="utf-8")) or {}
        self.bindings = {item["binding_id"]: item for item in bindings.get("bindings", [])}
        self.execution_enabled = execution_enabled
        self.driver = driver or P10PlatformDriverRegistry(base_dir=self.base_dir, live=execution_enabled)
        self._now = now or (lambda: datetime.now(timezone.utc))
        self._plans: dict[str, dict[str, Any]] = {}
        self._results: dict[str, dict[str, Any]] = {}
        self._approvals: dict[str, dict[str, Any]] = {}
        self._used_phrases: set[str] = set()
        self._cancellations: dict[str, threading.Event] = {}
        self._mutations_started: set[str] = set()
        self.audit_records: list[dict[str, Any]] = []
        self._state_lock = threading.RLock()
        self._schemas: dict[str, dict[str, Any]] = {}

    def _validate_contract(self, schema_name: str, instance: Any) -> None:
        schema = self._schemas.get(schema_name)
        if schema is None:
            schema = json.loads((self.base_dir / "00_meta/schemas" / schema_name).read_text(encoding="utf-8"))
            self._schemas[schema_name] = schema
        jsonschema.Draft7Validator(schema, format_checker=jsonschema.FormatChecker()).validate(instance)

    def _validate_policy(self) -> None:
        required = {
            "approval_state": "OWNER_CONTROLLED",
            "owner_reference": OWNER_REFERENCE,
            "audit_mode": "IN_MEMORY_ONLY",
            "retention": "NONE",
            "ticketing_enabled": False,
            "paging_enabled": False,
            "notifications_enabled": False,
            "automatic_assignment_enabled": False,
            "automatic_remediation_enabled": False,
        }
        for key, expected in required.items():
            if self.policy.get(key) != expected:
                raise P10SafetyError(f"P10 policy mismatch for {key}.")

    @staticmethod
    def _canonical(value: Any) -> str:
        return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)

    @classmethod
    def _hash(cls, value: Any) -> str:
        return hashlib.sha256(cls._canonical(value).encode("utf-8")).hexdigest()

    def _session_digest(self, value: Any) -> str:
        if isinstance(value, str) and self._HASH.fullmatch(value):
            return value
        if self.execution_enabled and getattr(self.driver, "live", False):
            raise P10SafetyError("An authenticated owner session binding is required.")
        return OFFLINE_SESSION_DIGEST

    def _approval_digest(self, plan: dict[str, Any]) -> str:
        immutable = {
            key: value for key, value in plan.items()
            if key not in {"integrity_hash", "plan_digest", "status"}
        }
        return self._hash(immutable)

    @staticmethod
    def _iso(moment: datetime) -> str:
        return moment.astimezone(timezone.utc).isoformat()

    @staticmethod
    def _parse_time(value: Any) -> datetime:
        if not isinstance(value, str):
            raise P10SafetyError("Evidence timestamp is required.")
        try:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError as exc:
            raise P10SafetyError("Evidence timestamp is invalid.") from exc
        if parsed.tzinfo is None:
            raise P10SafetyError("Evidence timestamp must include a timezone.")
        return parsed.astimezone(timezone.utc)

    def _binding(self, binding_id: Any, platform: str) -> dict[str, Any]:
        if not isinstance(binding_id, str) or binding_id not in self.bindings:
            raise P10SafetyError("One exact registered P7 binding is required.")
        binding = self.bindings[binding_id]
        if binding.get("scope_status") != "ACTIVE":
            raise P10SafetyError("The selected P7 binding is not active.")
        compatible = {
            "windows_powershell": {"windows_identity", "microsoft_exchange"},
            "cisco_switching": {"cisco_iosxe", "cisco_router"},
            "fujitsu_switching": {"fujitsu_switch"},
            "linux_host": {"linux_host"},
            "vmware_vcenter": {"vmware_vcenter"},
            "fortinet_fortios": {"fortinet_fortios"},
            "f5_bigip": {"f5_bigip"},
            "cisco_fmc": {"cisco_fmc"},
        }
        if binding.get("platform") not in compatible.get(platform, {platform}):
            raise P10SafetyError("Operation platform does not match the exact P7 binding.")
        return deepcopy(binding)

    def _validate_target(self, target: Any) -> str:
        if not isinstance(target, str) or not self._TARGET.fullmatch(target):
            raise P10SafetyError("An exact hostname or IP target is required.")
        if "*" in target or target in {"0.0.0.0", "::", "all", "any"}:
            raise P10SafetyError("Wildcard or non-exact targets are prohibited.")
        return target

    def _validate_evidence(
        self,
        evidence: Any,
        *,
        binding_id: str,
        target: str,
        identity_pin: str,
        required_checks: list[str],
        prohibited_conditions: list[str],
    ) -> dict[str, Any]:
        if not isinstance(evidence, dict):
            raise P10SafetyError("Recent read-only evidence is required.")
        required_fields = {"evidence_id", "observed_at", "binding_id", "target", "identity_pin", "state_digest", "checks", "facts"}
        if set(evidence) != required_fields:
            raise P10SafetyError("Evidence fields do not match the P10 contract.")
        if evidence["binding_id"] != binding_id or evidence["target"] != target:
            raise P10SafetyError("Evidence is not bound to the exact target and binding.")
        if evidence["identity_pin"] != identity_pin or not identity_pin:
            raise P10SafetyError("Pinned identity proof is missing or changed.")
        observed = self._parse_time(evidence["observed_at"])
        age = (self._now() - observed).total_seconds()
        if age < -30 or age > PLAN_TTL_SECONDS:
            raise P10SafetyError("Read-only evidence is stale or future-dated.")
        if not isinstance(evidence["state_digest"], str) or not self._HASH.fullmatch(evidence["state_digest"]):
            raise P10SafetyError("Evidence state digest is invalid.")
        if not isinstance(evidence["checks"], list) or not isinstance(evidence["facts"], dict):
            raise P10SafetyError("Evidence checks or facts are malformed.")
        check_map = {item.get("check_id"): item for item in evidence["checks"] if isinstance(item, dict)}
        for check in evidence["checks"]:
            try:
                self._validate_contract("p10-check-result.schema.json", check)
            except jsonschema.ValidationError as exc:
                raise P10SafetyError(f"Pre-check result contract failed: {exc.message}") from exc
        missing = [check for check in required_checks if not check_map.get(check, {}).get("passed")]
        if missing:
            raise P10SafetyError(f"Required read-only pre-checks failed or are missing: {missing}")
        active_prohibitions = [condition for condition in prohibited_conditions if evidence["facts"].get(condition) is True]
        if active_prohibitions:
            raise P10SafetyError(f"Prohibited target state detected: {active_prohibitions}")
        if evidence["facts"].get("unrelated_pending_changes") is True:
            raise P10SafetyError("Unrelated pending changes were discovered.")
        return deepcopy(evidence)

    def prepare(
        self,
        operation_id: str,
        *,
        binding_id: str,
        target: str,
        identity_pin: str,
        parameters: dict[str, Any],
        evidence: dict[str, Any],
        owner_reference: str = OWNER_REFERENCE,
        owner_session_digest: str = "",
        precheck_runner: Callable[[dict[str, Any]], dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        if owner_reference != OWNER_REFERENCE:
            raise P10SafetyError("Only MNE-BRAIN-OWNER may prepare a write plan.")
        session_digest = self._session_digest(owner_session_digest)
        operation = self.catalog.get(operation_id)
        exact_target = self._validate_target(target)
        binding = self._binding(binding_id, operation["platform"])
        if binding_id not in operation["allowed_bindings"]:
            raise P10SafetyError("The exact P7 binding is outside this reviewed operation template.")
        parameters = self.catalog.validate_parameters(operation, parameters)
        self._validate_contract("p10-operation-parameters.schema.json", {
            "operation_id": operation_id, "binding_id": binding_id, "target": exact_target,
            "identity_pin": identity_pin, "parameters": parameters, "evidence": evidence,
        })
        prepared_evidence = precheck_runner(deepcopy(evidence)) if precheck_runner else evidence
        prepared_evidence = self._validate_evidence(
            prepared_evidence,
            binding_id=binding_id,
            target=exact_target,
            identity_pin=identity_pin,
            required_checks=operation["pre_checks"],
            prohibited_conditions=operation["prohibited_conditions"],
        )
        command_bundle = self.catalog.render(operation, parameters, target=exact_target)
        rollback_bundle = self.catalog.render(operation, parameters, target=exact_target, rollback=True)
        if operation["rollback_strategy"] == "NO_SAFE_ROLLBACK":
            rollback_bundle = {"commands": [], "display_commands": ["NO SAFE ROLLBACK"], "bundle_hash": self._hash("NO SAFE ROLLBACK"), "contains_credentials": False, "hidden_chaining": False}
        elif not rollback_bundle["commands"]:
            raise P10SafetyError("A safe rollback must be generated during preparation.")
        if self.execution_enabled and getattr(self.driver, "live", False):
            if not all(hasattr(self.driver, method) for method in ("probe_write_authorization", "capture_state")):
                raise P10SafetyError("The live driver lacks mandatory authorization or state probes.")
            authorization = self.driver.probe_write_authorization(
                platform=operation["platform"], binding_id=binding_id, target=exact_target,
                timeout_seconds=min(int(operation["timeout_seconds"]), 30),
            )
            if authorization.get("write_authorized") is not True:
                raise P10SafetyError(f"Write authorization is not established: {authorization.get('status', 'UNKNOWN')}")
            live_state = self.driver.capture_state(
                platform=operation["platform"], binding_id=binding_id, target=exact_target,
                commands=deepcopy(command_bundle["commands"]), timeout_seconds=min(int(operation["timeout_seconds"]), 30), postcheck=False,
            )
            if live_state.get("status") not in {"SUCCESS", "SUCCESS_ABSENT"} or not self._HASH.fullmatch(str(live_state.get("state_digest", ""))):
                raise P10SafetyError(f"Fresh exact read-only state probe failed: {live_state.get('status', 'UNKNOWN')}")
            if live_state.get("identity_pin") != identity_pin:
                raise P10SafetyError("Configured target identity differs from the proposed identity pin.")
            prepared_evidence["state_digest"] = live_state["state_digest"]
        now = self._now()
        critical = bool(operation["requires_critical_exception"] or operation["risk_level"] == 4)
        approval_kind = "CRITICAL" if critical else "CATALOGED"
        plan_core = {
            "operation_id": operation_id,
            "template_version": operation["template_version"],
            "platform": operation["platform"],
            "protocol": self.platform_registry[operation["platform"]]["transport"],
            "binding_id": binding_id,
            "target": exact_target,
            "parameters": parameters,
            "risk_level": operation["risk_level"],
            "approval_kind": approval_kind,
            "command_hash": command_bundle["bundle_hash"],
            "rollback_hash": rollback_bundle["bundle_hash"],
            "target_identity_hash": self._hash({"binding_id": binding_id, "target": exact_target, "identity_pin": identity_pin}),
            "state_digest": prepared_evidence["state_digest"],
        }
        plan_id = f"p10-{self._hash({**plan_core, 'nonce': uuid.uuid4().hex})[:20]}"
        plan = {
            "plan_id": plan_id,
            **plan_core,
            "title": operation["title"],
            "operation_type": operation["operation_type"],
            "status": "PREPARED",
            "created_at": self._iso(now),
            "expires_at": self._iso(now + timedelta(seconds=PLAN_TTL_SECONDS)),
            "single_use": True,
            "owner_reference": OWNER_REFERENCE,
            "approval_state": "OWNER_CONTROLLED",
            "audit_mode": "IN_MEMORY_ONLY",
            "retention": "NONE",
            "command_bundle": command_bundle,
            "rollback_bundle": rollback_bundle,
            "identity_pin": identity_pin,
            "evidence_id": prepared_evidence["evidence_id"],
            "pre_check_results": prepared_evidence["checks"],
            "post_checks": operation["post_checks"],
            "rollback_strategy": "PREAPPROVED_AUTOMATIC_ON_DECLARED_FAILURE" if rollback_bundle["commands"] else "NO_SAFE_ROLLBACK",
            "transaction_mode": operation["transaction_mode"],
            "timeout_seconds": operation["timeout_seconds"],
            "expected_impact": operation["expected_impact"],
            "risk_preview": self._risk_preview(operation, exact_target),
            "blast_radius": f"One exact target: {exact_target}. Dependencies are displayed separately and are not implicit write targets.",
            "possible_downtime": operation["expected_impact"],
            "worst_reasonable_failure": "The exact target may lose the affected service or management access until the displayed rollback is verified.",
            "intended_changes": f"{operation['title']} on exact target {exact_target} using only the displayed immutable operation bundle.",
            "affected_systems": [exact_target],
            "dependencies": list(operation["prohibited_conditions"]),
            "backup_snapshot": (
                "The platform-native transaction provides a pre-commit abort checkpoint; no separate backup is claimed."
                if operation["transaction_mode"] == "PLATFORM_NATIVE_TRANSACTION"
                else "No automatic backup or snapshot is claimed. The exact rollback bundle is prepared before approval."
            ),
            "rollback_conditions": [
                "Abort an open platform transaction if pre-commit validation fails.",
                "Run the displayed rollback automatically only when a declared post-change validation condition fails.",
            ],
            "success_conditions": [f"Every independent post-check passes: {check}." for check in operation["post_checks"]],
            "failure_conditions": [f"Independent post-check fails: {check}." for check in operation["post_checks"]],
            "non_rollbackable_operations": (["This complete action has no safe automatic rollback."] if operation["rollback_strategy"] == "NO_SAFE_ROLLBACK" else []),
            "critical_warning": self._critical_warning(operation, exact_target, command_bundle, rollback_bundle) if critical else None,
            "supports_dry_run": operation["supports_dry_run"],
            "maximum_targets": 1,
            "live_connection_attempted": False,
            "persistence_attempted": False,
            "owner_session_digest": session_digest,
            "owner_session_binding": self._hash(session_digest),
        }
        plan["plan_digest"] = self._approval_digest(plan)
        plan["integrity_hash"] = self._integrity_hash(plan)
        self._validate_contract("p10-prepared-plan.schema.json", self._public_plan(plan))
        with self._state_lock:
            self._plans[plan_id] = deepcopy(plan)
            self._cancellations[plan_id] = threading.Event()
            self._audit("PLAN_PREPARED", plan_id=plan_id, operation_id=operation_id)
        return self._public_plan(plan)

    def prepare_critical_exception(
        self,
        *,
        platform: str,
        binding_id: str,
        target: str,
        identity_pin: str,
        commands: list[str],
        rollback_commands: list[str],
        evidence: dict[str, Any],
        warning: dict[str, Any],
        protocol: str = "",
        irreversible: bool = False,
        owner_reference: str = OWNER_REFERENCE,
        owner_session_digest: str = "",
    ) -> dict[str, Any]:
        if owner_reference != OWNER_REFERENCE:
            raise P10SafetyError("Only MNE-BRAIN-OWNER may prepare a critical exception.")
        session_digest = self._session_digest(owner_session_digest)
        exact_target = self._validate_target(target)
        self._binding(binding_id, platform)
        if platform == "cisco_ftd":
            raise P10SafetyError("FMC-managed FTD changes must use the cisco_fmc platform and exact FMC REST binding.")
        expected_protocol = str((self.platform_registry.get(platform) or {}).get("transport", ""))
        selected_protocol = protocol or expected_protocol
        if not expected_protocol or selected_protocol != expected_protocol:
            raise P10SafetyError("Expert fallback protocol does not match the registered platform transport.")
        required_warning = {
            "outside_catalog_reason", "expected_outcome", "blast_radius", "downtime_risk",
            "management_access_risk", "security_risk", "data_loss_risk", "dependencies_affected",
            "reversibility", "out_of_band_recovery",
        }
        if not isinstance(warning, dict) or set(warning) != required_warning or any(not isinstance(v, str) or not v.strip() for v in warning.values()):
            raise P10SafetyError("The complete critical warning contract is required.")
        command_bundle = self._raw_bundle(commands, rollback=False)
        if not irreversible and any(self._IRREVERSIBLE.search(command) for command in commands):
            raise P10SafetyError("A destructive or irreversible command requires irreversible approval mode.")
        rollback_bundle = self._raw_bundle(rollback_commands, rollback=True) if rollback_commands else {
            "commands": [], "display_commands": ["NO SAFE ROLLBACK"], "bundle_hash": self._hash("NO SAFE ROLLBACK"), "contains_credentials": False, "hidden_chaining": False,
        }
        checked = self._validate_evidence(
            evidence, binding_id=binding_id, target=exact_target, identity_pin=identity_pin,
            required_checks=["critical_scope_verified"], prohibited_conditions=["unrelated_pending_changes"],
        )
        now = self._now()
        approval_kind = "IRREVERSIBLE" if irreversible else "CRITICAL"
        core = {
            "operation_id": "critical-exception",
            "template_version": "exception-1.0",
            "platform": platform,
            "protocol": selected_protocol,
            "binding_id": binding_id,
            "target": exact_target,
            "parameters": {},
            "risk_level": 4,
            "approval_kind": approval_kind,
            "command_hash": command_bundle["bundle_hash"],
            "rollback_hash": rollback_bundle["bundle_hash"],
            "target_identity_hash": self._hash({"binding_id": binding_id, "target": exact_target, "identity_pin": identity_pin}),
            "state_digest": checked["state_digest"],
        }
        plan_id = f"p10-{self._hash({**core, 'nonce': uuid.uuid4().hex})[:20]}"
        critical_warning = {"target": exact_target, "exact_commands": command_bundle["display_commands"], **warning,
            "rollback": rollback_bundle["display_commands"] if rollback_commands else "NO SAFE ROLLBACK",
            "command_hash": command_bundle["bundle_hash"], "rollback_hash": rollback_bundle["bundle_hash"]}
        plan = {
            "plan_id": plan_id, **core, "title": "Critical exception", "operation_type": "critical_exception",
            "status": "PREPARED", "created_at": self._iso(now), "expires_at": self._iso(now + timedelta(seconds=PLAN_TTL_SECONDS)),
            "single_use": True, "owner_reference": OWNER_REFERENCE, "approval_state": "OWNER_CONTROLLED",
            "audit_mode": "IN_MEMORY_ONLY", "retention": "NONE", "command_bundle": command_bundle,
            "rollback_bundle": rollback_bundle, "identity_pin": identity_pin, "evidence_id": checked["evidence_id"],
            "pre_check_results": checked["checks"], "post_checks": ["critical_effect_verified"],
            "rollback_strategy": "PREAPPROVED_AUTOMATIC_ON_DECLARED_FAILURE" if rollback_commands else "NO_SAFE_ROLLBACK",
            "transaction_mode": "EXPLICIT_ORDERED_BUNDLE", "timeout_seconds": 30,
            "expected_impact": warning["expected_outcome"], "risk_preview": warning["blast_radius"],
            "blast_radius": warning["blast_radius"], "possible_downtime": warning["downtime_risk"],
            "worst_reasonable_failure": warning["data_loss_risk"],
            "intended_changes": f"Critical exception on exact target {exact_target} using only the displayed immutable command bundle.",
            "affected_systems": [exact_target], "dependencies": [warning["dependencies_affected"]],
            "backup_snapshot": "No automatic backup or snapshot is claimed for a critical exception; the displayed rollback is the only prepared recovery path.",
            "rollback_conditions": ["Run the displayed rollback only when the declared independent post-change validation fails."],
            "success_conditions": ["The exact critical scope passes independent post-change validation."],
            "failure_conditions": ["The exact critical scope fails independent post-change validation."],
            "non_rollbackable_operations": (["The approved critical exception is explicitly marked irreversible."] if irreversible or not rollback_commands else []),
            "critical_warning": critical_warning, "supports_dry_run": False, "maximum_targets": 1,
            "live_connection_attempted": False, "persistence_attempted": False,
            "owner_session_digest": session_digest, "owner_session_binding": self._hash(session_digest),
        }
        plan["plan_digest"] = self._approval_digest(plan)
        plan["integrity_hash"] = self._integrity_hash(plan)
        self._validate_contract("p10-critical-warning.schema.json", critical_warning)
        self._validate_contract("p10-prepared-plan.schema.json", self._public_plan(plan))
        with self._state_lock:
            self._plans[plan_id] = deepcopy(plan)
            self._cancellations[plan_id] = threading.Event()
            self._audit("CRITICAL_PLAN_PREPARED", plan_id=plan_id, operation_id="critical-exception")
        return self._public_plan(plan)

    def _raw_bundle(self, commands: Any, *, rollback: bool) -> dict[str, Any]:
        if not isinstance(commands, list) or not 1 <= len(commands) <= 20:
            raise P10SafetyError("A visible ordered command list of 1 through 20 commands is required.")
        bundle = []
        for index, command in enumerate(commands, 1):
            if not isinstance(command, str) or not command.strip() or len(command) > 2048:
                raise P10SafetyError("Critical commands must be bounded non-empty strings.")
            if self._FORBIDDEN_RAW.search(command) or self._SECRET.search(command) or "*" in command:
                raise P10SafetyError("Hidden chains, wildcards, scripts, downloads, and secrets are prohibited.")
            bundle.append({"sequence": index, "display": command.strip(), "transaction": {"kind": "VISIBLE_RAW_EXCEPTION", "command": command.strip(), "rollback": rollback}})
        displays = [item["display"] for item in bundle]
        return {"commands": bundle, "display_commands": displays, "bundle_hash": self._hash(displays), "contains_credentials": False, "hidden_chaining": False}

    @staticmethod
    def _risk_preview(operation: dict[str, Any], target: str) -> str:
        return f"Level {operation['risk_level']} {operation['operation_type']} on exact target {target}. {operation['expected_impact']}"

    @staticmethod
    def _critical_warning(operation: dict[str, Any], target: str, command: dict[str, Any], rollback: dict[str, Any]) -> dict[str, Any]:
        return {
            "target": target,
            "exact_commands": command["display_commands"],
            "outside_catalog_reason": "Reviewed template is classified as Level 4 or critical-exception-only.",
            "expected_outcome": operation["expected_impact"],
            "blast_radius": "May affect infrastructure availability beyond the named object.",
            "downtime_risk": "HIGH",
            "management_access_risk": "POSSIBLE",
            "security_risk": "HIGH",
            "data_loss_risk": "POSSIBLE",
            "dependencies_affected": operation["prohibited_conditions"],
            "reversibility": operation["rollback_strategy"],
            "rollback": rollback["display_commands"] or "NO SAFE ROLLBACK",
            "out_of_band_recovery": "MUST BE CONFIRMED BEFORE LIVE USE",
            "command_hash": command["bundle_hash"],
            "rollback_hash": rollback["bundle_hash"],
        }

    def expected_approval_phrase(self, plan_id: str) -> str:
        plan = self._get_internal(plan_id)
        if plan["approval_kind"] == "CATALOGED":
            return f"APPROVE {plan_id} {plan['command_hash']} {plan['plan_digest']}"
        if plan["approval_kind"] == "CRITICAL":
            return f"APPROVE CRITICAL {plan_id} {plan['command_hash']} {plan['plan_digest']} I ACCEPT THE STATED RISKS"
        return f"APPROVE IRREVERSIBLE {plan_id} {plan['command_hash']} {plan['plan_digest']} I ACCEPT PERMANENT DATA OR SERVICE LOSS"

    def approve(self, plan_id: str, phrase: str, *, owner_reference: str, source: str = "local", owner_session_digest: str = "") -> dict[str, Any]:
        with self._state_lock:
            plan = self._get_internal(plan_id)
            self._assert_prepared(plan)
            if owner_reference != OWNER_REFERENCE or source != "local":
                raise P10SafetyError("Approval is accepted only from the local sole owner interface.")
            expected = self.expected_approval_phrase(plan_id)
            phrase_fingerprint = self._hash(phrase)
            if phrase != expected:
                raise P10SafetyError("Approval phrase does not exactly match the prepared plan.")
            if phrase_fingerprint in self._used_phrases:
                raise P10SafetyError("Approval replay rejected.")
            session_digest = self._session_digest(owner_session_digest)
            if session_digest != plan["owner_session_digest"]:
                raise P10SafetyError("Approval belongs to a different owner session.")
            if plan.get("plan_digest") != self._approval_digest(plan):
                raise P10SafetyError("The complete immutable plan digest changed before approval.")
            approval_id = f"approval-{uuid.uuid4().hex[:16]}"
            approval = {
                "approval_id": approval_id, "plan_id": plan_id, "approved_at": self._iso(self._now()),
                "expires_at": plan["expires_at"], "used": False, "owner_reference": OWNER_REFERENCE,
                "owner_session_digest": session_digest, "approved_digest": plan["plan_digest"],
                "phrase_fingerprint": phrase_fingerprint,
            }
            self._approvals[plan_id] = approval
            plan["status"] = "APPROVED"
            plan["integrity_hash"] = self._integrity_hash(plan)
            self._plans[plan_id] = plan
            self._audit("PLAN_APPROVED", plan_id=plan_id, operation_id=plan["operation_id"])
            return {key: value for key, value in approval.items() if key != "phrase_fingerprint"}

    def execute(
        self,
        plan_id: str,
        *,
        owner_session_digest: str = "",
        state_probe: Callable[[dict[str, Any]], dict[str, Any]] | None = None,
        postcheck_runner: Callable[[dict[str, Any], dict[str, Any]], list[dict[str, Any]]] | None = None,
        cancellation_event: threading.Event | None = None,
    ) -> dict[str, Any]:
        plan = self._get_internal(plan_id)
        if plan["status"] != "APPROVED" or plan_id not in self._approvals:
            raise P10SafetyError("An unused exact approval is required.")
        session_digest = self._session_digest(owner_session_digest)
        approval = self._approvals[plan_id]
        if session_digest != plan["owner_session_digest"] or session_digest != approval["owner_session_digest"]:
            raise P10SafetyError("Execution belongs to a different owner session.")
        if approval.get("approved_digest") != plan.get("plan_digest") or plan.get("plan_digest") != self._approval_digest(plan):
            raise P10SafetyError("The approved immutable plan digest changed.")
        cancellation_event = cancellation_event or self._cancellations.setdefault(plan_id, threading.Event())
        if not self.execution_enabled:
            return self._result(plan, "EXECUTION_DISABLED", submitted=False, driver_status="EXECUTION_DISABLED")
        if self._manual_verification_hold.is_set():
            return self._result(plan, "GLOBAL_MANUAL_VERIFICATION_HOLD", submitted=False, driver_status=None)
        if state_probe is None and getattr(self.driver, "live", False) and hasattr(self.driver, "capture_state"):
            def state_probe(_public_plan: dict[str, Any]) -> dict[str, Any]:
                state = self.driver.capture_state(
                    platform=plan["platform"], binding_id=plan["binding_id"], target=plan["target"],
                    commands=deepcopy(plan["command_bundle"]["commands"]), timeout_seconds=min(int(plan["timeout_seconds"]), 30), postcheck=False,
                )
                if state.get("status") not in {"SUCCESS", "SUCCESS_ABSENT"}:
                    return {}
                return {"identity_pin": state.get("identity_pin"), "state_digest": state.get("state_digest"), "unrelated_pending_changes": False}
        if postcheck_runner is None and getattr(self.driver, "live", False) and hasattr(self.driver, "capture_state"):
            def postcheck_runner(_public_plan: dict[str, Any], _driver_metadata: dict[str, Any]) -> list[dict[str, Any]]:
                state = self.driver.capture_state(
                    platform=plan["platform"], binding_id=plan["binding_id"], target=plan["target"],
                    commands=deepcopy(plan["command_bundle"]["commands"]), timeout_seconds=min(int(plan["timeout_seconds"]), 30), postcheck=True,
                )
                passed = state.get("status") in {"SUCCESS", "SUCCESS_ABSENT"} and state.get("effect_verified") is True
                observed = self._iso(self._now())
                return [{"check_id": check, "passed": passed, "read_only": True, "evidence_id": f"post-{plan['plan_id']}", "observed_at": observed,
                         "detail": "Exact independent state query matched the expected effect." if passed else f"Exact state verification failed: {state.get('status', 'UNKNOWN')}"}
                        for check in plan["post_checks"]]
        if state_probe is None or postcheck_runner is None:
            raise P10SafetyError("Fresh pre-check and independent post-check runners are mandatory.")
        if cancellation_event and cancellation_event.is_set():
            return self._result(plan, "CANCELLED", submitted=False, driver_status=None)
        if not self._global_execution_lock.acquire(blocking=False):
            return self._result(plan, "CONCURRENT_EXECUTION_BLOCKED", submitted=False, driver_status=None)
        try:
            with self._state_lock:
                plan = self._get_internal(plan_id)
                self._assert_integrity(plan)
                self._assert_not_expired(plan)
                approval = self._approvals[plan_id]
                if approval["used"]:
                    raise P10SafetyError("Approval has already been consumed.")
                if approval.get("approved_digest") != plan.get("plan_digest"):
                    raise P10SafetyError("Approval digest mismatch.")
            fresh = state_probe(self._public_plan(plan))
            if not isinstance(fresh, dict):
                raise P10SafetyError("Fresh pre-check state is unavailable.")
            if fresh.get("identity_pin") != plan["identity_pin"]:
                return self._consume_and_result(plan, "IDENTITY_PIN_CHANGED", submitted=False, driver_status=None)
            if fresh.get("state_digest") != plan["state_digest"]:
                return self._consume_and_result(plan, "PRECHECK_STATE_CHANGED", submitted=False, driver_status=None)
            if fresh.get("unrelated_pending_changes") is True:
                return self._consume_and_result(plan, "UNRELATED_PENDING_CHANGES", submitted=False, driver_status=None)
            if cancellation_event and cancellation_event.is_set():
                return self._consume_and_result(plan, "CANCELLED", submitted=False, driver_status=None)
            with self._state_lock:
                self._approvals[plan_id]["used"] = True
                self._used_phrases.add(self._approvals[plan_id]["phrase_fingerprint"])
                plan["status"] = "EXECUTING"
                plan["integrity_hash"] = self._integrity_hash(plan)
                self._plans[plan_id] = plan
                self._mutations_started.add(plan_id)
            driver_result = self._invoke_driver(plan)
            driver_status = driver_result.get("status", "UNKNOWN") if isinstance(driver_result, dict) else "UNKNOWN"
            submitted = bool(isinstance(driver_result, dict) and driver_result.get("submitted"))
            raw_output = driver_result.pop("output", None) if isinstance(driver_result, dict) else None
            if raw_output is not None:
                output_size = len(raw_output) if isinstance(raw_output, bytes) else len(str(raw_output).encode("utf-8", errors="replace"))
                if output_size > int(self.policy["maximum_driver_output_bytes"]):
                    return self._result(plan, "UNCERTAIN" if submitted else "OUTPUT_LIMIT_EXCEEDED", submitted=submitted, driver_status="OUTPUT_LIMIT_EXCEEDED")
            if driver_status in {"TIMEOUT", "UNKNOWN", "UNCERTAIN", "NETWORK_LOST"}:
                return self._result(plan, "UNCERTAIN", submitted=submitted, driver_status=driver_status)
            if driver_status not in {"SUBMITTED", "SUCCESS", "COMMITTED"}:
                if isinstance(driver_result, dict) and driver_result.get("transaction_state") == "OPEN" and driver_result.get("transaction_id"):
                    try:
                        abort = self.driver.abort(transaction_id=driver_result["transaction_id"])
                    except Exception:
                        abort = {"status": "ABORT_UNAVAILABLE"}
                    return self._result(plan, "FAILED_TRANSACTION_ABORTED" if abort.get("status") == "ABORTED" else "UNCERTAIN", submitted=submitted, driver_status=driver_status)
                return self._result(plan, "FAILED", submitted=submitted, driver_status=driver_status)
            safe_driver_metadata = {
                key: driver_result.get(key) for key in ("status", "submitted", "transaction_state", "transaction_id") if key in driver_result
            }
            try:
                post_results = postcheck_runner(self._public_plan(plan), safe_driver_metadata)
            except Exception:
                return self._result(plan, "UNCERTAIN", submitted=submitted, driver_status=driver_status)
            if not isinstance(post_results, list) or not post_results:
                return self._result(plan, "UNCERTAIN", submitted=submitted, driver_status=driver_status)
            try:
                for check in post_results:
                    self._validate_contract("p10-check-result.schema.json", check)
            except jsonschema.ValidationError:
                return self._result(plan, "UNCERTAIN", submitted=submitted, driver_status=driver_status)
            passed = all(isinstance(item, dict) and item.get("passed") is True and item.get("read_only") is True for item in post_results)
            if passed:
                return self._result(plan, "SUCCESS", submitted=submitted, driver_status=driver_status, post_checks=post_results)
            return self._automatic_rollback(plan, state_probe=state_probe, driver_status=driver_status, post_results=post_results)
        finally:
            self._global_execution_lock.release()

    def request_cancel(self, plan_id: str) -> dict[str, Any]:
        """Cancel safely before submission; never pretend an in-flight write stopped."""
        with self._state_lock:
            plan = self._plans.get(plan_id)
            if plan is None:
                raise P10SafetyError("Prepared plan was not found in memory.")
            if plan_id in self._mutations_started or plan.get("status") == "EXECUTING":
                return {
                    "plan_id": plan_id, "status": "MUTATION_ALREADY_STARTED",
                    "automatic_retry": False, "manual_verification_required": True,
                }
            event = self._cancellations.setdefault(plan_id, threading.Event())
            event.set()
            return {
                "plan_id": plan_id, "status": "CANCELLATION_REQUESTED",
                "automatic_retry": False, "manual_verification_required": False,
            }

    def _automatic_rollback(
        self,
        plan: dict[str, Any],
        *,
        state_probe: Callable[[dict[str, Any]], dict[str, Any]],
        driver_status: str,
        post_results: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """Use the already approved rollback only for a declared failed postcheck."""
        if plan["rollback_strategy"] != "PREAPPROVED_AUTOMATIC_ON_DECLARED_FAILURE" or not plan["rollback_bundle"]["commands"]:
            return self._result(
                plan, "POSTCHECK_FAILED", submitted=True, driver_status=driver_status,
                post_checks=post_results, rollback_status="NO_SAFE_ROLLBACK", rollback_result=None,
            )
        rollback_plan = deepcopy(plan)
        rollback_plan["command_bundle"] = deepcopy(plan["rollback_bundle"])
        rollback_driver = self._invoke_driver(rollback_plan)
        rollback_driver.pop("output", None)
        rollback_status = str(rollback_driver.get("status", "UNKNOWN"))
        rollback_submitted = bool(rollback_driver.get("submitted"))
        if rollback_status in {"TIMEOUT", "UNKNOWN", "UNCERTAIN", "NETWORK_LOST"}:
            return self._result(
                plan, "UNCERTAIN", submitted=True, driver_status=driver_status, post_checks=post_results,
                rollback_status="UNCERTAIN", rollback_result={"status": rollback_status, "submitted": rollback_submitted, "verified": False},
            )
        if rollback_status not in {"SUBMITTED", "SUCCESS", "COMMITTED"}:
            return self._result(
                plan, "ROLLBACK_FAILED", submitted=True, driver_status=driver_status, post_checks=post_results,
                rollback_status="FAILED", rollback_result={"status": rollback_status, "submitted": rollback_submitted, "verified": False},
            )
        try:
            restored = state_probe(self._public_plan(plan))
        except Exception:
            restored = {}
        verified = (
            restored.get("identity_pin") == plan["identity_pin"]
            and restored.get("state_digest") == plan["state_digest"]
            and restored.get("unrelated_pending_changes") is not True
        )
        return self._result(
            plan, "ROLLED_BACK_AFTER_POSTCHECK_FAILURE" if verified else "UNCERTAIN",
            submitted=True, driver_status=driver_status, post_checks=post_results,
            rollback_status="VERIFIED" if verified else "UNCERTAIN",
            rollback_result={"status": rollback_status, "submitted": rollback_submitted, "verified": verified},
        )

    def _invoke_driver(self, plan: dict[str, Any]) -> dict[str, Any]:
        """Enforce the plan timeout without retrying or exposing exception text."""
        container: list[dict[str, Any]] = []

        def invoke() -> None:
            try:
                value = self.driver.execute(
                    platform=plan["platform"], target=plan["target"],
                    commands=deepcopy(plan["command_bundle"]["commands"]), timeout_seconds=plan["timeout_seconds"],
                    binding_id=plan["binding_id"],
                )
                container.append(value if isinstance(value, dict) else {"status": "UNKNOWN", "submitted": True})
            except Exception:
                container.append({"status": "UNCERTAIN", "submitted": True, "output": None})

        worker = threading.Thread(target=invoke, daemon=True, name=f"p10-{plan['plan_id']}")
        worker.start()
        worker.join(timeout=plan["timeout_seconds"])
        if worker.is_alive():
            self._manual_verification_hold.set()
            return {"status": "TIMEOUT", "submitted": True, "output": None}
        return container[0] if container else {"status": "UNCERTAIN", "submitted": True, "output": None}

    def prepare_rollback(self, plan_id: str) -> dict[str, Any]:
        """Return the pre-approved rollback contract; no second approval exists."""
        original = self._get_internal(plan_id)
        if not any(result.get("plan_id") == plan_id for result in self._results.values()):
            raise P10SafetyError("Rollback requires a completed or uncertain execution result.")
        if original["rollback_strategy"] == "NO_SAFE_ROLLBACK" or not original["rollback_bundle"]["commands"]:
            raise P10SafetyError("NO_SAFE_ROLLBACK")
        rollback_contract = {
            "original_plan_id": original["plan_id"], "rollback_hash": original["rollback_hash"],
            "approval_required": False, "post_checks": list(original["post_checks"]),
            "strategy": "PREAPPROVED_AUTOMATIC_ON_DECLARED_FAILURE",
        }
        self._validate_contract("p10-rollback-plan.schema.json", rollback_contract)
        return rollback_contract

    def get_plan(self, plan_id: str) -> dict[str, Any]:
        return self._public_plan(self._get_internal(plan_id))

    def get_result(self, execution_id: str) -> dict[str, Any]:
        if execution_id not in self._results:
            raise P10SafetyError("Execution result is unavailable in memory.")
        return deepcopy(self._results[execution_id])

    def _assert_prepared(self, plan: dict[str, Any]) -> None:
        self._assert_integrity(plan)
        self._assert_not_expired(plan)
        if plan["status"] != "PREPARED":
            raise P10SafetyError("Plan is not awaiting approval.")

    def _assert_not_expired(self, plan: dict[str, Any]) -> None:
        if self._now() >= self._parse_time(plan["expires_at"]):
            raise P10SafetyError("Prepared plan has expired.")

    def _integrity_hash(self, plan: dict[str, Any]) -> str:
        protected = {key: value for key, value in plan.items() if key != "integrity_hash"}
        return self._hash(protected)

    def _assert_integrity(self, plan: dict[str, Any]) -> None:
        if plan.get("integrity_hash") != self._integrity_hash(plan):
            raise P10SafetyError("Prepared target, command, rollback, identity, risk, or plan content changed.")

    def _get_internal(self, plan_id: str) -> dict[str, Any]:
        if not isinstance(plan_id, str) or plan_id not in self._plans:
            raise P10SafetyError("Prepared plan was not found in memory.")
        return deepcopy(self._plans[plan_id])

    def _public_plan(self, plan: dict[str, Any]) -> dict[str, Any]:
        public = deepcopy(plan)
        public.pop("identity_pin", None)
        public.pop("owner_session_digest", None)
        public.pop("integrity_hash", None)
        public["command_bundle"]["display_commands"] = [self._redact(item) for item in public["command_bundle"].get("display_commands", [])]
        public["rollback_bundle"]["display_commands"] = [self._redact(item) for item in public["rollback_bundle"].get("display_commands", [])]
        for bundle_name in ("command_bundle", "rollback_bundle"):
            public[bundle_name].pop("commands", None)
        return public

    def _redact(self, value: str) -> str:
        return self._SECRET.sub("[REDACTED]", value)[:8192]

    def _consume_and_result(self, plan: dict[str, Any], status: str, *, submitted: bool, driver_status: str | None) -> dict[str, Any]:
        with self._state_lock:
            approval = self._approvals[plan["plan_id"]]
            approval["used"] = True
            self._used_phrases.add(approval["phrase_fingerprint"])
        return self._result(plan, status, submitted=submitted, driver_status=driver_status)

    def _result(
        self, plan: dict[str, Any], status: str, *, submitted: bool,
        driver_status: str | None, post_checks: list[dict[str, Any]] | None = None,
        rollback_status: str | None = None, rollback_result: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        execution_id = f"p10-exec-{uuid.uuid4().hex[:16]}"
        result = {
            "execution_id": execution_id, "plan_id": plan["plan_id"], "operation_id": plan["operation_id"],
            "status": status, "success": status == "SUCCESS", "submitted": submitted, "driver_status": driver_status,
            "mutation_started": submitted, "automatic_retry": False,
            "post_check_results": deepcopy(post_checks or []), "manual_verification_required": status in {"MANUAL_VERIFICATION_REQUIRED", "UNCERTAIN"},
            "rollback_status": rollback_status or ("NOT_TRIGGERED" if plan["rollback_strategy"] != "NO_SAFE_ROLLBACK" else "NO_SAFE_ROLLBACK"),
            "rollback_result": deepcopy(rollback_result),
            "timestamp": self._iso(self._now()), "audit_mode": "IN_MEMORY_ONLY", "retention": "NONE",
            "output_persisted": False, "credentials_included": False, "notification_sent": False, "ticket_created": False,
            "page_sent": False, "automatic_assignment": False, "automatic_remediation": False,
        }
        with self._state_lock:
            self._results[execution_id] = deepcopy(result)
            stored = deepcopy(self._plans[plan["plan_id"]])
            stored["status"] = status
            stored["integrity_hash"] = self._integrity_hash(stored)
            self._plans[plan["plan_id"]] = stored
            self._audit("EXECUTION_RESULT", plan_id=plan["plan_id"], operation_id=plan["operation_id"], status=status)
        self._validate_contract("p10-execution-result.schema.json", result)
        return result

    def _audit(self, event: str, **fields: Any) -> None:
        self.audit_records.append({"event": event, "timestamp": self._iso(self._now()), **fields, "persisted": False})
