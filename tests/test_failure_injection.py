#!/usr/bin/env python3
"""Offline failure-injection tests with all mutable fixtures isolated."""

import sys
from pathlib import Path
from tempfile import TemporaryDirectory

import yaml

base_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(base_dir))

from core.entity.build_entity_index import EntityIndexBuilder
from core.lifecycle.lifecycle_engine import KnowledgeLifecycleEngine
from core.router.route_query import QueryRouter
from core.tools.drivers.driver_factory import DriverFactory


def run_failure_injection_suite() -> bool:
    print("[RUNNING OFFLINE CONTROLLED FAILURE-INJECTION SUITE]")
    errors: list[str] = []
    passed = 0

    factory = DriverFactory()
    disabled = factory.execute_command("ssh", "192.0.2.10", "read-status", authorized=True)
    if disabled["status"] == "EXECUTION_DISABLED" and disabled["connection_attempted"] is False:
        print(" [PASS] Disabled transport fails before any network connection")
        passed += 1
    else:
        errors.append(f"Disabled transport boundary failed: {disabled}")

    invalid_target = factory.plan_command("rest", "https://user:secret@example.invalid/status", "GET")
    if invalid_target["status"] == "INVALID_REQUEST" and invalid_target["connection_attempted"] is False:
        print(" [PASS] Credential-bearing targets fail closed")
        passed += 1
    else:
        errors.append(f"Credential-bearing target was not rejected: {invalid_target}")

    try:
        yaml.safe_load("id: test\n  bad_indent: [unclosed list")
        errors.append("Invalid YAML did not raise an error")
    except yaml.YAMLError:
        print(" [PASS] Invalid YAML is rejected")
        passed += 1

    with TemporaryDirectory() as temporary_directory:
        isolated_root = Path(temporary_directory)
        empty_index = EntityIndexBuilder(base_dir=isolated_root).build_index()
    if empty_index["total_entities"] == 0:
        print(" [PASS] Missing knowledge directory returns an empty in-memory index")
        passed += 1
    else:
        errors.append(f"Missing knowledge directory handling failed: {empty_index}")

    vague = QueryRouter(base_dir=base_dir).classify_query("Unknown mystery outage")
    if vague["resolution_status"] == "unknown" and vague["clarification_request"]["requires_clarification"]:
        print(" [PASS] Unknown target requests clarification")
        passed += 1
    else:
        errors.append(f"Unknown-target handling failed: {vague}")

    with TemporaryDirectory() as temporary_directory:
        isolated_root = Path(temporary_directory)
        queue_file = isolated_root / "operations" / "discovery" / "review_queue.json"
        queue_file.parent.mkdir(parents=True)
        queue_file.write_text("{corrupted_json_syntax", encoding="utf-8")
        result = KnowledgeLifecycleEngine(base_dir=isolated_root).promote_to_canonical(
            "missing-proposal", explicit_owner_instruction=True
        )
        queue_unchanged = queue_file.read_text(encoding="utf-8") == "{corrupted_json_syntax"
    if result["promoted"] is False and result["owner_reviewed_for_manual_promotion"] is False and queue_unchanged:
        print(" [PASS] Corrupted isolated review queue fails closed without rewriting it")
        passed += 1
    else:
        errors.append(f"Corrupted review-queue handling failed: {result}")

    print("\n--- OFFLINE FAILURE-INJECTION SUMMARY ---")
    if errors:
        print(f"FAILED with {len(errors)} errors:")
        for error in errors:
            print(f" - {error}")
        return False
    print(f"SUCCESS: {passed} Failure Scenarios Passed (0 Errors)")
    return True


if __name__ == "__main__":
    sys.exit(0 if run_failure_injection_suite() else 1)
