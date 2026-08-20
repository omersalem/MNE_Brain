#!/usr/bin/env python3
"""Run deterministic P4 incident-intake acceptance scenarios."""

import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Callable


BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from core.incidents.intake import IncidentIntakeService


def _request(**updates: Any) -> dict[str, Any]:
    payload = {
        "target_reference": "fw-fortigate-edge-01",
        "symptom": "Remote users cannot reach the published service",
        "affected_service": "SSL VPN",
        "affected_scope": "multiple_users",
        "availability": "unavailable",
        "affected_user_count": 12,
        "incident_reference": "INC-P4-INTAKE-PILOT",
        "reported_at": datetime.now(timezone.utc).isoformat(),
    }
    payload.update(updates)
    return payload


def _rejects(service: IncidentIntakeService, payload: dict[str, Any], text: str) -> bool:
    try:
        service.create_intake(payload)
    except ValueError as exc:
        return text.casefold() in str(exc).casefold()
    return False


def run_p4_intake_pilot() -> dict[str, Any]:
    service = IncidentIntakeService(base_dir=BASE_DIR)
    ready_request = _request()
    ready = service.create_intake(ready_request)
    incomplete = service.create_intake(
        _request(affected_scope="unknown", availability="unknown", affected_user_count=None)
    )
    unknown = service.create_intake(_request(target_reference="unknown-ministry-target"))
    branch = service.create_intake(
        _request(
            affected_scope="branch",
            branch_references=["nablus"],
            affected_user_count=None,
        )
    )
    multi_branch = service.create_intake(
        _request(
            affected_scope="multiple_branches",
            branch_references=["nablus", "jenin"],
            affected_user_count=None,
        )
    )

    scenarios: list[tuple[str, Callable[[], bool], str]] = [
        (
            "p4i-01",
            lambda: ready["status"] == "READY_FOR_EVIDENCE_REVIEW"
            and ready["case"]["priority"]["classification"] == "PROVISIONAL_P2"
            and bool(ready["next_evidence_objectives"]),
            "complete exact-target intake is ready for evidence review",
        ),
        (
            "p4i-02",
            lambda: incomplete["status"] == "IMPACT_REQUIRED"
            and incomplete["next_evidence_objectives"] == [],
            "unknown impact withholds evidence objectives",
        ),
        (
            "p4i-03",
            lambda: unknown["status"] == "NEEDS_TARGET"
            and unknown["next_evidence_objectives"] == [],
            "unknown target withholds evidence objectives",
        ),
        (
            "p4i-04",
            lambda: branch["intake"]["branch_references"] == ["nablus"],
            "single-branch scope preserves one branch reference",
        ),
        (
            "p4i-05",
            lambda: multi_branch["intake"]["branch_references"] == ["nablus", "jenin"],
            "multi-branch scope preserves bounded unique references",
        ),
        (
            "p4i-06",
            lambda: ready["intake"]["owner_reference"] == "MNE-BRAIN-OWNER"
            and ready["case"]["ownership"]["primary"]["team"] == "MNE-BRAIN-OWNER"
            and ready["safety"]["notification_sent"] is False,
            "sole owner is applied automatically without notification",
        ),
        (
            "p4i-07",
            lambda: _rejects(
                service,
                _request(affected_scope="single_user", affected_user_count=2),
                "equal to 1",
            ),
            "inconsistent single-user count fails closed",
        ),
        (
            "p4i-08",
            lambda: _rejects(
                service,
                _request(affected_scope="multiple_users", affected_user_count=1),
                "at least 2",
            ),
            "inconsistent multi-user count fails closed",
        ),
        (
            "p4i-09",
            lambda: _rejects(
                service,
                _request(reported_at=(datetime.now(timezone.utc) + timedelta(days=1)).isoformat()),
                "future",
            ),
            "future report timestamp fails closed",
        ),
        (
            "p4i-10",
            lambda: _rejects(service, _request(unexpected="field"), "additional properties"),
            "unsupported fields fail closed",
        ),
        (
            "p4i-11",
            lambda: _rejects(service, _request(symptom="bad\nsecond line"), "does not match"),
            "control characters fail closed",
        ),
        (
            "p4i-12",
            lambda: ready["intake_id"] == service.create_intake(ready_request)["intake_id"]
            and not any(ready["safety"].values()),
            "same report is deterministic and causes no side effects",
        ),
    ]

    passed = 0
    print("=" * 72)
    print(" MNE_Brain P4 - Professional Incident Intake Pilot")
    print("=" * 72)
    for scenario_id, assertion, description in scenarios:
        success = assertion()
        passed += int(success)
        print(f"[{'PASS' if success else 'FAIL'}] {scenario_id} | {description}")
    print("=" * 72)
    print(f" P4 INTAKE PILOT: {passed} / {len(scenarios)} SCENARIOS PASSED")
    print(" Live: 0 | Notifications: 0 | Persistence: 0 | Remediation: 0")
    print("=" * 72)
    return {"success": passed == len(scenarios), "passed": passed, "total": len(scenarios)}


if __name__ == "__main__":
    outcome = run_p4_intake_pilot()
    sys.exit(0 if outcome["success"] else 1)
