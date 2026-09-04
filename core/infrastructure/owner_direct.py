"""Owner Direct infrastructure operations with explicit, in-memory confirmation.

This module deliberately does not use the legacy P7 pin gate or the P10
template catalog.  It is the owner-only control plane for one exact asset and
one exact operation at a time.  Protocol adapters are registered objects; the
service never shells out and never handles or returns a credential value.
"""

from __future__ import annotations

import hashlib
import json
import re
import secrets
import threading
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Protocol

import yaml
import jsonschema

from core.entity.build_entity_index import EntityIndexBuilder
from core.transports.credentials import CredentialResolver


class OwnerDirectError(ValueError):
    """Raised for an unsafe or incomplete Owner Direct request."""


class OwnerDirectAdapter(Protocol):
    """Registered protocol adapter.  Implementations receive only a reference."""

    def read(self, request: dict[str, Any]) -> dict[str, Any]: ...
    def write(self, request: dict[str, Any]) -> dict[str, Any]: ...


class OwnerDirectService:
    MODE = "OWNER_DIRECT"
    READ_PROTOCOLS = {"ssh", "powershell", "winrm", "rest", "snmp", "https", "tcp"}
    _TARGET = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:-]{0,252}$")
    _SECRET_KEY = re.compile(r"(?i)(?:password|passwd|token|secret|authorization|api[_-]?key|private[_-]?key|community)")
    _INJECTION = re.compile(r"(?:[;&|`]|\$\(|<\(|>\(|\r|\n|\x00|\b(?:iex|invoke-expression|cmd\.exe|-encodedcommand|frombase64string)\b)", re.I)
    _READ_SSH = re.compile(
        r"^(?:show|get|display|hostnamectl|tmsh\s+-q\s+-c\s+'show|system\s+diagnostics|help|"
        r"diagnose|execute\s+ping|execute\s+traceroute|ping|traceroute|cat|ip|netstat|ss|uptime|uname|terminal)\b",
        re.I,
    )
    _READ_PS = re.compile(
        r"^(?:Get-[A-Za-z0-9*_-]+(?:\s+[A-Za-z0-9,*._:-]+)*|"
        r"Test-[A-Za-z0-9*_-]+(?:\s+[A-Za-z0-9,*._:-]+)*|"
        r"Resolve-DnsName(?:\s+[A-Za-z0-9,*._:-]+)*|"
        r"Select-Object(?:\s+[A-Za-z0-9,*._:-]+)*|"
        r"Format-[A-Za-z0-9*_-]+(?:\s+[A-Za-z0-9,*._:-]+)*|"
        r"repadmin\s+/replsummary|ping\s+[A-Za-z0-9.-]+|tracert\s+[A-Za-z0-9.-]+)$",
        re.I,
    )
    _CRITICAL_WRITE = re.compile(r"\b(?:reboot|reload|format|erase|delete|shutdown|drop|destroy)\b", re.I)
    _HIGH_WRITE = re.compile(r"\b(?:router|route|firewall|policy|acl|access-list|iptables|filter|rule)\b", re.I)
    _MEDIUM_WRITE = re.compile(r"\b(?:interface|vlan|port|service|restart|reload-config)\b", re.I)

    def __init__(self, base_dir: Path, *, adapters: dict[str, OwnerDirectAdapter] | None = None, now: Any = None):
        self.base_dir = Path(base_dir).resolve()
        self.credentials = CredentialResolver(self.base_dir)
        self.entities = {item["entity_id"]: item for item in EntityIndexBuilder(self.base_dir).build_index(persist=False)["entities"]}
        bindings = yaml.safe_load((self.base_dir / "config/p7_device_bindings.yaml").read_text(encoding="utf-8")) or {}
        self.bindings = [item for item in bindings.get("bindings", []) if item.get("scope_status") == "ACTIVE" and item.get("read_only") is True]
        self.adapters: dict[str, OwnerDirectAdapter] = dict(adapters or {})
        schema_dir = self.base_dir / "00_meta/schemas"
        self._warning_schema = json.loads((schema_dir / "owner-direct-risk-warning.schema.json").read_text(encoding="utf-8"))
        self._audit_schema = json.loads((schema_dir / "owner-direct-identity-audit.schema.json").read_text(encoding="utf-8"))
        self._now = now or (lambda: datetime.now(timezone.utc))
        self._plans: dict[str, dict[str, Any]] = {}
        self._lock = threading.RLock()

    @staticmethod
    def _canonical(value: Any) -> str:
        return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)

    @classmethod
    def _evidence_id(cls, value: Any) -> str:
        return "ev-owner-direct-" + hashlib.sha256(cls._canonical(value).encode("utf-8")).hexdigest()[:20]

    @staticmethod
    def _safe(value: Any) -> Any:
        """Drop secret-shaped data from adapter output before any state is retained."""
        if isinstance(value, dict):
            return {str(key): OwnerDirectService._safe(item) for key, item in value.items() if not OwnerDirectService._SECRET_KEY.search(str(key))}
        if isinstance(value, list):
            return [OwnerDirectService._safe(item) for item in value]
        if isinstance(value, str):
            return OwnerDirectService._SECRET_KEY.sub("[REDACTED]", value)[:8192]
        return value

    def register_adapter(self, protocol: str, adapter: OwnerDirectAdapter) -> None:
        if protocol not in self.READ_PROTOCOLS:
            raise OwnerDirectError("Protocol is not registered for Owner Direct.")
        self.adapters[protocol] = adapter

    def _entity(self, entity_id: str) -> dict[str, Any]:
        entity = self.entities.get(entity_id)
        if not entity:
            raise OwnerDirectError("Target is outside the canonical asset inventory.")
        return entity

    def _binding(self, entity_id: str, protocol: str) -> dict[str, Any] | None:
        matches = [item for item in self.bindings if item.get("entity_id") == entity_id and item.get("protocol") == protocol]
        return sorted(matches, key=lambda item: item["binding_id"])[0] if matches else None

    @classmethod
    def _target(cls, entity: dict[str, Any], binding: dict[str, Any] | None, target: str | None, owner_supplied_target: bool) -> tuple[str, bool]:
        canonical = str((binding or {}).get("target") or entity.get("verification_target") or entity.get("fqdn") or entity.get("hostname") or entity.get("ip") or "")
        requested = target or canonical
        if not isinstance(requested, str) or not cls._TARGET.fullmatch(requested):
            raise OwnerDirectError("One exact hostname, FQDN, or IP target is required.")
        is_new_target = bool(target and target != canonical)
        if is_new_target and not owner_supplied_target:
            raise OwnerDirectError("Target is outside the canonical asset inventory; owner-supplied target confirmation is required.")
        return requested, is_new_target

    def _credential_reference(self, binding: dict[str, Any] | None) -> str | None:
        ref_env = str((binding or {}).get("credential_ref_env") or "")
        if not ref_env:
            return None
        reference = self.credentials.value(ref_env)
        if not reference:
            raise OwnerDirectError("The registered credential reference is unavailable.")
        # The reference, not its value, is retained for the active adapter call.
        return ref_env

    @classmethod
    def _validate_read(cls, protocol: str, operation: str) -> None:
        if protocol not in cls.READ_PROTOCOLS or not isinstance(operation, str) or cls._INJECTION.search(operation):
            raise OwnerDirectError("Malformed read-only operation rejected.")
        if protocol == "rest" or protocol == "https":
            if not re.fullmatch(r"(?:GET|HEAD)\s+/[^\s?#]*", operation, re.I):
                raise OwnerDirectError("Owner Direct REST discovery permits one exact GET or HEAD path.")
        elif protocol == "snmp":
            if not re.fullmatch(r"SNMP_(?:GET|WALK)\s+[0-9.]+", operation, re.I):
                raise OwnerDirectError("Owner Direct SNMP discovery permits one exact GET or WALK OID.")
        elif protocol in {"powershell", "winrm"}:
            if not cls._READ_PS.fullmatch(operation):
                raise OwnerDirectError("Owner Direct PowerShell discovery permits read-only commands only.")
        elif protocol == "ssh" and not cls._READ_SSH.match(operation):
            raise OwnerDirectError("Owner Direct SSH discovery permits read-only commands only.")

    @classmethod
    def _validate_write_operation(cls, protocol: str, operations: list[str]) -> None:
        if protocol not in cls.READ_PROTOCOLS or not isinstance(operations, list) or not operations or len(operations) > 20:
            raise OwnerDirectError("One exact protocol and a bounded operation list are required.")
        for operation in operations:
            if not isinstance(operation, str) or not operation.strip() or len(operation) > 8192 or cls._INJECTION.search(operation):
                raise OwnerDirectError("Malformed command or command injection rejected.")
            if cls._SECRET_KEY.search(operation):
                raise OwnerDirectError("Secret-bearing commands are rejected.")

    @staticmethod
    def _identity(trusted: str | None, observed: Any) -> tuple[str, str | None]:
        observed_text = str(observed or "").strip() or None
        if trusted and observed_text and trusted != observed_text:
            return "IDENTITY_CONFLICT", observed_text
        if trusted and observed_text == trusted:
            return "IDENTITY_VERIFIED", observed_text
        return "IDENTITY_UNVERIFIED", observed_text

    def discover(self, *, entity_id: str, protocol: str, operation: str, target: str | None = None,
                 owner_supplied_target: bool = False, trusted_identity: str | None = None) -> dict[str, Any]:
        """Run exactly one registered read.  Missing pins are evidence, never a gate."""
        entity = self._entity(entity_id)
        binding = self._binding(entity_id, protocol)
        resolved_target, new_target = self._target(entity, binding, target, owner_supplied_target)
        self._validate_read(protocol, operation)
        adapter = self.adapters.get(protocol)
        if adapter is None:
            return {"status": "ADAPTER_NOT_REGISTERED", "entity_id": entity_id, "target": resolved_target, "protocol": protocol,
                    "operation": operation, "attempt_count": 0, "automatic_retry": False, "credentials_returned": False}
        request = {"mode": self.MODE, "entity_id": entity_id, "target": resolved_target, "protocol": protocol, "operation": operation,
                   "credential_reference": self._credential_reference(binding), "canonical_target": not new_target}
        try:
            raw = adapter.read(deepcopy(request))
        except Exception:
            raw = {"status": "TRANSPORT_FAILED", "reachable": False, "authenticated": False}
        result = self._safe(raw if isinstance(raw, dict) else {})
        identity_status, observed_identity = self._identity(trusted_identity, result.get("identity"))
        observed_at = self._now().isoformat()
        evidence_id = self._evidence_id({"entity_id": entity_id, "target": resolved_target, "operation": operation, "observed_at": observed_at, "identity": observed_identity})
        facts = result.get("facts") if isinstance(result.get("facts"), dict) else {}
        return {
            "status": "IDENTITY_CONFLICT" if identity_status == "IDENTITY_CONFLICT" else str(result.get("status", "UNKNOWN")),
            "entity_id": entity_id, "target_ip": entity.get("ip", ""), "hostname": entity.get("hostname", ""), "fqdn": entity.get("fqdn", ""),
            "platform": (binding or {}).get("platform", "UNKNOWN"), "role": entity.get("category", ""), "protocol": protocol, "check": operation,
            "reachability": bool(result.get("reachable", result.get("connection_attempted", False))), "authentication_result": str(result.get("authentication", result.get("status", "UNKNOWN"))),
            "identity_result": identity_status, "observed_identity": observed_identity, "serial": facts.get("serial"), "model": facts.get("model"), "version": facts.get("version"),
            "timestamp": observed_at, "evidence_id": evidence_id, "attempt_count": 1, "automatic_retry": False,
            "facts": facts, "credentials_returned": False, "canonical_documents_updated": False, "new_target_owner_supplied": new_target,
        }

    @classmethod
    def _classify_risk(cls, operations: list[str], explicit_level: str | None = None) -> str:
        if explicit_level in {"LOW", "MEDIUM", "HIGH", "CRITICAL"}:
            return explicit_level
        joined = " ".join(operations)
        if cls._CRITICAL_WRITE.search(joined):
            return "CRITICAL"
        if cls._HIGH_WRITE.search(joined):
            return "HIGH"
        if cls._MEDIUM_WRITE.search(joined):
            return "MEDIUM"
        return "LOW"

    def prepare_write(self, *, entity_id: str, protocol: str, operations: list[str], intended_change: str,
                      expected_impact: str, downtime_risk: str, blast_radius: str, prechecks: list[str], postchecks: list[str],
                      rollback_steps: list[str] | None = None, trusted_identity: str | None = None, observed_identity: str | None = None,
                      target: str | None = None, owner_supplied_target: bool = False, owner_requested: bool = False) -> dict[str, Any]:
        if owner_requested is not True:
            raise OwnerDirectError("Infrastructure writes must originate from an explicit owner request.")
        entity = self._entity(entity_id)
        binding = self._binding(entity_id, protocol)
        resolved_target, new_target = self._target(entity, binding, target, owner_supplied_target)
        self._validate_write_operation(protocol, operations)
        identity_status, observed = self._identity(trusted_identity, observed_identity)
        if identity_status == "IDENTITY_CONFLICT":
            raise OwnerDirectError("IDENTITY_CONFLICT: resolve the recorded identity mismatch before a write.")
        if not all(isinstance(item, str) and item.strip() for item in (prechecks + postchecks)):
            raise OwnerDirectError("Prechecks and postchecks must be explicit plain text.")
        plan_id = "odplan_" + secrets.token_urlsafe(18)
        rollback = list(rollback_steps or [])
        can_rollback = bool(rollback)
        rollback_status = "DECLARED" if can_rollback else "NO_SAFE_ROLLBACK"
        rollback_summary = (
            f"Automated rollback available ({len(rollback)} step(s) declared)."
            if can_rollback
            else "IRREVERSIBLE / NO SAFE ROLLBACK: This operation cannot be automatically reversed. Manual recovery required if reverted."
        )
        calculated_risk = self._classify_risk(operations)
        warning = {
            "target_device_system": f"{entity_id} ({resolved_target})", "exact_intended_change": intended_change,
            "commands_or_api_operations": list(operations), "expected_impact_and_downtime_risk": f"{expected_impact}; downtime risk: {downtime_risk}",
            "blast_radius": blast_radius, "prechecks": list(prechecks), "postchecks": list(postchecks),
            "rollback_steps": rollback or ["NO_SAFE_ROLLBACK"], "rollback_status": rollback_status,
            "can_rollback": can_rollback, "risk_level": calculated_risk, "rollback_summary": rollback_summary,
            "identity_status": identity_status, "identity_warning": "Identity is unverified; the owner may proceed only after reviewing this warning." if identity_status == "IDENTITY_UNVERIFIED" else "Identity matched the recorded value.",
        }
        jsonschema.Draft7Validator(self._warning_schema).validate(warning)
        plan = {"plan_id": plan_id, "mode": self.MODE, "entity_id": entity_id, "target": resolved_target, "protocol": protocol,
                "operations": list(operations), "binding_id": (binding or {}).get("binding_id"), "risk_level": calculated_risk,
                "can_rollback": can_rollback, "rollback_summary": rollback_summary, "warning": warning,
                "identity_status": identity_status, "observed_identity": observed, "owner_requested": True, "new_target_owner_supplied": new_target,
                "status": "AWAITING_FINAL_CONFIRMATION", "created_at": self._now().isoformat(), "confirmation_count": 0}
        with self._lock:
            self._plans[plan_id] = plan
        return deepcopy(plan)

    def confirm_write(self, plan_id: str, *, owner_session_digest: str) -> dict[str, Any]:
        """The single, final confirmation.  It sends the exact prepared operation once."""
        if not re.fullmatch(r"[0-9a-f]{64}", owner_session_digest or ""):
            raise OwnerDirectError("An authenticated owner session is required for final confirmation.")
        with self._lock:
            plan = self._plans.get(plan_id)
            if not plan or plan["status"] != "AWAITING_FINAL_CONFIRMATION" or plan["confirmation_count"]:
                raise OwnerDirectError("The Owner Direct plan is unavailable or was already confirmed.")
            plan["confirmation_count"] = 1
            plan["status"] = "EXECUTING"
            binding = self._binding(plan["entity_id"], plan["protocol"])
            public_request = {key: plan[key] for key in ("mode", "entity_id", "target", "protocol", "operations")}
            # Resolve the opaque reference only for this active adapter connection;
            # never retain it in a prepared plan or return it to the caller.
            public_request["credential_reference"] = self._credential_reference(binding)
        adapter = self.adapters.get(plan["protocol"])
        if adapter is None:
            final = {"status": "ADAPTER_NOT_REGISTERED", "submitted": False, "postcheck_status": "NOT_RUN", "automatic_retry": False}
        else:
            try:
                write_result = self._safe(adapter.write(deepcopy(public_request)))
            except Exception:
                write_result = {"status": "UNCERTAIN", "submitted": True}
            submitted = bool(write_result.get("submitted", write_result.get("status") in {"SUCCESS", "COMMITTED", "SUBMITTED"}))
            try:
                post = self._safe(adapter.read({**public_request, "operation": "POSTCHECK", "postcheck": True}))
            except Exception:
                post = {"status": "POSTCHECK_FAILED"}
            final = {"status": str(write_result.get("status", "UNKNOWN")), "submitted": submitted, "postcheck_status": str(post.get("status", "POSTCHECK_FAILED")),
                     "postcheck_evidence_id": self._evidence_id({"plan_id": plan_id, "post": post, "at": self._now().isoformat()}), "automatic_retry": False,
                     "rollback_status": plan["warning"]["rollback_status"], "can_rollback": plan.get("can_rollback", False)}
        with self._lock:
            plan["status"] = "COMPLETED" if final["status"] in {"SUCCESS", "COMMITTED", "SUBMITTED"} else final["status"]
        return {"plan_id": plan_id, "identity_status": plan["identity_status"], "credentials_returned": False, **final}

    def identity_audit(self, *, requests: list[dict[str, Any]]) -> dict[str, Any]:
        """One request per canonical asset; discovery never writes inventory or pins."""
        seen: set[str] = set(); rows: list[dict[str, Any]] = []
        for item in requests:
            entity_id = str(item.get("entity_id", ""))
            if entity_id in seen:
                raise OwnerDirectError("Identity audit permits one attempt per canonical asset.")
            seen.add(entity_id)
            rows.append(self.discover(**item))
        proposals = [{"entity_id": row["entity_id"], "proposed_identity": row.get("observed_identity"), "reason": row["identity_result"]}
                     for row in rows if row.get("observed_identity") and row["identity_result"] != "IDENTITY_VERIFIED"]
        audit = {"mode": self.MODE, "audit_status": "COMPLETE", "attempts": len(rows), "rows": rows, "proposed_correction_enrollment_batch": proposals,
                 "canonical_documents_updated": False, "pins_updated": False, "bindings_updated": False, "indexes_updated": False}
        jsonschema.Draft7Validator(self._audit_schema).validate(audit)
        return audit
