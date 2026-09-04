"""Complete, secret-free infrastructure coverage for OWNER_FULL_CONTROL."""

from __future__ import annotations

import json
import re
from collections import Counter
from copy import deepcopy
from pathlib import Path
from typing import Any

import jsonschema
import yaml

from core.entity.build_entity_index import EntityIndexBuilder
from core.transports.credentials import CredentialResolver


COVERAGE_STATUSES = {
    "READY",
    "IDENTITY_CONFLICT",
    "CREDENTIAL_REFERENCE_MISSING",
    "IDENTITY_PIN_MISSING",
    "TRANSPORT_UNSUPPORTED",
    "OWNER_EXCLUDED",
}
READ_STATUSES = {
    "DOCUMENTED", "REACHABLE", "AUTHENTICATED", "LIVE_VERIFIED",
    "CONFLICT", "FAILED", "NOT_RUN",
}


class InfrastructureCoverageService:
    """Resolve every canonical entity without attempting a connection."""

    _HOSTKEY = re.compile(r"^ssh-[A-Za-z0-9-]+\s+\d+\s+SHA256:[A-Za-z0-9+/=]+$")
    _SHA256 = re.compile(r"^[A-Fa-f0-9]{64}$")

    def __init__(self, base_dir: Path):
        self.base_dir = Path(base_dir).resolve()
        self.credentials = CredentialResolver(self.base_dir)
        self.entities = EntityIndexBuilder(self.base_dir).build_index(persist=False).get("entities", [])
        self.bindings = (self._yaml("config/p7_device_bindings.yaml")).get("bindings", [])
        p8 = self._yaml("config/p8_diagnostic_catalog.yaml")
        self.reconciliations = {item["binding_id"]: item for item in p8.get("reconciliations", [])}
        transport = self._yaml("config/p7_transport_catalog.yaml")
        self.target_conflicts = {
            item["entity_id"]: item for item in transport.get("target_reconciliations", [])
            if item.get("disposition") == "CONFLICT_REQUIRES_IDENTITY_PROOF"
        }
        self.drivers = {item["protocol"]: item for item in transport.get("drivers", [])}
        connector_catalog = self._yaml("config/p6_connector_catalog.yaml")
        self.connectors: dict[str, dict[str, Any]] = {}
        for connector in connector_catalog.get("connectors", []):
            for entity_id in connector.get("entity_ids", []):
                self.connectors[entity_id] = connector
        self._schema = json.loads((self.base_dir / "00_meta/schemas/owner-full-control-coverage.schema.json").read_text(encoding="utf-8"))

    def _yaml(self, relative: str) -> dict[str, Any]:
        return yaml.safe_load((self.base_dir / relative).read_text(encoding="utf-8")) or {}

    def bindings_for_entity(self, entity_id: str) -> list[dict[str, Any]]:
        matches = []
        for binding in self.bindings:
            reconciliation = self.reconciliations.get(binding["binding_id"], {})
            if binding.get("entity_id") == entity_id or reconciliation.get("canonical_entity_id") == entity_id:
                matches.append(deepcopy(binding))
        return sorted(matches, key=lambda item: (item.get("scope_status") != "ACTIVE", item["binding_id"]))

    def exact_target(self, binding: dict[str, Any], entity: dict[str, Any]) -> tuple[str, str, bool]:
        """Return target, source label, and whether local config disagrees."""
        if binding.get("identity_mode") == "KERBEROS_FQDN":
            return str(binding.get("kerberos_fqdn", "")), "KERBEROS_FQDN", False
        prefix = str(binding.get("env_prefix", ""))
        configured = self.credentials.value(f"{prefix}_HOST") if prefix else ""
        expected = str(binding.get("target") or entity.get("ip") or entity.get("fqdn") or entity.get("hostname") or "")
        return configured or expected, "LOCAL_REFERENCE" if configured else "CANONICAL_BINDING", bool(configured and expected and configured.casefold() != expected.casefold())

    def _identity_status(self, binding: dict[str, Any]) -> tuple[str, str]:
        prefix = str(binding.get("env_prefix", ""))
        mode = binding.get("identity_mode")
        if mode == "KERBEROS_FQDN":
            target = str(binding.get("kerberos_fqdn", ""))
            return ("CONFIGURED" if target and "." in target else "MISSING"), "KERBEROS_FQDN"
        if mode == "PINNED_TLS_CERT":
            ref = f"{prefix}_TLS_CERT_SHA256"
            return self.credentials.status(ref, kind="sha256"), ref
        if mode == "PINNED_HOST_KEY":
            ref = f"{prefix}_SSH_HOSTKEY"
            return self.credentials.status(ref, kind="ssh_hostkey"), ref
        if mode == "SNMP_ENGINE_ID":
            ref = f"{prefix}_SNMP_ENGINE_ID"
            status = "CONFIGURED" if self.credentials.value(ref) or self.credentials.value("SNMPV3_ENGINE_ID") else "MISSING"
            return status, ref
        return "INVALID", "UNSUPPORTED_IDENTITY_MODE"

    def _credential_status(self, binding: dict[str, Any], connector: dict[str, Any]) -> tuple[str, str]:
        prefix = str(binding.get("credential_env_prefix") or binding.get("env_prefix", ""))
        reference = str(binding.get("credential_ref_env") or connector.get("credential_ref_env") or f"{prefix}_CREDENTIAL_REF")
        if binding.get("protocol") != "snmp":
            username = bool(self.credentials.value(f"{prefix}_USERNAME"))
            password = bool(self.credentials.value(f"{prefix}_PASSWORD"))
            if username and password:
                return "CONFIGURED", reference
            if username != password:
                return "INVALID", reference
            return "MISSING", reference
        opaque = self.credentials.status(reference, kind="opaque")
        if opaque == "CONFIGURED":
            return "CONFIGURED", reference
        if opaque == "INVALID":
            return "INVALID", reference
        return "MISSING", reference

    def _binding_view(self, entity: dict[str, Any], binding: dict[str, Any], connector: dict[str, Any]) -> dict[str, Any]:
        target, source, mismatch = self.exact_target(binding, entity)
        identity_status, identity_ref = self._identity_status(binding)
        credential_status, credential_ref = self._credential_status(binding, connector)
        driver = self.drivers.get(str(binding.get("protocol")), {})
        blockers = []
        if binding.get("scope_status") == "OWNER_EXCLUDED": blockers.append("OWNER_EXCLUDED")
        if not target: blockers.append("EXACT_TARGET_MISSING")
        if mismatch: blockers.append("CONFIGURED_TARGET_CONFLICT")
        if identity_status != "CONFIGURED": blockers.append("IDENTITY_PIN_MISSING" if identity_status == "MISSING" else "IDENTITY_PIN_INVALID")
        if credential_status != "CONFIGURED": blockers.append("CREDENTIAL_REFERENCE_MISSING" if credential_status == "MISSING" else "CREDENTIAL_REFERENCE_INVALID")
        if driver.get("implementation") not in {"IMPLEMENTED", "DEPENDENCY_GATED"}: blockers.append("TRANSPORT_UNSUPPORTED")
        return {
            "binding_id": binding["binding_id"], "protocol": binding["protocol"],
            "check_id": binding["check_id"], "target": target or "NOT_CONFIGURED",
            "target_source": source, "identity_mode": binding["identity_mode"],
            "identity_reference": identity_ref, "identity_status": identity_status,
            "credential_reference": credential_ref, "credential_status": credential_status,
            "scope_status": binding["scope_status"], "blockers": blockers,
        }

    def _entity_row(self, entity: dict[str, Any]) -> dict[str, Any]:
        entity_id = entity["entity_id"]
        connector = self.connectors.get(entity_id, {})
        bindings = [self._binding_view(entity, item, connector) for item in self.bindings_for_entity(entity_id)]
        conflict = self.target_conflicts.get(entity_id)
        if any(item["scope_status"] == "OWNER_EXCLUDED" for item in bindings) and not any(item["scope_status"] == "ACTIVE" for item in bindings):
            status = "OWNER_EXCLUDED"
        elif conflict or any("CONFIGURED_TARGET_CONFLICT" in item["blockers"] for item in bindings):
            status = "IDENTITY_CONFLICT"
        elif not bindings:
            status = "TRANSPORT_UNSUPPORTED"
        elif not any(item["identity_status"] == "CONFIGURED" for item in bindings):
            status = "IDENTITY_PIN_MISSING"
        elif not any(item["credential_status"] == "CONFIGURED" for item in bindings):
            status = "CREDENTIAL_REFERENCE_MISSING"
        else:
            status = "READY"
        return {
            "entity_id": entity_id, "name": entity.get("name", entity_id),
            "platform": connector.get("platform", "unmapped"), "role": entity.get("category", "unknown"),
            "documented_management_ip": entity.get("ip", ""), "documented_hostname": entity.get("hostname", ""),
            "documented_fqdn": entity.get("fqdn", ""), "status": status,
            "binding_ids": [item["binding_id"] for item in bindings], "bindings": bindings,
            "read_status": "CONFLICT" if status == "IDENTITY_CONFLICT" else "DOCUMENTED",
            "blocker": (
                "Conflicting documented target requires owner-reviewed authenticated identity proof."
                if status == "IDENTITY_CONFLICT" else
                "No exact registered governed binding exists for this canonical asset."
                if not bindings else
                "; ".join(sorted({blocker for item in bindings for blocker in item["blockers"]}))
            ),
        }

    def status(self) -> dict[str, Any]:
        rows = [self._entity_row(item) for item in sorted(self.entities, key=lambda item: item["entity_id"])]
        counts = Counter(item["status"] for item in rows)
        credential_counts = Counter(
            item["credential_status"] for row in rows for item in row["bindings"]
        )
        conflicts = [
            {
                "entity_id": row["entity_id"],
                "canonical_target": (self.target_conflicts.get(row["entity_id"]) or {}).get("canonical_target", row["documented_management_ip"]),
                "operational_target": (self.target_conflicts.get(row["entity_id"]) or {}).get("documented_target", "CONFIGURED_TARGET_DIFFERS"),
                "disposition": "IDENTITY_PROOF_REQUIRED",
            }
            for row in rows if row["status"] == "IDENTITY_CONFLICT"
        ]
        result = {
            "mode": "OWNER_FULL_CONTROL", "loopback_only": True,
            "automatic_safe_reads": True, "writes_require_one_exact_approval": True,
            "total_entities": len(rows), "coverage_counts": {status: counts.get(status, 0) for status in sorted(COVERAGE_STATUSES)},
            "credential_readiness_counts": {status: credential_counts.get(status, 0) for status in ("CONFIGURED", "MISSING", "INVALID", "AUTHENTICATION_FAILED")},
            "read_status_values": sorted(READ_STATUSES), "entities": rows, "identity_conflicts": conflicts,
            "engine_capabilities": {
                "codex": ["AUTOMATIC_GOVERNED_READS", "EXACT_CHANGE_PREPARATION", "ONE_APPROVAL_EXECUTION"],
                "opencode": ["AUTOMATIC_GOVERNED_READS", "EXACT_CHANGE_PREPARATION", "ONE_APPROVAL_EXECUTION"],
                "parity": True,
            },
            "secrets_returned": False, "connection_attempted": False,
        }
        jsonschema.Draft7Validator(self._schema).validate(result)
        return result
