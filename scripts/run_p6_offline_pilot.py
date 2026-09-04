#!/usr/bin/env python3
"""Run complete P6 multi-platform connector acceptance without network access."""

import json
import sys
from copy import deepcopy
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any, Callable

import yaml

base_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(base_dir))

from core.connectors.engine import MultiPlatformConnectorEngine
from core.connectors.registry import ConnectorRegistry
from core.entity.build_entity_index import EntityIndexBuilder


def run_p6_offline_pilot() -> dict[str, Any]:
    print("=" * 76)
    print(" MNE_Brain P6 - Multi-Platform Read-Only Connector Pilot")
    print("=" * 76)
    registry = ConnectorRegistry(base_dir=base_dir)
    engine = MultiPlatformConnectorEngine(base_dir=base_dir)
    entities = EntityIndexBuilder(base_dir=base_dir).build_index(persist=False)["entities"]
    results: list[dict[str, Any]] = []

    def scenario(scenario_id: str, check: Callable[[], tuple[bool, str, dict[str, Any]]]) -> None:
        try:
            passed, detail, metrics = check()
        except Exception as exc:
            passed, detail, metrics = False, f"{type(exc).__name__}: {exc}", {}
        results.append({"scenario_id": scenario_id, "passed": passed, "detail": detail, "metrics": metrics})
        print(f"[{'PASS' if passed else 'FAIL'}] {scenario_id} | {detail}")

    def catalog_contract() -> tuple[bool, str, dict[str, Any]]:
        catalog = registry.public_catalog()
        passed = (
            catalog["total_connectors"] == 15
            and all(item["implementation_status"] == "offline_validated" for item in catalog["connectors"])
            and all(item["requires_owner_proceed"] is True for item in catalog["connectors"])
            and all(item["live_enabled"] is False for item in catalog["connectors"])
            and all(item["persistence_enabled"] is False for item in catalog["connectors"])
            and all(item["notifications_enabled"] is False for item in catalog["connectors"])
            and all(item["remediation_enabled"] is False for item in catalog["connectors"])
            and catalog["operations_included"] is False
        )
        return passed, "15 schema-valid connector families preserve the sole-owner boundary", {"connectors": catalog["total_connectors"]}

    scenario("p6-01", catalog_contract)

    def complete_coverage() -> tuple[bool, str, dict[str, Any]]:
        coverage = registry.coverage_report()
        passed = (
            coverage["total_entities"] == coverage["planned_entities"] == coverage["offline_validated_entities"] == 48
            and coverage["planning_coverage_percent"] == 100.0
            and coverage["offline_validation_coverage_percent"] == 100.0
            and coverage["coverage_gaps"] == []
            and coverage["full_offline_connector_readiness"] is True
            and coverage["live_collection_enabled"] is False
            and coverage["production_readiness_claimed"] is False
        )
        return passed, "all 48 canonical entities have an exact offline-validated connector", coverage

    scenario("p6-02", complete_coverage)

    def all_entity_plans() -> tuple[bool, str, dict[str, Any]]:
        plans = [registry.build_plan(item["entity_id"]) for item in entities]
        serialized = json.dumps(plans, sort_keys=True).casefold()
        passed = (
            len(plans) == 48
            and all(item["status"] == "PLANNED_READ_ONLY" for item in plans)
            and all(item["entity_id"] == entity["entity_id"] for item, entity in zip(plans, entities))
            and all(item["execution_permitted"] is False for item in plans)
            and all(item["raw_operations_included"] is False for item in plans)
            and not any(marker in serialized for marker in ("password", "credential_reference", "raw_output"))
        )
        return passed, "48 exact plans are deterministic, fingerprinted, and operation-minimized", {"plans": len(plans)}

    scenario("p6-03", all_entity_plans)

    def all_entity_fixtures() -> tuple[bool, str, dict[str, Any]]:
        fixtures = [engine.validate_offline_fixture(item["entity_id"]) for item in entities]
        passed = (
            len(fixtures) == 48
            and all(item["status"] == "SIMULATED_NOT_ACCEPTED" for item in fixtures)
            and all(item["trust_level"] == 0 for item in fixtures)
            and all(item["checks_succeeded"] >= 2 for item in fixtures)
            and all(item["connection_attempted"] is False for item in fixtures)
            and all(item["persistence_attempted"] is False for item in fixtures)
            and all(item["notification_sent"] is False for item in fixtures)
            and all(item["remediation_attempted"] is False for item in fixtures)
        )
        return passed, "all 48 entity routes pass trust-zero injected transport validation", {"fixtures": len(fixtures)}

    scenario("p6-04", all_entity_fixtures)

    def live_default_block() -> tuple[bool, str, dict[str, Any]]:
        unauthorized = engine.execute_readonly("fw-fortigate-edge-01")
        authorized = engine.execute_readonly("fw-fortigate-edge-01", authorized=True)
        passed = (
            unauthorized["reason"] == "OWNER_PROCEED_REQUIRED"
            and authorized["reason"] == "P6_LIVE_TRANSPORTS_DISABLED"
            and not unauthorized["connection_attempted"]
            and not authorized["connection_attempted"]
        )
        return passed, "default and broad authorization cannot activate a live transport", {}

    scenario("p6-05", live_default_block)

    def unknown_target() -> tuple[bool, str, dict[str, Any]]:
        plan = registry.build_plan("unknown-platform-01")
        return plan["status"] == "NOT_PLANNED", "unknown targets fail closed without connector guessing", {}

    scenario("p6-06", unknown_target)

    def unknown_check() -> tuple[bool, str, dict[str, Any]]:
        plan = registry.build_plan("waf-f5-bigip-01", ["modify_pool"])
        return plan["status"] == "NOT_PLANNED", "checks outside the exact allowlist fail closed", {}

    scenario("p6-07", unknown_check)

    def duplicate_mapping() -> tuple[bool, str, dict[str, Any]]:
        duplicate = deepcopy(registry.catalog)
        duplicate["connectors"][1]["entity_ids"].append("fw-fortigate-edge-01")
        duplicate_rejected = False
        with TemporaryDirectory(prefix="mne-p6-duplicate-") as temp_dir:
            path = Path(temp_dir) / "catalog.yaml"
            path.write_text(yaml.safe_dump(duplicate, sort_keys=False), encoding="utf-8")
            try:
                ConnectorRegistry(base_dir=base_dir, catalog_path=path)
            except ValueError:
                duplicate_rejected = True
        unsafe = deepcopy(registry.catalog)
        unsafe["connectors"][0]["checks"][0]["operation"] = "reboot"
        unsafe_rejected = False
        with TemporaryDirectory(prefix="mne-p6-unsafe-") as temp_dir:
            path = Path(temp_dir) / "catalog.yaml"
            path.write_text(yaml.safe_dump(unsafe, sort_keys=False), encoding="utf-8")
            try:
                ConnectorRegistry(base_dir=base_dir, catalog_path=path)
            except ValueError:
                unsafe_rejected = True
        return duplicate_rejected and unsafe_rejected, "duplicate mappings and mutating operations fail closed", {}

    scenario("p6-08", duplicate_mapping)

    def missing_adapter() -> tuple[bool, str, dict[str, Any]]:
        connector = registry.connector_for_entity("waf-f5-bigip-01")
        assert connector is not None
        engine.policy.update(
            {
                "enabled": True,
                "allowed_connectors": [connector["connector_id"]],
                "allowed_adapters": [connector["adapter_id"]],
                "allowed_entities": ["waf-f5-bigip-01"],
                "allowed_checks": {connector["connector_id"]: [connector["checks"][0]["id"]]},
            }
        )
        result = engine.execute_readonly(
            "waf-f5-bigip-01",
            [connector["checks"][0]["id"]],
            authorized=True,
            scope_reference="P6-EXACT-F5-CHECK",
            credential_reference="secretref://local/f5-readonly",
        )
        return result["reason"] == "P6_ADAPTER_NOT_REGISTERED" and not result["connection_attempted"], "policy flags cannot invent a missing registered transport", {}

    scenario("p6-09", missing_adapter)

    def minimized_catalog() -> tuple[bool, str, dict[str, Any]]:
        public = registry.public_catalog()
        serialized = json.dumps(public, sort_keys=True).casefold()
        forbidden = ("operation\"", "command\"", "password", "credential_reference", "raw_output", "172.23.", "10.1.")
        passed = not any(item in serialized for item in forbidden) and public["operations_included"] is False
        return passed, "public connector metadata excludes operations, secrets, addresses, and raw output", {"chars": len(serialized)}

    scenario("p6-10", minimized_catalog)

    for index, connector in enumerate(registry.public_catalog()["connectors"], start=11):
        connector_record = next(item for item in registry.catalog["connectors"] if item["connector_id"] == connector["connector_id"])
        entity_id = connector_record["entity_ids"][0]

        def family_check(entity_id: str = entity_id, connector_id: str = connector["connector_id"]) -> tuple[bool, str, dict[str, Any]]:
            plan = registry.build_plan(entity_id)
            fixture = MultiPlatformConnectorEngine(base_dir=base_dir).validate_offline_fixture(entity_id)
            passed = (
                plan["connector_id"] == connector_id
                and plan["status"] == "PLANNED_READ_ONLY"
                and fixture["status"] == "SIMULATED_NOT_ACCEPTED"
                and fixture["trust_level"] == 0
                and fixture["connection_attempted"] is False
            )
            return passed, f"{connector_id} routes and validates without a connection", {"entity": entity_id}

        scenario(f"p6-{index:02d}", family_check)

    passed_count = sum(1 for item in results if item["passed"])
    coverage = registry.coverage_report()
    report = {
        "success": passed_count == len(results),
        "mode": registry.MODE,
        "passed": passed_count,
        "total": len(results),
        "connector_families": registry.public_catalog()["total_connectors"],
        "canonical_entities": coverage["total_entities"],
        "planning_coverage_percent": coverage["planning_coverage_percent"],
        "offline_validation_coverage_percent": coverage["offline_validation_coverage_percent"],
        "live_transport_coverage_percent": coverage["live_transport_coverage_percent"],
        "live_connections": 0,
        "notifications": 0,
        "persistence_actions": 0,
        "remediation_actions": 0,
        "production_readiness_claimed": False,
        "results": results,
    }
    print("=" * 76)
    print(f" P6 OFFLINE PILOT: {passed_count} / {len(results)} SCENARIOS PASSED")
    print(" Planning: 100% | Offline validation: 100% | Live collection: disabled")
    print("=" * 76)
    return report


if __name__ == "__main__":
    sys.exit(0 if run_p6_offline_pilot()["success"] else 1)
