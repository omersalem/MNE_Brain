"""Schema-governed P7 transport and target reconciliation registry."""

import json
import re
from copy import deepcopy
from pathlib import Path
from typing import Any

import jsonschema
import yaml

from core.connectors.registry import ConnectorRegistry
from core.entity.build_entity_index import EntityIndexBuilder


class TransportRegistry:
    MODE = "OWNER_GATED_LIVE_TRANSPORT_READINESS"
    _WRITE_TOKENS = re.compile(r"\b(?:set|configure|delete|remove|reboot|restart|clear|shutdown|format|write|copy)\b", re.IGNORECASE)

    def __init__(self, base_dir: Path | None = None):
        self.base_dir = base_dir or Path(__file__).resolve().parent.parent.parent
        schema = json.loads((self.base_dir / "00_meta/schemas/p7-transport-catalog.schema.json").read_text(encoding="utf-8"))
        catalog = yaml.safe_load((self.base_dir / "config/p7_transport_catalog.yaml").read_text(encoding="utf-8")) or {}
        jsonschema.validate(catalog, schema, format_checker=jsonschema.FormatChecker())
        self.catalog = catalog
        binding_schema = json.loads((self.base_dir / "00_meta/schemas/p7-device-bindings.schema.json").read_text(encoding="utf-8"))
        binding_catalog = yaml.safe_load((self.base_dir / "config/p7_device_bindings.yaml").read_text(encoding="utf-8")) or {}
        jsonschema.validate(binding_catalog, binding_schema)
        self.binding_catalog = binding_catalog
        entities = EntityIndexBuilder(base_dir=self.base_dir).build_index(persist=False)["entities"]
        self.entities = {item["entity_id"]: item for item in entities}
        self.connectors = ConnectorRegistry(base_dir=self.base_dir)
        self.reconciliations = {item["entity_id"]: item for item in catalog["target_reconciliations"]}
        unknown = set(self.reconciliations).difference(self.entities)
        if unknown:
            raise ValueError(f"Unknown P7 reconciliation entities: {sorted(unknown)}")
        self._validate_bindings()

    def _validate_bindings(self) -> None:
        ids: set[str] = set()
        for binding in self.binding_catalog["bindings"]:
            if binding["binding_id"] in ids:
                raise ValueError("P7 binding IDs must be unique.")
            ids.add(binding["binding_id"])
            operation = binding["operation"]
            if any(character in operation for character in ("\r", "\n", "\x00")) or self._WRITE_TOKENS.search(operation):
                raise ValueError(f"Mutating or malformed P7 operation: {binding['binding_id']}")
            if binding["protocol"] in ("winrm", "powershell") and not binding.get("kerberos_fqdn"):
                raise ValueError(f"PowerShell remoting requires an exact Kerberos FQDN: {binding['binding_id']}")
            if binding["protocol"] in ("winrm", "powershell") and binding["identity_mode"] != "KERBEROS_FQDN":
                raise ValueError(f"PowerShell remoting requires Kerberos identity: {binding['binding_id']}")
            if binding["protocol"] == "ssh" and binding.get("kerberos_fqdn"):
                raise ValueError(f"SSH binding cannot declare a Kerberos FQDN: {binding['binding_id']}")
            if binding["protocol"] == "ssh" and binding["identity_mode"] != "PINNED_HOST_KEY":
                raise ValueError(f"SSH binding requires a pinned host key: {binding['binding_id']}")
            if binding["protocol"] == "rest" and (binding["identity_mode"] != "PINNED_TLS_CERT" or not operation.startswith(("GET ", "HEAD "))):
                raise ValueError(f"REST binding requires pinned TLS and a GET/HEAD operation: {binding['binding_id']}")
            if binding["protocol"] == "ssh" and not operation.startswith(("get ", "show ", "hostnamectl ", "tmsh ", "system diagnostics ", "help")):
                raise ValueError(f"SSH binding is outside the read-only grammar: {binding['binding_id']}")
            if binding["protocol"] == "snmp" and (
                binding["identity_mode"] != "SNMP_ENGINE_ID"
                or not re.fullmatch(r"SNMP_(?:GET|WALK) [0-9.]+", operation)
            ):
                raise ValueError(f"SNMP binding requires an exact read-only OID and engine identity: {binding['binding_id']}")
            if binding["protocol"] == "tcp" and binding["identity_mode"] != "EXACT_TARGET_ONLY":
                raise ValueError(f"TCP dependency checks require an exact target: {binding['binding_id']}")

    def binding_summary(self) -> dict[str, Any]:
        bindings = self.binding_catalog["bindings"]
        active = [item for item in bindings if item["scope_status"] == "ACTIVE"]
        excluded = [item for item in bindings if item["scope_status"] == "OWNER_EXCLUDED"]
        protocols: dict[str, int] = {}
        for item in active:
            protocols[item["protocol"]] = protocols.get(item["protocol"], 0) + 1
        return {
            "total_bindings": len(bindings),
            "active_bindings": len(active),
            "owner_excluded_bindings": len(excluded),
            "protocol_counts": protocols,
            "identity_pinned_bindings": sum(item["identity_mode"] in ("PINNED_HOST_KEY", "PINNED_TLS_CERT") for item in active),
            "host_key_pinned_bindings": sum(item["identity_mode"] == "PINNED_HOST_KEY" for item in active),
            "tls_pinned_bindings": sum(item["identity_mode"] == "PINNED_TLS_CERT" for item in active),
            "kerberos_bindings": sum(item["identity_mode"] == "KERBEROS_FQDN" for item in active),
            "permanent_mapping_complete": len(active) >= 32 and len(excluded) == 1,
            "operations_included": False,
            "environment_references_included": False,
        }

    def target_plan(self, entity_id: str) -> dict[str, Any]:
        entity = self.entities.get(entity_id)
        connector = self.connectors.connector_for_entity(entity_id)
        if not entity or not connector:
            return {"status": "NOT_PLANNED", "entity_id": entity_id, "reason": "Exact canonical entity is unavailable."}
        canonical = entity.get("ip")
        reconciliation = self.reconciliations.get(entity_id)
        candidate = reconciliation["documented_target"] if reconciliation else canonical
        disposition = reconciliation["disposition"] if reconciliation else "MATCH"
        identity_required = disposition != "MATCH"
        return {
            "status": "PLANNED_READ_ONLY",
            "entity_id": entity_id,
            "connector_id": connector["connector_id"],
            "protocol": connector["protocol"],
            "canonical_target": canonical,
            "candidate_target": candidate,
            "target_disposition": disposition,
            "identity_proof_required": identity_required,
            "live_evidence_permitted": not identity_required,
            "requires_owner_proceed": True,
            "default_enabled": False,
            "persistence_enabled": False,
            "remediation_enabled": False,
        }

    def public_status(self) -> dict[str, Any]:
        plans = [self.target_plan(entity_id) for entity_id in sorted(self.entities)]
        conflicts = [item for item in plans if item.get("identity_proof_required")]
        return {
            "mode": self.MODE,
            "approval_state": "OWNER_CONTROLLED",
            "owner_reference": "MNE-BRAIN-OWNER",
            "audit_mode": "IN_MEMORY_ONLY",
            "retention": "NONE",
            "total_entities": len(plans),
            "transport_implementation_coverage": len(plans),
            "transport_implementation_coverage_percent": round(len(plans) / len(self.entities) * 100, 2),
            "identity_conflicts": len(conflicts),
            "credential_bindings": self.binding_summary(),
            "drivers": deepcopy(self.catalog["drivers"]),
            "live_enabled": False,
            "notifications_enabled": False,
            "ticketing_enabled": False,
            "paging_enabled": False,
            "automatic_assignment_enabled": False,
            "persistence_enabled": False,
            "remediation_enabled": False,
        }
