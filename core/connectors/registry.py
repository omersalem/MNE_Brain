#!/usr/bin/env python3
"""Schema-governed connector catalog, exact entity routing, and coverage."""

import hashlib
import json
import re
from copy import deepcopy
from pathlib import Path
from typing import Any

import jsonschema
import yaml

from core.entity.build_entity_index import EntityIndexBuilder


class ConnectorRegistry:
    """Build redacted read-only plans without importing any transport library."""

    MODE = "OFFLINE_MULTI_PLATFORM_CONNECTOR_READINESS"
    OWNER_REFERENCE = "MNE-BRAIN-OWNER"
    _WRITE_TOKENS = re.compile(
        r"\b(?:set|configure|delete|remove|reboot|restart|clear|shutdown|format|write|copy|invoke)\b",
        re.IGNORECASE,
    )
    _ALLOWED_PREFIXES = {
        "ssh": ("show ", "get ", "uname ", "systemctl ", "ss "),
        "rest": ("GET ", "HEAD ", "TLS_CERTIFICATE_METADATA"),
        "powershell": ("Get-",),
        "winrm": ("Get-", "repadmin /replsummary"),
        "vmware": ("get_",),
        "snmp": ("SNMP_GET ", "SNMP_WALK "),
    }

    def __init__(
        self,
        base_dir: Path | None = None,
        *,
        catalog_path: Path | None = None,
        schema_path: Path | None = None,
    ):
        self.base_dir = base_dir or Path(__file__).resolve().parent.parent.parent
        self.catalog_path = catalog_path or self.base_dir / "config" / "p6_connector_catalog.yaml"
        self.schema_path = schema_path or self.base_dir / "00_meta" / "schemas" / "connector-catalog.schema.json"
        self.schema = json.loads(self.schema_path.read_text(encoding="utf-8"))
        catalog = yaml.safe_load(self.catalog_path.read_text(encoding="utf-8")) or {}
        if not isinstance(catalog, dict):
            raise ValueError("P6 connector catalog must be a mapping")
        jsonschema.validate(catalog, self.schema)
        self.catalog = catalog
        self._connectors: dict[str, dict[str, Any]] = {}
        self._entity_to_connector: dict[str, str] = {}
        self._validate_catalog()

    @staticmethod
    def _fingerprint(value: str) -> str:
        return hashlib.sha256(value.encode("utf-8")).hexdigest()

    def _validate_catalog(self) -> None:
        canonical_ids = {
            item["entity_id"]
            for item in EntityIndexBuilder(base_dir=self.base_dir).build_index(persist=False)["entities"]
        }
        for connector in self.catalog["connectors"]:
            connector_id = connector["connector_id"]
            if connector_id in self._connectors:
                raise ValueError(f"Duplicate connector ID: {connector_id}")
            check_ids = [check["id"] for check in connector["checks"]]
            if len(check_ids) != len(set(check_ids)):
                raise ValueError(f"Duplicate check ID in {connector_id}")
            for check in connector["checks"]:
                self._validate_operation(connector["protocol"], check["operation"], connector_id)
            for entity_id in connector["entity_ids"]:
                if entity_id not in canonical_ids:
                    raise ValueError(f"Unknown canonical entity in P6 catalog: {entity_id}")
                if entity_id in self._entity_to_connector:
                    raise ValueError(f"Entity mapped to multiple P6 connectors: {entity_id}")
                self._entity_to_connector[entity_id] = connector_id
            self._connectors[connector_id] = connector

    @classmethod
    def _validate_operation(cls, protocol: str, operation: str, connector_id: str) -> None:
        if any(character in operation for character in ("\r", "\n", "\x00")):
            raise ValueError(f"Control characters are forbidden in {connector_id}")
        if cls._WRITE_TOKENS.search(operation):
            raise ValueError(f"Mutating operation is forbidden in {connector_id}")
        prefixes = cls._ALLOWED_PREFIXES.get(protocol, ())
        if not any(operation.startswith(prefix) for prefix in prefixes):
            raise ValueError(f"Operation is outside the {protocol} read-only grammar in {connector_id}")

    def connector_for_entity(self, entity_id: str) -> dict[str, Any] | None:
        connector_id = self._entity_to_connector.get(entity_id)
        connector = self._connectors.get(connector_id or "")
        return deepcopy(connector) if connector else None

    def build_plan(self, entity_id: Any, check_ids: list[str] | None = None) -> dict[str, Any]:
        if not isinstance(entity_id, str) or not entity_id:
            return self._not_planned("An exact canonical entity ID is required.")
        connector = self.connector_for_entity(entity_id)
        if connector is None:
            return self._not_planned("No governed P6 connector maps to the exact entity.", entity_id)
        requested = set(check_ids or [item["id"] for item in connector["checks"]])
        declared = {item["id"] for item in connector["checks"]}
        if not requested or not requested.issubset(declared):
            return self._not_planned("One or more checks are outside the connector allowlist.", entity_id)
        checks = [item for item in connector["checks"] if item["id"] in requested]
        return {
            "status": "PLANNED_READ_ONLY",
            "mode": self.MODE,
            "owner_reference": self.OWNER_REFERENCE,
            "entity_id": entity_id,
            "connector_id": connector["connector_id"],
            "platform": connector["platform"],
            "protocol": connector["protocol"],
            "adapter_id": connector["adapter_id"],
            "implementation_status": connector["implementation_status"],
            "live_transport_status": connector["live_transport_status"],
            "planned_checks": [
                {
                    "check_id": item["id"],
                    "evidence_objective": item["evidence_objective"],
                    "operation_fingerprint": self._fingerprint(item["operation"]),
                }
                for item in checks
            ],
            "timeout_seconds": connector["timeout_seconds"],
            "max_output_bytes": connector["max_output_bytes"],
            "requires_exact_target": True,
            "requires_owner_proceed": True,
            "execution_permitted": False,
            "live_connection_attempted": False,
            "persistence_attempted": False,
            "notification_sent": False,
            "remediation_attempted": False,
            "raw_operations_included": False,
        }

    def _not_planned(self, reason: str, entity_id: str | None = None) -> dict[str, Any]:
        return {
            "status": "NOT_PLANNED",
            "mode": self.MODE,
            "owner_reference": self.OWNER_REFERENCE,
            "entity_id": entity_id,
            "planned_checks": [],
            "execution_permitted": False,
            "live_connection_attempted": False,
            "persistence_attempted": False,
            "notification_sent": False,
            "remediation_attempted": False,
            "raw_operations_included": False,
            "reason": reason,
        }

    def public_catalog(self) -> dict[str, Any]:
        connectors = []
        for connector in sorted(self._connectors.values(), key=lambda item: item["connector_id"]):
            connectors.append(
                {
                    "connector_id": connector["connector_id"],
                    "title": connector["title"],
                    "platform": connector["platform"],
                    "protocol": connector["protocol"],
                    "adapter_id": connector["adapter_id"],
                    "implementation_status": connector["implementation_status"],
                    "live_transport_status": connector["live_transport_status"],
                    "entity_count": len(connector["entity_ids"]),
                    "check_ids": [item["id"] for item in connector["checks"]],
                    "review_sources": connector["review_sources"],
                    "requires_owner_proceed": True,
                    "live_enabled": False,
                    "persistence_enabled": False,
                    "notifications_enabled": False,
                    "remediation_enabled": False,
                }
            )
        return {
            "mode": self.MODE,
            "owner_reference": self.OWNER_REFERENCE,
            "total_connectors": len(connectors),
            "connectors": connectors,
            "operations_included": False,
            "persistence_attempted": False,
        }

    def coverage_report(self) -> dict[str, Any]:
        entities = EntityIndexBuilder(base_dir=self.base_dir).build_index(persist=False)["entities"]
        entity_ids = {item["entity_id"] for item in entities}
        covered = sorted(entity_ids.intersection(self._entity_to_connector))
        gaps = sorted(entity_ids.difference(self._entity_to_connector))
        live_transport_entities = sorted(
            entity_id
            for entity_id, connector_id in self._entity_to_connector.items()
            if self._connectors[connector_id]["live_transport_status"] == "OWNER_GATED_AVAILABLE"
        )
        total = len(entity_ids)
        return {
            "mode": self.MODE,
            "owner_reference": self.OWNER_REFERENCE,
            "total_entities": total,
            "planned_entities": len(covered),
            "planning_coverage_percent": round(len(covered) / total * 100, 2) if total else 0.0,
            "offline_validated_entities": len(covered),
            "offline_validation_coverage_percent": round(len(covered) / total * 100, 2) if total else 0.0,
            "coverage_gaps": gaps,
            "live_transport_entities": len(live_transport_entities),
            "live_transport_coverage_percent": round(len(live_transport_entities) / total * 100, 2) if total else 0.0,
            "full_offline_connector_readiness": bool(total) and not gaps,
            "live_collection_enabled": False,
            "production_readiness_claimed": False,
            "persistence_attempted": False,
        }
