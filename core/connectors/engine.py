#!/usr/bin/env python3
"""Owner-gated P6 connector orchestration with trust-zero fixture validation."""

from pathlib import Path
from typing import Any

import yaml

from core.entity.build_entity_index import EntityIndexBuilder
from core.verification.readonly_adapter import ReadOnlyVerificationAdapter
from core.connectors.registry import ConnectorRegistry


class MultiPlatformConnectorEngine:
    """Route exact entities to injected adapters; default construction cannot connect."""

    def __init__(
        self,
        base_dir: Path | None = None,
        *,
        adapters: dict[str, ReadOnlyVerificationAdapter] | None = None,
    ):
        self.base_dir = base_dir or Path(__file__).resolve().parent.parent.parent
        self.registry = ConnectorRegistry(base_dir=self.base_dir)
        self.adapters = dict(adapters or {})
        policy_path = self.base_dir / "config" / "p6_connector_policy.yaml"
        self.policy = yaml.safe_load(policy_path.read_text(encoding="utf-8")) or {}

    def plan(self, entity_id: str, check_ids: list[str] | None = None) -> dict[str, Any]:
        return self.registry.build_plan(entity_id, check_ids)

    @staticmethod
    def _fixture_transport(request: dict[str, Any]) -> dict[str, Any]:
        return {
            "status": "SIMULATED_SUCCESS",
            "connection_attempted": False,
            "output": f"offline fixture for {request['entity_id']} check {request['check_id']}",
        }

    def validate_offline_fixture(
        self, entity_id: str, check_ids: list[str] | None = None
    ) -> dict[str, Any]:
        if self.policy.get("offline_fixture_validation_enabled") is not True:
            return self._not_run("OFFLINE_FIXTURE_VALIDATION_DISABLED", entity_id)
        connector = self.registry.connector_for_entity(entity_id)
        plan = self.registry.build_plan(entity_id, check_ids)
        if connector is None or plan["status"] != "PLANNED_READ_ONLY":
            return self._not_run("INVALID_CONNECTOR_SCOPE", entity_id)
        selected_ids = {item["check_id"] for item in plan["planned_checks"]}
        checks = [
            {"check_id": item["id"], "command": item["operation"]}
            for item in connector["checks"]
            if item["id"] in selected_ids
        ]
        adapter = ReadOnlyVerificationAdapter(
            connector["adapter_id"],
            self._fixture_transport,
            simulation_mode=True,
            base_dir=self.base_dir,
        )
        result = adapter.collect(
            profile_name=connector["connector_id"],
            platform=connector["platform"],
            entity_id=entity_id,
            target="offline.invalid",
            checks=checks,
            scope_reference=f"P6-FIXTURE-{entity_id}",
            credential_reference="secretref://offline/p6-fixture",
            timeout_seconds=connector["timeout_seconds"],
            max_output_bytes=connector["max_output_bytes"],
            freshness_ttl_seconds=900,
            activation_context={
                "policy_enabled": True,
                "authorization_granted": True,
                "activation_state": "OFFLINE_FIXTURE_ONLY",
                "adapter_id": connector["adapter_id"],
                "entity_id": entity_id,
                "scope_reference": f"P6-FIXTURE-{entity_id}",
            },
        )
        return {
            "status": result["status"],
            "entity_id": entity_id,
            "connector_id": connector["connector_id"],
            "adapter_id": connector["adapter_id"],
            "trust_level": result["trust_level"],
            "checks_attempted": result["checks_attempted"],
            "checks_succeeded": result["checks_succeeded"],
            "evidence_records": result["evidence_records"],
            "connection_attempted": result["connection_attempted"],
            "simulation_mode": True,
            "persistence_attempted": False,
            "notification_sent": False,
            "remediation_attempted": False,
        }

    def execute_readonly(
        self,
        entity_id: str,
        check_ids: list[str] | None = None,
        *,
        authorized: bool = False,
        scope_reference: str | None = None,
        credential_reference: str | None = None,
    ) -> dict[str, Any]:
        if not authorized:
            return self._not_run("OWNER_PROCEED_REQUIRED", entity_id)
        plan = self.registry.build_plan(entity_id, check_ids)
        if plan["status"] != "PLANNED_READ_ONLY":
            return self._not_run("INVALID_CONNECTOR_SCOPE", entity_id)
        if self.policy.get("enabled") is not True:
            blocked = self._not_run("P6_LIVE_TRANSPORTS_DISABLED", entity_id)
            blocked["planned_checks"] = plan["planned_checks"]
            return blocked
        connector = self.registry.connector_for_entity(entity_id)
        if connector is None:
            return self._not_run("INVALID_CONNECTOR_SCOPE", entity_id)
        allowed_checks = set(self.policy.get("allowed_checks", {}).get(connector["connector_id"], []))
        planned_ids = {item["check_id"] for item in plan["planned_checks"]}
        scope_allowed = (
            connector["connector_id"] in set(self.policy.get("allowed_connectors", []))
            and connector["adapter_id"] in set(self.policy.get("allowed_adapters", []))
            and entity_id in set(self.policy.get("allowed_entities", []))
            and planned_ids.issubset(allowed_checks)
            and bool(scope_reference)
            and bool(credential_reference)
        )
        if not scope_allowed:
            return self._not_run("P6_SCOPE_BLOCKED", entity_id)
        adapter = self.adapters.get(connector["adapter_id"])
        if adapter is None:
            return self._not_run("P6_ADAPTER_NOT_REGISTERED", entity_id)
        matches = EntityIndexBuilder(base_dir=self.base_dir).resolve_entity(entity_id)
        if len(matches) != 1 or not matches[0].get("ip"):
            return self._not_run("P6_TARGET_UNAVAILABLE", entity_id)
        checks = [
            {"check_id": item["id"], "command": item["operation"]}
            for item in connector["checks"]
            if item["id"] in planned_ids
        ]
        return adapter.collect(
            profile_name=connector["connector_id"],
            platform=connector["platform"],
            entity_id=entity_id,
            target=matches[0]["ip"],
            checks=checks,
            scope_reference=str(scope_reference),
            credential_reference=str(credential_reference),
            timeout_seconds=min(connector["timeout_seconds"], int(self.policy["timeout_seconds_maximum"])),
            max_output_bytes=min(connector["max_output_bytes"], int(self.policy["max_output_bytes_maximum"])),
            freshness_ttl_seconds=int(self.policy["freshness_ttl_seconds_maximum"]),
            activation_context={
                "policy_enabled": True,
                "authorization_granted": True,
                "activation_state": self.policy.get("activation_state"),
                "adapter_id": connector["adapter_id"],
                "entity_id": entity_id,
                "scope_reference": scope_reference,
                "p0_containment_reference": self.policy.get("p0_containment_reference"),
                "owner_reference": self.policy.get("owner_reference"),
                "owner_authorization": self.policy.get("owner_authorization"),
            },
        )

    @staticmethod
    def _not_run(reason: str, entity_id: str | None) -> dict[str, Any]:
        return {
            "status": "NOT_RUN",
            "reason": reason,
            "entity_id": entity_id,
            "trust_level": 0,
            "checks_attempted": 0,
            "checks_succeeded": 0,
            "evidence_records": [],
            "connection_attempted": False,
            "persistence_attempted": False,
            "notification_sent": False,
            "remediation_attempted": False,
        }
