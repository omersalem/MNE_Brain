#!/usr/bin/env python3
"""Offline acceptance for P6 multi-platform connector readiness."""

import json
import sys
from pathlib import Path

import yaml

base_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(base_dir))

from core.connectors.engine import MultiPlatformConnectorEngine
from core.connectors.registry import ConnectorRegistry
from core.entity.build_entity_index import EntityIndexBuilder
from scripts.run_p6_offline_pilot import run_p6_offline_pilot


def test_p6_phase() -> bool:
    print("[VALIDATING P6 MULTI-PLATFORM CONNECTORS]")
    errors: list[str] = []
    passed = 0

    policy = yaml.safe_load((base_dir / "config" / "p6_connector_policy.yaml").read_text(encoding="utf-8"))
    if (
        policy["mode"] == "OFFLINE_MULTI_PLATFORM_CONNECTOR_READINESS"
        and policy["owner_reference"] == "MNE-BRAIN-OWNER"
        and policy["enabled"] is False
        and policy["offline_fixture_validation_enabled"] is True
        and policy["automatic_activation_enabled"] is False
        and policy["persistence_enabled"] is False
        and policy["notifications_enabled"] is False
        and policy["ticketing_enabled"] is False
        and policy["paging_enabled"] is False
        and policy["automatic_assignment_enabled"] is False
        and policy["remediation_enabled"] is False
        and policy["production_readiness_claimed"] is False
    ):
        print(" [PASS] P6 policy preserves sole-owner, disabled-live, and zero-side-effect controls")
        passed += 1
    else:
        errors.append("P6 policy boundary is incomplete or unsafe")

    registry = ConnectorRegistry(base_dir=base_dir)
    public = registry.public_catalog()
    coverage = registry.coverage_report()
    if (
        public["total_connectors"] == 15
        and coverage["total_entities"] == coverage["planned_entities"] == coverage["offline_validated_entities"] == 48
        and coverage["planning_coverage_percent"] == coverage["offline_validation_coverage_percent"] == 100.0
        and coverage["coverage_gaps"] == []
        and coverage["live_transport_entities"] == 1
        and coverage["live_transport_coverage_percent"] == 2.08
        and coverage["live_collection_enabled"] is False
        and coverage["production_readiness_claimed"] is False
    ):
        print(" [PASS] Fifteen connector families cover all 48 entities without inflating live readiness")
        passed += 1
    else:
        errors.append(f"P6 coverage truthfulness failed: {coverage}")

    entities = EntityIndexBuilder(base_dir=base_dir).build_index(persist=False)["entities"]
    plans = [registry.build_plan(item["entity_id"]) for item in entities]
    if (
        len(plans) == 48
        and all(item["status"] == "PLANNED_READ_ONLY" for item in plans)
        and all(item["raw_operations_included"] is False for item in plans)
        and all(item["execution_permitted"] is False for item in plans)
        and all(not item["live_connection_attempted"] for item in plans)
    ):
        print(" [PASS] Every canonical entity receives an exact minimized non-executing plan")
        passed += 1
    else:
        errors.append("P6 exact plan generation failed")

    engine = MultiPlatformConnectorEngine(base_dir=base_dir)
    fixtures = [engine.validate_offline_fixture(item["entity_id"]) for item in entities]
    if (
        len(fixtures) == 48
        and all(item["status"] == "SIMULATED_NOT_ACCEPTED" for item in fixtures)
        and all(item["trust_level"] == 0 for item in fixtures)
        and all(item["connection_attempted"] is False for item in fixtures)
        and all(item["persistence_attempted"] is False for item in fixtures)
        and all(item["notification_sent"] is False for item in fixtures)
        and all(item["remediation_attempted"] is False for item in fixtures)
    ):
        print(" [PASS] All 48 injected fixture routes remain trust zero and side-effect free")
        passed += 1
    else:
        errors.append("P6 fixture validation boundary failed")

    blocked = engine.execute_readonly("fw-fortigate-edge-01", authorized=True)
    if blocked["status"] == "NOT_RUN" and blocked["reason"] == "P6_LIVE_TRANSPORTS_DISABLED" and blocked["connection_attempted"] is False:
        print(" [PASS] Owner authorization alone cannot bypass the disabled live policy")
        passed += 1
    else:
        errors.append(f"P6 disabled-live gate failed: {blocked}")

    serialized = json.dumps(public, sort_keys=True).casefold()
    if public["operations_included"] is False and not any(marker in serialized for marker in ("password", "credential_reference", "raw_output", "172.23.")):
        print(" [PASS] Public catalog metadata excludes secrets, addresses, operations, and raw output")
        passed += 1
    else:
        errors.append("P6 public catalog minimization failed")

    pilot = run_p6_offline_pilot()
    if (
        pilot["success"]
        and pilot["passed"] == pilot["total"] == 25
        and pilot["connector_families"] == 15
        and pilot["canonical_entities"] == 48
        and pilot["planning_coverage_percent"] == pilot["offline_validation_coverage_percent"] == 100.0
        and pilot["live_connections"] == 0
        and pilot["persistence_actions"] == 0
        and pilot["remediation_actions"] == 0
        and pilot["production_readiness_claimed"] is False
    ):
        print(" [PASS] Twenty-five P6 scenarios validate all platforms without a live or write action")
        passed += 1
    else:
        errors.append(f"P6 pilot failed: {pilot}")

    required = (
        base_dir / "docs" / "P6_PLAN.md",
        base_dir / "docs" / "P6_READINESS.md",
        base_dir / "docs" / "P6_OFFLINE_PILOT_REPORT.md",
        base_dir / "00_meta" / "adr" / "ADR-013-P6-Multi-Platform-Read-Only-Connectors.md",
    )
    ci_text = (base_dir / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
    if all(path.is_file() for path in required) and "run_p6_offline_pilot.py" in ci_text:
        print(" [PASS] P6 plan, readiness, pilot report, ADR, and CI entry point are present")
        passed += 1
    else:
        errors.append("P6 governance or CI integration is missing")

    print("\n--- P6 VALIDATION SUMMARY ---")
    if errors:
        print(f"FAILED with {len(errors)} errors:")
        for error in errors:
            print(f" - {error}")
        return False
    print(f"SUCCESS: {passed} P6 Components Verified (0 Errors)")
    return True


if __name__ == "__main__":
    sys.exit(0 if test_p6_phase() else 1)
