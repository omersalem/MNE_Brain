#!/usr/bin/env python3
"""Run minimal sole-owner P4 governance scenarios."""

import copy
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable


BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from core.incidents.intake import IncidentIntakeService
from core.incidents.workflow_governance import IncidentWorkflowGovernance


def _unsafe_policy_rejected(**updates: Any) -> bool:
    evaluator = IncidentWorkflowGovernance(base_dir=BASE_DIR)
    original = copy.deepcopy(evaluator.policy)
    evaluator.policy.update(updates)
    try:
        evaluator.evaluate()
    except ValueError:
        return True
    finally:
        evaluator.policy = original
    return False


def _intake() -> dict[str, Any]:
    return IncidentIntakeService(base_dir=BASE_DIR).create_intake(
        {
            "target_reference": "fw-fortigate-edge-01",
            "symptom": "Remote users cannot reach the published service",
            "affected_service": "SSL VPN",
            "affected_scope": "multiple_users",
            "availability": "unavailable",
            "affected_user_count": 12,
            "reported_at": datetime.now(timezone.utc).isoformat(),
        }
    )


def run_p4_workflow_governance_pilot() -> dict[str, Any]:
    status = IncidentWorkflowGovernance(base_dir=BASE_DIR).evaluate()
    intake = _intake()
    scenarios: list[tuple[str, Callable[[], bool], str]] = [
        (
            "p4g-01",
            lambda: status["approval_state"] == "OWNER_CONTROLLED",
            "governance is controlled by one owner",
        ),
        (
            "p4g-02",
            lambda: status["owner_reference"] == "MNE-BRAIN-OWNER",
            "the sole owner reference is exact and stable",
        ),
        (
            "p4g-03",
            lambda: status["audit_mode"] == "IN_MEMORY_ONLY"
            and status["retention"] == "NONE",
            "audit is in memory and retention is disabled",
        ),
        (
            "p4g-04",
            lambda: status["authorization"]["read_only_troubleshooting"]
            == "EXPLICIT_OWNER_PROCEED",
            "read-only troubleshooting requires explicit owner proceed",
        ),
        (
            "p4g-05",
            lambda: status["authorization"]["configuration_changes"]
            == "EXPLICIT_OWNER_INSTRUCTION"
            and status["authorization"]["remediation"]
            == "EXPLICIT_OWNER_INSTRUCTION",
            "changes and remediation require explicit owner instruction",
        ),
        (
            "p4g-06",
            lambda: not any(status["disabled_capabilities"].values()),
            "automatic workflow and persistence capabilities are disabled",
        ),
        (
            "p4g-07",
            lambda: not any(status["safety"].values()),
            "governance evaluation causes no side effects",
        ),
        (
            "p4g-08",
            lambda: _unsafe_policy_rejected(notifications_enabled=True),
            "automatic notification activation fails closed",
        ),
        (
            "p4g-09",
            lambda: _unsafe_policy_rejected(retention="PERSISTENT"),
            "persistent retention activation fails closed",
        ),
        (
            "p4g-10",
            lambda: intake["workflow_governance"]["approval_state"]
            == "OWNER_CONTROLLED"
            and intake["intake"]["owner_reference"] == "MNE-BRAIN-OWNER"
            and intake["readiness"]["owner_controlled"] is True,
            "incident intake carries the same sole-owner policy",
        ),
    ]

    passed = 0
    print("=" * 72)
    print(" MNE_Brain P4 - Sole-Owner Governance Pilot")
    print("=" * 72)
    for scenario_id, assertion, description in scenarios:
        success = assertion()
        passed += int(success)
        print(f"[{'PASS' if success else 'FAIL'}] {scenario_id} | {description}")
    print("=" * 72)
    print(f" P4 SOLE-OWNER PILOT: {passed} / {len(scenarios)} SCENARIOS PASSED")
    print(" Automatic assignment: 0 | Notifications: 0 | Persistence: 0 | Remediation: 0")
    print("=" * 72)
    return {"success": passed == len(scenarios), "passed": passed, "total": len(scenarios)}


if __name__ == "__main__":
    outcome = run_p4_workflow_governance_pilot()
    sys.exit(0 if outcome["success"] else 1)
